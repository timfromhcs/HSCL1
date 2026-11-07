//! `hscl ai serve`: typed options -> the exact `llama-server` argv, printed and never executed.
//!
//! Safe by construction (same idea as `lab.rs`): the host is fixed to 127.0.0.1, the API key is passed as a key FILE (never as text),
//! there is no field that can add `--tools`, MCP proxy flags, another host, or arbitrary extra flags, the model must live inside the
//! model storage directory, and the defaults are the measured ones from docs/research/2026-11-06-local-subagents-prism-bonsai-turboquant.md:
//! thinking off, K cache q8_0, V cache q4_0, 4096 context, one slot, small prompt cache, idle sleep.

use anyhow::{bail, Result};
use std::path::{Component, Path, PathBuf};

pub const HOST: &str = "127.0.0.1";
pub const MIN_PORT: u16 = 1024;
pub const MIN_CTX: u32 = 512;
pub const MAX_CTX: u32 = 262_144;
pub const MAX_ROUTER_MODELS: u32 = 2;

#[derive(Debug, Clone)]
pub struct ServeOpts {
    pub model: PathBuf,
    pub port: u16,
    pub ctx: u32,
    pub api_key_file: PathBuf,
    pub router_dir: Option<PathBuf>,
    pub models_max: Option<u32>,
    pub metrics: bool,
    /// `--load-mode`: how the backend loads the model (`auto`, `none`, `mmap`, `mlock`, `mmap+mlock`, `dio`).
    /// Verified against llama.cpp build 12128/12130 `--help` (2026-11-07): the old
    /// `--mmap`/`--no-mmap`/`--mlock` flags were replaced by this one, and its `auto` disables mmap on Vulkan
    /// iGPUs, which is why the profile can pin `mmap` explicitly on such a machine.
    pub load_mode: Option<String>,
    /// `-nkvo/--no-kv-offload`: keep the KV cache in system RAM while the weights stay on the GPU. That is the
    /// lever that frees GPU-accessible memory on a shared-memory APU at the cost of prefill speed.
    pub kv_in_ram: bool,
    /// `-md/--spec-draft-model`: a small model used for speculative decoding. Only meaningful with a draft that
    /// shares the tokenizer; the command prints the flag and the user decides (never started here).
    pub draft_model: Option<PathBuf>,
    /// `--spec-draft-n-max`: how many tokens the draft may propose per step (llama.cpp default is 3).
    pub draft_max: Option<u32>,
}

/// Characters allowed in paths that end up in a command line the user may copy and paste: no quotes, `$`, backticks, `;`, `|`,
/// `&`, redirections, globs or newlines. Spaces and Windows drive/backslash forms are fine because every value is one argv element.
fn path_text(p: &Path, what: &str) -> Result<String> {
    let s = p
        .to_str()
        .ok_or_else(|| anyhow::anyhow!("{what}: path is not valid UTF-8"))?;
    if s.is_empty() {
        bail!("{what}: path is empty");
    }
    let ok = |c: char| c.is_alphanumeric() || " _.-/\\:()+@,=~".contains(c);
    if !s.chars().all(ok) {
        bail!("{what}: path contains a character that is not allowed in a copy-paste command line");
    }
    Ok(s.to_string())
}

/// Absolute (has a root), no `.`/`..`, and lexically below `base` (component-wise: `/a/ModelsEvil` is not below `/a/Models`).
fn inside(path: &Path, base: &Path) -> bool {
    path.has_root()
        && !path
            .components()
            .any(|c| matches!(c, Component::ParentDir | Component::CurDir))
        && path.starts_with(base)
}

