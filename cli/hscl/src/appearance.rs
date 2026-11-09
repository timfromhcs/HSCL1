//! `hscl appearance theme ...` - list, show, set and restore HCS themes.
//!
//! Themes come from the design-token file (single source of truth). Applying a theme only ever runs the
//! fixed Plasma helper programs with validated arguments (no shell, no user-provided command text), after
//! writing a backup of the previous selection.

use anyhow::{bail, Context, Result};
use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::path::{Path, PathBuf};

pub const DEFAULT_THEME: &str = "hcs-midnight";
const DEFAULT_TOKENS: &str = "/usr/share/hscl/themes/tokens.json";

#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct Theme {
    pub id: String,
    pub title: String,
    pub color_scheme: String,
    pub wallpaper: String,
}

/// Where the token file lives (`HSCL_TOKENS` overrides, used by tests and development builds).
pub fn tokens_path() -> PathBuf {
    std::env::var_os("HSCL_TOKENS")
        .map(PathBuf::from)
        .unwrap_or_else(|| PathBuf::from(DEFAULT_TOKENS))
}

/// Per-user state directory (`HSCL_CONFIG_DIR` overrides).
pub fn config_dir() -> PathBuf {
    if let Some(d) = std::env::var_os("HSCL_CONFIG_DIR") {
        return PathBuf::from(d);
    }
    if let Some(x) = std::env::var_os("XDG_CONFIG_HOME") {
        return PathBuf::from(x).join("hscl");
    }
    // HOME is unset on Windows; without this fallback every command wrote to a relative
    // `./.config/hscl` inside whatever directory it was started from (found 2026-11-09 by a miner
    // CLI test leaving `.config/hscl/miner.json` in the repository root).
    for var in ["HOME", "USERPROFILE"] {
        if let Some(home) = std::env::var_os(var) {
            if !home.is_empty() {
                return PathBuf::from(home).join(".config").join("hscl");
            }
        }
    }
    if let (Some(drive), Some(path)) = (std::env::var_os("HOMEDRIVE"), std::env::var_os("HOMEPATH"))
    {
        if !path.is_empty() {
            return PathBuf::from(drive).join(path).join(".config").join("hscl");
        }
    }
    PathBuf::from(".config").join("hscl")
}

/// Theme ids are a closed, boring alphabet: `hcs-` + `[a-z0-9-]`, at most 24 characters.
pub fn validate_id(id: &str) -> Result<()> {
    let ok = id.len() <= 24
        && id.len() > 4
        && id.starts_with("hcs-")
        && id
            .bytes()
            .all(|b| b.is_ascii_lowercase() || b.is_ascii_digit() || b == b'-')
        && !id.contains("--");
    if !ok {
        bail!("invalid theme id {id:?}: expected hcs-<name> using a-z, 0-9 and '-'");
    }
    Ok(())
}

fn title_case(word: &str) -> String {
    let mut c = word.chars();
    c.next()
        .map(|f| f.to_uppercase().collect::<String>() + c.as_str())
        .unwrap_or_default()
}

pub fn catalog_from(tokens: &Value) -> Result<Vec<Theme>> {
    let themes = tokens
        .get("themes")
        .and_then(Value::as_object)
        .context("token file has no \"themes\" object")?;
    let mut out = Vec::new();
    for id in themes.keys() {
        validate_id(id)?;
        let name = title_case(&id["hcs-".len()..]);
        out.push(Theme {
            id: id.clone(),
            title: format!("HCS {name}"),
            color_scheme: format!("HCS{name}"),
            wallpaper: format!("HSCL1{name}"),
        });
    }
    out.sort_by(|a, b| a.id.cmp(&b.id));
    Ok(out)
}

pub fn load_catalog() -> Result<Vec<Theme>> {
    let p = tokens_path();
    let text = std::fs::read_to_string(&p)
        .with_context(|| format!("cannot read token file {}", p.display()))?;
    catalog_from(&serde_json::from_str(&text).context("token file is not valid JSON")?)
}

