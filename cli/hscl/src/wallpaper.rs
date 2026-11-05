//! `hscl wallpaper` - Wallpaper Studio backend: presets for the HSCL1 animated wallpaper effects.
//!
//! Presets are small JSON files (system presets in `/usr/share/hscl/wallpaper-presets`, user presets in
//! `~/.local/share/hscl/wallpaper-presets`). Every value is validated and bounded; only validated primitives ever reach the
//! Plasma scripting call, so no preset can inject script text. Low-VRAM mode caps density and animation speed.

use crate::appearance::Runner;
use anyhow::{bail, Context, Result};
use serde::{Deserialize, Serialize};
use std::path::{Path, PathBuf};

pub const EFFECTS: [&str; 4] = ["rain", "starfield", "aurora", "grid"];

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct Preset {
    pub id: String,
    pub name: String,
    pub effect: String,
    #[serde(default = "two")]
    pub density: u8,
    #[serde(default = "two")]
    pub speed: u8,
    #[serde(default = "yes")]
    pub show_mark: bool,
    /// `#rrggbb` or empty for the HSCL1 default.
    #[serde(default)]
    pub accent: String,
    #[serde(default)]
    pub background: String,
}

fn two() -> u8 {
    2
}
fn yes() -> bool {
    true
}

fn is_hex_colour(c: &str) -> bool {
    c.is_empty()
        || (c.len() == 7 && c.starts_with('#') && c[1..].bytes().all(|b| b.is_ascii_hexdigit()))
}

pub fn validate(p: &Preset) -> Result<()> {
    if p.id.is_empty()
        || p.id.len() > 32
        || !p
            .id
            .bytes()
            .all(|b| b.is_ascii_lowercase() || b.is_ascii_digit() || b == b'-')
        || p.id.starts_with('-')
    {
        bail!(
            "invalid preset id {:?}: use a-z, 0-9 and '-' (max 32)",
            p.id
        );
    }
    if p.name.is_empty() || p.name.chars().count() > 40 || p.name.chars().any(|c| c.is_control()) {
        bail!("invalid preset name");
    }
    if !EFFECTS.contains(&p.effect.as_str()) {
        bail!(
            "unknown effect {:?}; choose one of {}",
            p.effect,
            EFFECTS.join(", ")
        );
    }
    if !(1..=3).contains(&p.density) || !(1..=3).contains(&p.speed) {
        bail!("density and speed must be between 1 and 3");
    }
    if !is_hex_colour(&p.accent) || !is_hex_colour(&p.background) {
        bail!("colours must be #rrggbb or empty");
    }
    Ok(())
}

/// Low-VRAM mode: sparse and slow so weak GPUs stay responsive.
pub fn capped(p: &Preset, low_vram: bool) -> Preset {
    let mut q = p.clone();
    if low_vram {
        q.density = q.density.min(1);
        q.speed = q.speed.min(2);
    }
    q
}

pub fn system_dir() -> PathBuf {
    std::env::var_os("HSCL_WALLPAPER_PRESETS")
        .map(PathBuf::from)
        .unwrap_or_else(|| PathBuf::from("/usr/share/hscl/wallpaper-presets"))
}

pub fn user_dir() -> PathBuf {
    if let Some(d) = std::env::var_os("HSCL_USER_PRESETS") {
        return PathBuf::from(d);
    }
    PathBuf::from(std::env::var_os("HOME").unwrap_or_default())
        .join(".local/share/hscl/wallpaper-presets")
}

fn read_dir(dir: &Path) -> Vec<Preset> {
    let mut out = vec![];
    if let Ok(rd) = std::fs::read_dir(dir) {
        for e in rd.flatten() {
            if e.path().extension().is_some_and(|x| x == "json") {
                if let Ok(t) = std::fs::read_to_string(e.path()) {
                    if let Ok(p) = serde_json::from_str::<Preset>(&t) {
                        if validate(&p).is_ok()
                            && e.path()
                                .file_stem()
                                .is_some_and(|s| s.to_string_lossy() == p.id)
                        {
                            out.push(p);
                        }
                    }
                }
            }
        }
    }
    out.sort_by(|a, b| a.id.cmp(&b.id));
    out
}