pub fn serve_argv(o: &ServeOpts, models_dir: &Path) -> Result<Vec<String>> {
    if o.port < MIN_PORT {
        bail!("port must be {MIN_PORT} or higher");
    }
    if !(MIN_CTX..=MAX_CTX).contains(&o.ctx) {
        bail!("ctx must be between {MIN_CTX} and {MAX_CTX}");
    }
    let key = path_text(&o.api_key_file, "api key file")?;
    if key.starts_with('-') {
        bail!("api key file must not start with '-'");
    }
    let mut a: Vec<String> = vec!["llama-server".into()];
    match &o.router_dir {
        Some(dir) => {
            let d = path_text(dir, "router dir")?;
            if !inside(dir, models_dir) {
                bail!("router dir must be inside the model storage directory");
            }
            let n = o.models_max.unwrap_or(1);
            if !(1..=MAX_ROUTER_MODELS).contains(&n) {
                bail!("models-max must be 1 or {MAX_ROUTER_MODELS} (RAM discipline: one big model at a time)");
            }
            a.extend([
                "--models-dir".into(),
                d,
                "--models-max".into(),
                n.to_string(),
            ]);
        }
        None => {
            if o.models_max.is_some() {
                bail!("models-max only applies to router mode (--router-dir)");
            }
            let m = path_text(&o.model, "model")?;
            let name = o.model.file_name().and_then(|n| n.to_str()).unwrap_or("");
            let is_gguf = o
                .model
                .extension()
                .and_then(|e| e.to_str())
                .is_some_and(|e| e.eq_ignore_ascii_case("gguf"));
            if !is_gguf || name.starts_with('-') {
                bail!("model must be a .gguf file whose name does not start with '-'");
            }
            if !inside(&o.model, models_dir) {
                bail!("model must be inside the model storage directory");
            }
            a.extend(["-m".into(), m]);
        }
    }
    a.extend(
        [
            "--host",
            HOST,
            "--port",
            &o.port.to_string(),
            "-c",
            &o.ctx.to_string(),
            "-ngl",
            "99",
            "-fa",
            "on",
            "-ctk",
            "q8_0",
            "-ctv",
            "q4_0",
            "-np",
            "1",
            "-ub",
            "256",
            "-cram",
            "1024",
            "--jinja",
            "-rea",
            "off",
            "--reasoning-format",
            "deepseek",
            "--sleep-idle-seconds",
            "600",
            "--no-warmup",
            "--api-key-file",
            &key,
        ]
        .map(String::from),
    );
    if let Some(mode) = &o.load_mode {
        let allowed = ["auto", "none", "mmap", "mlock", "mmap+mlock", "dio"];
        if !allowed.contains(&mode.as_str()) {
            bail!("load mode must be one of: {}", allowed.join(", "));
        }
        a.extend(["--load-mode".into(), mode.clone()]);
    }
    if o.kv_in_ram {
        a.push("-nkvo".into());
    }
    match (&o.draft_model, o.draft_max) {
        (Some(draft), n) => {
            let d = path_text(draft, "draft model")?;
            let name = draft.file_name().and_then(|x| x.to_str()).unwrap_or("");
            if !draft
                .extension()
                .and_then(|e| e.to_str())
                .is_some_and(|e| e.eq_ignore_ascii_case("gguf"))
                || name.starts_with('-')
            {
                bail!("draft model must be a .gguf file whose name does not start with '-'");
            }
            if !inside(draft, models_dir) {
                bail!("draft model must be inside the model storage directory");
            }
            a.extend(["-md".into(), d]);
            let n = n.unwrap_or(3);
            if !(1..=16).contains(&n) {
                bail!("spec-draft-n-max must be between 1 and 16");
            }
            a.extend(["--spec-draft-n-max".into(), n.to_string()]);
        }
        (None, Some(_)) => bail!("--draft-max only applies with --draft-model"),
        (None, None) => {}
    }
    if o.metrics {
        a.push("--metrics".into());
    }
    Ok(a)
}

/// One line for humans: arguments with anything unusual are single-quoted (a `'` becomes `'\''`).
pub fn render(argv: &[String]) -> String {
    let plain = |s: &str| {
        !s.is_empty()
            && s.chars()
                .all(|c| c.is_alphanumeric() || "_@%+=:,./-".contains(c))
    };
    argv.iter()
        .map(|s| {
            if plain(s) {
                s.clone()
            } else {
                format!("'{}'", s.replace('\'', "'\\''"))
            }
        })
        .collect::<Vec<_>>()
        .join(" ")
}

#[cfg(test)]
mod tests {
    use super::*;

    fn dir() -> PathBuf {
        PathBuf::from("/home/u/AI/Models")
    }

    fn opts() -> ServeOpts {
        ServeOpts {
            model: dir().join("bonsai-9b.gguf"),
            port: 8081,
            ctx: 4096,
            api_key_file: PathBuf::from("/home/u/.config/hscl/ai-server.key"),
            router_dir: None,
            models_max: None,
            metrics: false,
            load_mode: None,
            kv_in_ram: false,
            draft_model: None,
            draft_max: None,
        }
    }

    fn argv(o: &ServeOpts) -> Vec<String> {
        serve_argv(o, &dir()).unwrap()
    }