pub fn find<'a>(catalog: &'a [Theme], id: &str) -> Result<&'a Theme> {
    validate_id(id)?;
    catalog
        .iter()
        .find(|t| t.id == id)
        .with_context(|| format!("unknown theme {id:?}; run `hscl appearance theme list`"))
}

#[derive(Debug, Serialize, PartialEq, Eq)]
pub struct Plan {
    pub theme: String,
    pub backup_file: PathBuf,
    pub state_file: PathBuf,
    pub commands: Vec<Vec<String>>,
}

pub fn plan(theme: &Theme, cfg: &Path, timestamp: u64) -> Plan {
    Plan {
        theme: theme.id.clone(),
        backup_file: cfg
            .join("appearance-backup")
            .join(format!("{timestamp}.json")),
        state_file: cfg.join("appearance.json"),
        commands: vec![
            vec![
                "plasma-apply-colorscheme".into(),
                theme.color_scheme.clone(),
            ],
            vec![
                "plasma-apply-wallpaperimage".into(),
                format!(
                    "/usr/share/wallpapers/{}/contents/images/1920x1080.png",
                    theme.wallpaper
                ),
            ],
        ],
    }
}

/// Executes argv vectors; replaced by a recorder in tests.
pub trait Runner {
    fn run(&mut self, argv: &[String]) -> Result<()>;
}

pub struct SystemRunner;

impl Runner for SystemRunner {
    fn run(&mut self, argv: &[String]) -> Result<()> {
        let (prog, args) = argv.split_first().context("empty command")?;
        let status = std::process::Command::new(prog)
            .args(args)
            .status()
            .with_context(|| format!("cannot run {prog} (is the Plasma desktop installed?)"))?;
        if !status.success() {
            bail!("{prog} failed with {status}");
        }
        Ok(())
    }
}

pub fn current(cfg: &Path) -> Option<String> {
    let text = std::fs::read_to_string(cfg.join("appearance.json")).ok()?;
    serde_json::from_str::<Value>(&text)
        .ok()?
        .get("theme")?
        .as_str()
        .map(str::to_owned)
}