/// System presets first, then user presets (a user preset with the same id replaces the system one).
pub fn load_all(system: &Path, user: &Path) -> Vec<Preset> {
    let mut all = read_dir(system);
    for u in read_dir(user) {
        all.retain(|p| p.id != u.id);
        all.push(u);
    }
    all.sort_by(|a, b| a.id.cmp(&b.id));
    all
}

pub fn find<'a>(all: &'a [Preset], id: &str) -> Result<&'a Preset> {
    all.iter()
        .find(|p| p.id == id)
        .with_context(|| format!("unknown wallpaper preset {id:?}; run `hscl wallpaper list`"))
}

/// Save a user preset; refuses to overwrite unless `overwrite`.
pub fn save(user: &Path, p: &Preset, overwrite: bool) -> Result<PathBuf> {
    validate(p)?;
    std::fs::create_dir_all(user)?;
    let path = user.join(format!("{}.json", p.id));
    if path.exists() && !overwrite {
        bail!("preset {} already exists (use --overwrite)", p.id);
    }
    std::fs::write(&path, serde_json::to_string_pretty(p)? + "\n")?;
    Ok(path)
}

/// Delete a user preset (system presets are read-only).
pub fn delete(user: &Path, id: &str) -> Result<()> {
    let path = user.join(format!("{id}.json"));
    if id.contains('/') || id.contains("..") || !path.is_file() {
        bail!("no user preset {id:?}");
    }
    std::fs::remove_file(path)?;
    Ok(())
}

/// Copy a preset to a new file (never overwrites).
pub fn export(p: &Preset, dest: &Path) -> Result<()> {
    use std::io::Write;
    let mut f = std::fs::OpenOptions::new()
        .write(true)
        .create_new(true)
        .open(dest)
        .with_context(|| format!("cannot create {} (it must not exist)", dest.display()))?;
    f.write_all((serde_json::to_string_pretty(p)? + "\n").as_bytes())?;
    Ok(())
}

/// Plasma scripting commands that make a preset the wallpaper of every desktop. Only validated primitives are interpolated.
pub fn apply_commands(p: &Preset) -> Result<Vec<Vec<String>>> {
    validate(p)?;
    let script = format!(
        "desktops().forEach(function(d){{ d.wallpaperPlugin = 'org.hcs.hscl1.rain'; d.currentConfigGroup = ['Wallpaper','org.hcs.hscl1.rain','General']; d.writeConfig('Effect', '{}'); d.writeConfig('Density', {}); d.writeConfig('Speed', {}); d.writeConfig('ShowMark', {}); d.writeConfig('Accent', '{}'); d.writeConfig('Background', '{}'); }});",
        p.effect, p.density, p.speed, p.show_mark, p.accent, p.background
    );
    Ok(vec![vec![
        "qdbus6".into(),
        "org.kde.plasmashell".into(),
        "/PlasmaShell".into(),
        "org.kde.PlasmaShell.evaluateScript".into(),
        script,
    ]])
}