    fn value_of<'a>(a: &'a [String], flag: &str) -> Option<&'a str> {
        a.iter()
            .position(|x| x == flag)
            .and_then(|i| a.get(i + 1))
            .map(String::as_str)
    }

    #[test]
    fn default_command_uses_the_measured_settings() {
        let a = argv(&opts());
        assert_eq!(a[0], "llama-server");
        let want = dir().join("bonsai-9b.gguf").display().to_string(); // join uses the platform separator
        assert_eq!(value_of(&a, "-m"), Some(want.as_str()));
        assert_eq!(value_of(&a, "--host"), Some("127.0.0.1"));
        assert_eq!(value_of(&a, "--port"), Some("8081"));
        assert_eq!(value_of(&a, "-c"), Some("4096"));
        assert_eq!(value_of(&a, "-ctk"), Some("q8_0"));
        assert_eq!(value_of(&a, "-ctv"), Some("q4_0"));
        assert_eq!(value_of(&a, "-rea"), Some("off"));
        assert_eq!(value_of(&a, "--reasoning-format"), Some("deepseek"));
        assert_eq!(value_of(&a, "-np"), Some("1"));
        assert_eq!(value_of(&a, "-cram"), Some("1024"));
        assert_eq!(value_of(&a, "--sleep-idle-seconds"), Some("600"));
        assert!(a.contains(&"--jinja".to_string()) && a.contains(&"-fa".to_string()));
    }

    #[test]
    fn the_key_is_passed_as_a_file_and_never_as_text() {
        let a = argv(&opts());
        assert_eq!(
            value_of(&a, "--api-key-file"),
            Some("/home/u/.config/hscl/ai-server.key")
        );
        assert!(
            !a.iter().any(|x| x == "--api-key"),
            "no --api-key with a value on the command line"
        );
    }

    #[test]
    fn metrics_only_when_asked() {
        assert!(!argv(&opts()).contains(&"--metrics".to_string()));
        let mut o = opts();
        o.metrics = true;
        assert!(argv(&o).contains(&"--metrics".to_string()));
    }

    #[test]
    fn privileged_and_low_ports_are_refused() {
        for p in [0u16, 1, 80, 1023] {
            let mut o = opts();
            o.port = p;
            assert!(serve_argv(&o, &dir()).is_err(), "port {p}");
        }
        let mut o = opts();
        o.port = 1024;
        assert!(serve_argv(&o, &dir()).is_ok());
    }

    #[test]
    fn context_must_be_in_range() {
        for c in [0u32, 511, 262_145, u32::MAX] {
            let mut o = opts();
            o.ctx = c;
            assert!(serve_argv(&o, &dir()).is_err(), "ctx {c}");
        }
        for c in [512u32, 262_144] {
            let mut o = opts();
            o.ctx = c;
            assert!(serve_argv(&o, &dir()).is_ok(), "ctx {c}");
        }
    }

    #[test]
    fn model_must_be_a_gguf_inside_the_model_storage() {
        let bad = [
            "/etc/passwd",
            "/home/u/AI/Models/../../.ssh/id_rsa.gguf",
            "/home/u/AI/Models/x.bin",
            "/home/u/AI/Models/-x.gguf",
            "/home/u/AI/Models/a\nb.gguf",
            "/home/u/AI/Models/a\0b.gguf",
            "/home/u/AI/ModelsEvil/x.gguf",
            "relative/x.gguf",
            "",
        ];
        for m in bad {
            let mut o = opts();
            o.model = PathBuf::from(m);
            assert!(serve_argv(&o, &dir()).is_err(), "{m:?}");
        }
    }

    #[test]
    fn router_mode_uses_models_dir_inside_storage_and_no_model_flag() {
        let mut o = opts();
        o.router_dir = Some(dir().join("coders"));
        o.models_max = Some(2);
        let a = argv(&o);
        let want = dir().join("coders").display().to_string();
        assert_eq!(value_of(&a, "--models-dir"), Some(want.as_str()));
        assert_eq!(value_of(&a, "--models-max"), Some("2"));
        assert!(!a.contains(&"-m".to_string()));
        o.router_dir = Some(PathBuf::from("/etc"));
        assert!(serve_argv(&o, &dir()).is_err());
        o.router_dir = Some(dir());
        o.models_max = Some(3);
        assert!(
            serve_argv(&o, &dir()).is_err(),
            "more than 2 resident models is refused"
        );
        o.models_max = Some(0);
        assert!(serve_argv(&o, &dir()).is_err());
    }

    #[test]
    fn seeded_fuzz_never_produces_a_forbidden_flag_or_a_foreign_host() {
        let forbidden = [
            "--tools",
            "--webui-mcp-proxy",
            "--ui-mcp-proxy",
            "--api-key",
            "--path",
            "--public-path",
            "--ssl-key-file",
        ];
        let mut x: u64 = 0x9E3779B97F4A7C15;
        let pieces = [
            "a", "b", "..", "-", "--tools", "x y", "é", "\n", "$(id)", ";", "|", "models", "k.gguf",
        ];
        for _ in 0..5000 {
            let mut next = || {
                x ^= x << 13;
                x ^= x >> 7;
                x ^= x << 17;
                x
            };
            let mut m = String::from("/home/u/AI/Models/");
            for _ in 0..(1 + next() % 4) {
                m.push_str(pieces[(next() % pieces.len() as u64) as usize]);
                if next() % 3 == 0 {
                    m.push('/');
                }
            }
            if next() % 2 == 0 {
                m.push_str(".gguf");
            }
            let mut o = opts();
            o.model = PathBuf::from(&m);
            o.port = (next() % 65536) as u16;
            o.ctx = (next() % 400_000) as u32;
            if let Ok(a) = serve_argv(&o, &dir()) {
                for f in forbidden {
                    assert!(!a.iter().any(|v| v == f), "{f} in {a:?} for {m:?}");
                }
                assert_eq!(value_of(&a, "--host"), Some("127.0.0.1"));
                assert!(!a.iter().any(|v| v.contains('\n') || v.contains('\0')));
            }
        }
    }
}