/// Back up the previous selection, run the Plasma helpers, then record the new theme.
pub fn apply(p: &Plan, cfg: &Path, runner: &mut dyn Runner, now: u64) -> Result<()> {
    std::fs::create_dir_all(
        p.backup_file
            .parent()
            .context("backup path has no parent")?,
    )?;
    let previous = current(cfg);
    std::fs::write(
        &p.backup_file,
        serde_json::to_string_pretty(
            &serde_json::json!({"previous_theme": previous, "created": now}),
        )?,
    )?;
    for argv in &p.commands {
        runner.run(argv)?;
    }
    std::fs::write(
        &p.state_file,
        serde_json::to_string_pretty(&serde_json::json!({"theme": p.theme}))?,
    )?;
    Ok(())
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct AppearanceConfig {
    pub theme: Option<String>,
    pub mode: String,
    pub dock_position: String,
}

impl Default for AppearanceConfig {
    fn default() -> Self {
        Self {
            theme: Some(DEFAULT_THEME.to_string()),
            mode: "dark".to_string(),
            dock_position: "bottom".to_string(),
        }
    }
}

pub fn validate_mode(mode: &str) -> Result<()> {
    match mode {
        "dark" | "light" | "auto" => Ok(()),
        other => bail!("invalid appearance mode '{other}'; valid modes: dark, light, auto"),
    }
}

pub fn validate_dock_position(pos: &str) -> Result<()> {
    match pos {
        "bottom" | "left" | "right" => Ok(()),
        other => bail!("invalid dock position '{other}'; valid positions: bottom, left, right"),
    }
}

pub fn load_config(cfg_dir: &Path) -> AppearanceConfig {
    let path = cfg_dir.join("appearance.json");
    if let Ok(content) = std::fs::read_to_string(&path) {
        if let Ok(cfg) = serde_json::from_str::<AppearanceConfig>(&content) {
            return cfg;
        }
    }
    AppearanceConfig::default()
}

pub fn save_config(cfg_dir: &Path, cfg: &AppearanceConfig) -> Result<()> {
    std::fs::create_dir_all(cfg_dir)?;
    let path = cfg_dir.join("appearance.json");
    let content = serde_json::to_string_pretty(cfg)?;
    std::fs::write(&path, content)?;
    Ok(())
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct ModePlan {
    pub mode: String,
    pub scheme: Option<String>,
    pub dry_run: bool,
    pub message: String,
}

/// The colour scheme that a mode request applies. `auto` deliberately maps to `None`: HSCL1 does not
/// ship a day/night timer yet, so the scheme is left alone and only the preference is recorded.
pub fn scheme_for_mode(mode: &str) -> Option<&'static str> {
    match mode {
        "dark" => Some("HCSMidnight"),
        "light" => Some("HCSLight"),
        _ => None,
    }
}

pub fn set_mode(
    mode: &str,
    dry_run: bool,
    cfg_dir: &Path,
    runner: &mut dyn Runner,
) -> Result<ModePlan> {
    validate_mode(mode)?;
    let scheme = scheme_for_mode(mode);
    let message = if dry_run {
        match scheme {
            Some(s) => format!(
                "Dry run: would set appearance mode to '{mode}' and apply colour scheme '{s}'"
            ),
            None => {
                format!("Dry run: would set appearance mode to '{mode}' (no colour scheme change)")
            }
        }
    } else {
        let mut cfg = load_config(cfg_dir);
        cfg.mode = mode.to_string();
        save_config(cfg_dir, &cfg)?;
        // Until 2026-11-09 this only wrote the JSON and reported success: the desktop never changed.
        // AGENTS.md 0.3.1 forbids a command that only prints success, so the scheme is really applied
        // and a failing helper is a failing command.
        if let Some(s) = scheme {
            runner.run(&["plasma-apply-colorscheme".into(), s.into()])?;
            format!("Appearance mode set to '{mode}' (colour scheme {s})")
        } else {
            format!("Appearance mode set to '{mode}' (colour scheme unchanged)")
        }
    };
    Ok(ModePlan {
        mode: mode.to_string(),
        scheme: scheme.map(str::to_owned),
        dry_run,
        message,
    })
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct DockPlan {
    pub position: String,
    pub script: String,
    pub dry_run: bool,
    pub message: String,
}

/// Plasma scripting snippet that moves the first panel which is not the HSCL1 top bar. Used by
/// `hscl appearance dock position`; it is a pure function so the generated script can be tested
/// without a desktop session.
pub fn dock_script(pos: &str) -> String {
    let loc = match pos {
        "left" => "left",
        "right" => "right",
        _ => "bottom",
    };
    format!(
        "var ps = panels();\nfor (var i = 0; i < ps.length; i++) {{\n  if (ps[i].location !== 'top') {{ ps[i].location = '{loc}'; break; }}\n}}\n"
    )
}

pub fn set_dock_position(
    pos: &str,
    dry_run: bool,
    cfg_dir: &Path,
    runner: &mut dyn Runner,
) -> Result<DockPlan> {
    validate_dock_position(pos)?;
    let message = if dry_run {
        format!("Dry run: would move the dock to '{pos}' and record the preference")
    } else {
        // Until 2026-11-09 this only wrote the JSON: nothing consumed the value, so the command
        // reported success while the dock stayed where it was. It now scripts the running panel.
        runner.run(&[
            "qdbus6".into(),
            "org.kde.plasmashell".into(),
            "/PlasmaShell".into(),
            "org.kde.PlasmaShell.evaluateScript".into(),
            dock_script(pos),
        ])?;
        let mut cfg = load_config(cfg_dir);
        cfg.dock_position = pos.to_string();
        save_config(cfg_dir, &cfg)?;
        format!("Dock position set to '{pos}'")
    };
    Ok(DockPlan {
        position: pos.to_string(),
        script: dock_script(pos),
        dry_run,
        message,
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    fn tokens() -> Value {
        json!({"themes": {"hcs-midnight": {}, "hcs-light": {}, "hcs-nord": {}}})
    }

    #[derive(Default)]
    struct Rec(Vec<Vec<String>>);
    impl Runner for Rec {
        fn run(&mut self, argv: &[String]) -> Result<()> {
            self.0.push(argv.to_vec());
            Ok(())
        }
    }

    #[test]
    fn catalog_is_sorted_and_named_from_tokens() {
        let c = catalog_from(&tokens()).unwrap();
        assert_eq!(
            c.iter().map(|t| t.id.as_str()).collect::<Vec<_>>(),
            ["hcs-light", "hcs-midnight", "hcs-nord"]
        );
        assert_eq!(c[1].color_scheme, "HCSMidnight");
        assert_eq!(c[1].wallpaper, "HSCL1Midnight");
        assert_eq!(c[1].title, "HCS Midnight");
    }

    #[test]
    fn rejects_traversal_and_shell_metacharacters() {
        for bad in [
            "../etc/passwd",
            "hcs-../x",
            "hcs-a;rm",
            "hcs-a b",
            "hcs-$(id)",
            "HCS-Midnight",
            "hcs-",
            "hcs--x",
            "midnight",
            "hcs-aaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            "hcs-\u{e9}",
        ] {
            assert!(validate_id(bad).is_err(), "{bad} must be rejected");
        }
        assert!(validate_id("hcs-midnight").is_ok());
    }

    #[test]
    fn unknown_theme_is_an_error() {
        let c = catalog_from(&tokens()).unwrap();
        assert!(find(&c, "hcs-aurora").is_err());
        assert!(find(&c, "hcs-nord").is_ok());
    }

    #[test]
    fn plan_uses_fixed_programs_and_no_shell() {
        let c = catalog_from(&tokens()).unwrap();
        let p = plan(&c[2], Path::new("/cfg"), 7);
        assert_eq!(p.commands[0], ["plasma-apply-colorscheme", "HCSNord"]);
        assert_eq!(p.commands[1][0], "plasma-apply-wallpaperimage");
        assert!(p
            .commands
            .iter()
            .flatten()
            .all(|a| !a.contains(';') && !a.contains('|') && !a.contains('$')));
        assert_eq!(p.backup_file, Path::new("/cfg/appearance-backup/7.json"));
    }

    #[test]
    fn apply_backs_up_previous_theme_then_records_new_one() {
        let dir = tempfile::tempdir().unwrap();
        let c = catalog_from(&tokens()).unwrap();
        let mut rec = Rec::default();
        apply(&plan(&c[1], dir.path(), 1), dir.path(), &mut rec, 1).unwrap();
        assert_eq!(current(dir.path()).as_deref(), Some("hcs-midnight"));
        apply(&plan(&c[2], dir.path(), 2), dir.path(), &mut rec, 2).unwrap();
        assert_eq!(current(dir.path()).as_deref(), Some("hcs-nord"));
        let backup: Value = serde_json::from_str(
            &std::fs::read_to_string(dir.path().join("appearance-backup/2.json")).unwrap(),
        )
        .unwrap();
        assert_eq!(backup["previous_theme"], "hcs-midnight");
        assert_eq!(rec.0.len(), 4);
    }

    #[test]
    fn failed_command_leaves_state_untouched() {
        struct Fail;
        impl Runner for Fail {
            fn run(&mut self, _: &[String]) -> Result<()> {
                bail!("boom")
            }
        }
        let dir = tempfile::tempdir().unwrap();
        let c = catalog_from(&tokens()).unwrap();
        assert!(apply(&plan(&c[1], dir.path(), 3), dir.path(), &mut Fail, 3).is_err());
        assert_eq!(current(dir.path()), None);
    }

    #[test]
    fn test_validate_mode_and_plan() {
        assert!(validate_mode("dark").is_ok());
        assert!(validate_mode("light").is_ok());
        assert!(validate_mode("auto").is_ok());
        assert!(validate_mode("neon").is_err());

        let dir = tempfile::tempdir().unwrap();
        let mut dry_runner = Rec::default();
        let plan_dry = set_mode("light", true, dir.path(), &mut dry_runner).unwrap();
        assert!(plan_dry.dry_run);
        assert_eq!(plan_dry.scheme.as_deref(), Some("HCSLight"));
        assert!(
            dry_runner.0.is_empty(),
            "a dry run must not touch the desktop"
        );
        assert_eq!(load_config(dir.path()).mode, "dark");

        let mut runner = Rec::default();
        let plan_real = set_mode("light", false, dir.path(), &mut runner).unwrap();
        assert!(!plan_real.dry_run);
        assert_eq!(load_config(dir.path()).mode, "light");
        assert_eq!(
            runner.0,
            vec![vec![
                "plasma-apply-colorscheme".to_string(),
                "HCSLight".to_string()
            ]],
            "the mode must really apply the colour scheme, not only write JSON"
        );
        assert!(plan_real.message.contains("HCSLight"));
    }

    #[test]
    fn auto_records_the_preference_without_changing_the_scheme() {
        let dir = tempfile::tempdir().unwrap();
        let mut runner = Rec::default();
        let plan = set_mode("auto", false, dir.path(), &mut runner).unwrap();
        assert_eq!(plan.scheme, None);
        assert!(runner.0.is_empty(), "auto must not pick a scheme blindly");
        assert_eq!(load_config(dir.path()).mode, "auto");
        assert!(plan.message.contains("unchanged"));
    }

    #[test]
    fn test_validate_dock_position_and_plan() {
        assert!(validate_dock_position("bottom").is_ok());
        assert!(validate_dock_position("left").is_ok());
        assert!(validate_dock_position("right").is_ok());
        assert!(validate_dock_position("top").is_err());

        let dir = tempfile::tempdir().unwrap();
        let mut dry_runner = Rec::default();
        let plan_dry = set_dock_position("left", true, dir.path(), &mut dry_runner).unwrap();
        assert!(plan_dry.dry_run);
        assert!(
            dry_runner.0.is_empty(),
            "a dry run must not script the panel"
        );
        assert_eq!(load_config(dir.path()).dock_position, "bottom");

        let mut runner = Rec::default();
        let plan_real = set_dock_position("left", false, dir.path(), &mut runner).unwrap();
        assert!(!plan_real.dry_run);
        assert_eq!(load_config(dir.path()).dock_position, "left");
        assert_eq!(runner.0.len(), 1, "the panel must really be moved");
        let argv = &runner.0[0];
        assert_eq!(argv[0], "qdbus6");
        assert_eq!(argv[3], "org.kde.PlasmaShell.evaluateScript");
        assert!(argv[4].contains("location = 'left'"), "{}", argv[4]);
        assert!(
            argv[4].contains("!== 'top'"),
            "the top bar must never be moved"
        );
    }

    #[test]
    fn dock_script_targets_the_non_top_panel_only() {
        for (pos, expected) in [
            ("bottom", "'bottom'"),
            ("left", "'left'"),
            ("right", "'right'"),
        ] {
            let s = dock_script(pos);
            assert!(s.contains(expected), "{}", s);
            assert!(s.contains("ps[i].location !== 'top'"));
            assert!(s.contains("break"), "only one panel should move");
        }
    }
}