pub fn apply(p: &Preset, low_vram: bool, runner: &mut dyn Runner) -> Result<()> {
    for argv in apply_commands(&capped(p, low_vram))? {
        runner.run(&argv)?;
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    fn p(id: &str) -> Preset {
        Preset {
            id: id.into(),
            name: "Test".into(),
            effect: "rain".into(),
            density: 2,
            speed: 2,
            show_mark: true,
            accent: String::new(),
            background: String::new(),
        }
    }

    #[test]
    fn validation_bounds() {
        assert!(validate(&p("ok-1")).is_ok());
        let mut bad = vec![];
        for id in ["", "UPPER", "a b", "../x", "-x", &"a".repeat(33), "x;y"] {
            bad.push(p(id));
        }
        let mut x = p("a");
        x.effect = "plasma".into();
        bad.push(x);
        let mut x = p("a");
        x.density = 0;
        bad.push(x);
        let mut x = p("a");
        x.speed = 4;
        bad.push(x);
        let mut x = p("a");
        x.accent = "red".into();
        bad.push(x);
        let mut x = p("a");
        x.background = "#12345".into();
        bad.push(x);
        let mut x = p("a");
        x.name = "x\ny".into();
        bad.push(x);
        for b in bad {
            assert!(validate(&b).is_err(), "{b:?}");
        }
    }

    #[test]
    fn low_vram_caps_density_and_speed() {
        let mut x = p("a");
        x.density = 3;
        x.speed = 3;
        let c = capped(&x, true);
        assert_eq!((c.density, c.speed), (1, 2));
        assert_eq!(capped(&x, false), x);
    }

    #[test]
    fn apply_script_contains_only_validated_values() {
        let mut x = p("a");
        x.effect = "aurora".into();
        x.accent = "#b07cff".into();
        let cmds = apply_commands(&x).unwrap();
        let s = &cmds[0][4];
        assert!(
            s.contains("writeConfig('Effect', 'aurora')")
                && s.contains("'#b07cff'")
                && s.contains("ShowMark', true")
        );
        // a hostile preset never gets that far
        let mut evil = p("a");
        evil.accent = "#12345'); evil(); ('".into();
        assert!(apply_commands(&evil).is_err());
        evil = p("a");
        evil.effect = "rain'); evil(); ('".into();
        assert!(apply_commands(&evil).is_err());
    }

    #[derive(Default)]
    struct Rec(Vec<Vec<String>>);
    impl Runner for Rec {
        fn run(&mut self, a: &[String]) -> Result<()> {
            self.0.push(a.to_vec());
            Ok(())
        }
    }

    #[test]
    fn apply_uses_low_vram_caps() {
        let mut x = p("a");
        x.density = 3;
        let mut r = Rec::default();
        apply(&x, true, &mut r).unwrap();
        assert!(r.0[0][4].contains("writeConfig('Density', 1)"));
        let mut r2 = Rec::default();
        apply(&x, false, &mut r2).unwrap();
        assert!(r2.0[0][4].contains("writeConfig('Density', 3)"));
    }

    #[test]
    fn user_presets_override_system_ones_and_bad_files_are_ignored() {
        let sys = tempfile::tempdir().unwrap();
        let usr = tempfile::tempdir().unwrap();
        save(sys.path(), &p("one"), false).unwrap();
        let mut mine = p("one");
        mine.name = "Mine".into();
        save(usr.path(), &mine, false).unwrap();
        std::fs::write(usr.path().join("broken.json"), "{not json").unwrap();
        std::fs::write(
            usr.path().join("mismatch.json"),
            serde_json::to_string(&p("other")).unwrap(),
        )
        .unwrap();
        let all = load_all(sys.path(), usr.path());
        assert_eq!(all.len(), 1);
        assert_eq!(all[0].name, "Mine");
        assert!(find(&all, "nope").is_err());
    }

    #[test]
    fn save_refuses_overwrite_delete_only_removes_user_files_export_never_overwrites() {
        let usr = tempfile::tempdir().unwrap();
        save(usr.path(), &p("a"), false).unwrap();
        assert!(save(usr.path(), &p("a"), false).is_err());
        assert!(save(usr.path(), &p("a"), true).is_ok());
        let dest = usr.path().join("out.json");
        export(&p("a"), &dest).unwrap();
        assert!(export(&p("a"), &dest).is_err());
        assert!(delete(usr.path(), "../a").is_err());
        assert!(delete(usr.path(), "missing").is_err());
        delete(usr.path(), "a").unwrap();
        assert!(!usr.path().join("a.json").exists());
    }

    #[test]
    fn shipped_presets_are_valid() {
        let dir = Path::new(env!("CARGO_MANIFEST_DIR"))
            .join("../../packages/debian/hscl-desktop/usr/share/hscl/wallpaper-presets");
        let all = read_dir(&dir);
        assert!(all.len() >= 5, "found {}", all.len());
        let effects: std::collections::BTreeSet<_> = all.iter().map(|p| p.effect.clone()).collect();
        for e in EFFECTS {
            assert!(effects.contains(e), "no shipped preset for {e}");
        }
    }
}