#[cfg(test)]
mod offload_tests {
    //! Options verified against llama.cpp build 12128/12130 `--help` (2026-11-07): `--load-mode` replaced
    //! `--mmap/--no-mmap/--mlock`, `-nkvo` keeps the KV cache in system RAM, and speculative decoding is
    //! `-md` + `--spec-draft-n-max`.
    use super::*;

    fn dir() -> PathBuf {
        PathBuf::from("/home/u/AI/Models")
    }

    fn opts() -> ServeOpts {
        ServeOpts {
            model: dir().join("bonsai-9b.gguf"),
            port: 8081,
            ctx: 4096,
            api_key_file: PathBuf::from("/home/u/.config/hscl/ai-server.key"),
            router_dir: None,
            models_max: None,
            metrics: false,
            load_mode: None,
            kv_in_ram: false,
            draft_model: None,
            draft_max: None,
        }
    }

    #[test]
    fn the_default_command_carries_no_offload_overrides() {
        let a = serve_argv(&opts(), &dir()).unwrap();
        assert!(!a
            .iter()
            .any(|x| x == "--load-mode" || x == "-nkvo" || x == "-md"));
    }

    #[test]
    fn a_load_mode_is_validated_and_passed_through_once() {
        let mut o = opts();
        o.load_mode = Some("mmap".into());
        let a = serve_argv(&o, &dir()).unwrap();
        assert_eq!(a.iter().filter(|x| *x == "--load-mode").count(), 1);
        assert_eq!(
            a[a.iter().position(|x| x == "--load-mode").unwrap() + 1],
            "mmap"
        );
        o.load_mode = Some("always".into());
        assert!(
            serve_argv(&o, &dir()).is_err(),
            "an unknown load mode must be refused, not guessed"
        );
    }

    #[test]
    fn kv_in_ram_adds_the_no_kv_offload_flag() {
        let mut o = opts();
        o.kv_in_ram = true;
        let a = serve_argv(&o, &dir()).unwrap();
        assert_eq!(a.iter().filter(|x| *x == "-nkvo").count(), 1);
    }

    #[test]
    fn a_draft_model_must_stay_inside_the_storage_and_is_passed_with_its_budget() {
        let mut o = opts();
        o.draft_model = Some(dir().join("draft-small.gguf"));
        o.draft_max = Some(4);
        let a = serve_argv(&o, &dir()).unwrap();
        let i = a.iter().position(|x| x == "-md").expect("-md");
        assert!(a[i + 1].ends_with("draft-small.gguf"));
        let j = a
            .iter()
            .position(|x| x == "--spec-draft-n-max")
            .expect("budget");
        assert_eq!(a[j + 1], "4");
        // Same rules as the main model: gguf, inside the storage, no leading dash.
        o.draft_model = Some(PathBuf::from("/etc/passwd.gguf"));
        assert!(serve_argv(&o, &dir()).is_err());
        o.draft_model = Some(dir().join("-evil.gguf"));
        assert!(serve_argv(&o, &dir()).is_err());
    }

    #[test]
    fn a_draft_budget_without_a_draft_model_is_refused() {
        let mut o = opts();
        o.draft_max = Some(3);
        assert!(serve_argv(&o, &dir()).is_err());
    }

    #[test]
    fn the_default_draft_budget_matches_upstream() {
        let mut o = opts();
        o.draft_model = Some(dir().join("draft-small.gguf"));
        let a = serve_argv(&o, &dir()).unwrap();
        let j = a
            .iter()
            .position(|x| x == "--spec-draft-n-max")
            .expect("budget");
        assert_eq!(a[j + 1], "3", "llama.cpp's documented default");
    }
}
