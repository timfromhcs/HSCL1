//! `hscl code` - HCS Coder: install and configure open-source coding agents for the local model server.
//!
//! Tools are installed into the user's home (npm prefix `~/.local`, pipx) - never system-wide and never with root. A tool whose
//! licence is not confirmed needs an explicit flag. Upstream names and licences are always shown ("powered by ...").
//! Config files that the user already owns are never overwritten.

use crate::appearance::Runner;
use anyhow::{bail, Context, Result};
use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use std::path::{Path, PathBuf};

const CATALOG: &str = include_str!("../../../tools/catalog/coding.json");
const AGENTS_TEMPLATE: &str = include_str!("../../../tools/hcscoder/AGENTS.hcs.md");

#[derive(Debug, Clone, Deserialize, Serialize, PartialEq)]
pub struct Install {
    pub kind: String,
    pub package: String,
}

#[derive(Debug, Clone, Deserialize, Serialize, PartialEq)]
pub struct Tool {
    pub id: String,
    pub name: String,
    pub licence: String,
    pub licence_confirmed: bool,
    pub install: Install,
    pub bin: String,
    pub homepage: String,
    pub default: bool,
    pub notes: String,
}

#[derive(Deserialize)]
struct File {
    tools: Vec<Tool>,
}

pub fn catalog() -> Result<Vec<Tool>> {
    let f: File = serde_json::from_str(CATALOG).context("coding tool catalog is invalid")?;
    Ok(f.tools)
}

pub fn find<'a>(tools: &'a [Tool], id: &str) -> Result<&'a Tool> {
    tools
        .iter()
        .find(|t| t.id == id)
        .with_context(|| format!("unknown coding tool {id:?}; run `hscl code list`"))
}

fn plain_pkg(p: &str) -> bool {
    !p.is_empty()
        && p.bytes()
            .all(|b| b.is_ascii_alphanumeric() || matches!(b, b'-' | b'_' | b'.' | b'@' | b'/'))
}

/// Fixed argument vector that installs a tool for the current user.
pub fn install_command(t: &Tool, home: &Path, accept_unconfirmed: bool) -> Result<Vec<String>> {
    if !t.licence_confirmed && !accept_unconfirmed {
        bail!("{}: licence not confirmed ({}). Check {} and re-run with --accept-unconfirmed-licence if it is acceptable.", t.name, t.licence, t.homepage);
    }
    if !plain_pkg(&t.install.package) && t.install.kind != "manual" {
        bail!("{}: unsafe package name", t.id);
    }
    Ok(match t.install.kind.as_str() {
        "npm" => vec![
            "npm".into(),
            "install".into(),
            "-g".into(),
            "--prefix".into(),
            home.join(".local").display().to_string(),
            t.install.package.clone(),
        ],
        "pipx" => vec!["pipx".into(), "install".into(), t.install.package.clone()],
        _ => bail!("{} has no automatic installer; see {}", t.name, t.homepage),
    })
}

pub fn banner(t: &Tool) -> String {
    format!("HCS Coder - powered by {} ({}) - {}\nMade with love by hcsmedia. {} is a third-party project; its licence and copyright stay with its authors.", t.name, t.licence, t.homepage, t.name)
}

/// OpenCode configuration: the local OpenAI-compatible provider and the `hscl` MCP server (format per the OpenCode docs; verify with `opencode`).
pub fn opencode_config(port: u16, model_label: &str) -> Value {
    json!({
        "$schema": "https://opencode.ai/config.json",
        "_hcs_managed": true,
        "provider": {"hcs-local": {"npm": "@ai-sdk/openai-compatible", "name": "HCS local model", "options": {"baseURL": format!("http://127.0.0.1:{port}/v1")}, "models": {"local": {"name": model_label}}}},
        "model": "hcs-local/local",
        "mcp": {"hscl": {"type": "local", "command": ["hscl", "mcp"], "enabled": true}}
    })
}

/// Environment for every OpenAI-compatible coding tool (loopback only).
pub fn tool_env(port: u16) -> Vec<(String, String)> {
    vec![
        (
            "OPENAI_BASE_URL".into(),
            format!("http://127.0.0.1:{port}/v1"),
        ),
        (
            "OPENAI_API_BASE".into(),
            format!("http://127.0.0.1:{port}/v1"),
        ),
        ("OPENAI_API_KEY".into(), "hcs-local".into()),
        ("OPENAI_MODEL".into(), "local".into()),
    ]
}

/// Write a file only when it does not exist or is HCS-managed; otherwise write `<name>.hcs` next to it. Returns the path written.
pub fn write_managed(path: &Path, content: &str, marker: &str) -> Result<PathBuf> {
    if let Some(dir) = path.parent() {
        std::fs::create_dir_all(dir)?;
    }
    let target = match std::fs::read_to_string(path) {
        Ok(existing) if !existing.contains(marker) => {
            let mut alt = path.as_os_str().to_owned();
            alt.push(".hcs");
            PathBuf::from(alt)
        }
        _ => path.to_path_buf(),
    };
    std::fs::write(&target, content)?;
    Ok(target)
}

/// Write the OpenCode config and the HCS agent notes into the user's config directory.
pub fn setup(home: &Path, port: u16, model_label: &str) -> Result<Vec<PathBuf>> {
    let dir = home.join(".config").join("opencode");
    let cfg = write_managed(
        &dir.join("opencode.json"),
        &serde_json::to_string_pretty(&opencode_config(port, model_label))?,
        "_hcs_managed",
    )?;
    let notes = write_managed(
        &dir.join("AGENTS.md"),
        AGENTS_TEMPLATE,
        "HCS Coder - system notes",
    )?;
    Ok(vec![cfg, notes])
}

pub fn installed(t: &Tool, home: &Path) -> bool {
    let local = home.join(".local").join("bin").join(&t.bin);
    local.exists()
        || std::env::var_os("PATH").is_some_and(|p| {
            std::env::split_paths(&p)
                .any(|d| d.join(&t.bin).exists() || d.join(format!("{}.exe", t.bin)).exists())
        })
}

pub fn run_install(t: &Tool, home: &Path, accept: bool, runner: &mut dyn Runner) -> Result<()> {
    let argv = install_command(t, home, accept)?;
    runner.run(&argv)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn tools() -> Vec<Tool> {
        catalog().unwrap()
    }

    #[test]
    fn catalog_is_valid_with_one_default_and_licences_stated() {
        let t = tools();
        assert!(t.len() >= 6);
        assert_eq!(t.iter().filter(|x| x.default).count(), 1);
        assert_eq!(t.iter().find(|x| x.default).unwrap().id, "opencode");
        for x in &t {
            assert!(
                !x.licence.is_empty() && x.homepage.starts_with("https://"),
                "{}",
                x.id
            );
        }
        let ids: std::collections::BTreeSet<_> = t.iter().map(|x| &x.id).collect();
        assert_eq!(ids.len(), t.len());
    }

    #[test]
    fn unconfirmed_licence_needs_an_explicit_flag() {
        let t = tools();
        let q = find(&t, "qwen-code").unwrap();
        assert!(!q.licence_confirmed);
        assert!(install_command(q, Path::new("/home/u"), false).is_err());
        assert!(install_command(q, Path::new("/home/u"), true).is_ok());
        assert!(
            install_command(find(&t, "opencode").unwrap(), Path::new("/home/u"), false).is_ok()
        );
    }

    #[test]
    fn installs_go_to_the_user_home_never_system_wide() {
        let t = tools();
        let c =
            install_command(find(&t, "opencode").unwrap(), Path::new("/home/u"), false).unwrap();
        assert_eq!(c[..4], ["npm", "install", "-g", "--prefix"]);
        assert!(c[4].ends_with(".local"));
        assert_eq!(
            install_command(find(&t, "aider").unwrap(), Path::new("/h"), true).unwrap(),
            ["pipx", "install", "aider-chat"]
        );
        assert!(!c.contains(&"sudo".to_string()));
    }

    #[test]
    fn manual_tools_have_no_automatic_installer() {
        let t = tools();
        assert!(install_command(find(&t, "goose").unwrap(), Path::new("/h"), true).is_err());
        assert!(install_command(find(&t, "crush").unwrap(), Path::new("/h"), true).is_err());
    }

    #[test]
    fn unsafe_package_names_are_rejected() {
        let mut t = tools().remove(0);
        t.install.package = "x; rm -rf /".into();
        assert!(install_command(&t, Path::new("/h"), true).is_err());
    }

    #[test]
    fn banner_credits_upstream_and_hcs() {
        let t = tools();
        let b = banner(find(&t, "opencode").unwrap());
        assert!(
            b.contains("powered by OpenCode")
                && b.contains("MIT")
                && b.contains("hcsmedia")
                && b.contains("third-party")
        );
    }

    #[test]
    fn opencode_config_points_at_loopback_and_registers_the_hscl_mcp() {
        let c = opencode_config(8080, "Qwen3.5 4B");
        assert_eq!(
            c["provider"]["hcs-local"]["options"]["baseURL"],
            "http://127.0.0.1:8080/v1"
        );
        assert_eq!(c["mcp"]["hscl"]["command"], json!(["hscl", "mcp"]));
        assert!(!c.to_string().contains("0.0.0.0"));
        assert!(tool_env(8080).iter().all(|(_, v)| !v.contains("0.0.0.0")));
    }

    #[test]
    fn setup_writes_config_and_never_overwrites_a_users_own_file() {
        let home = tempfile::tempdir().unwrap();
        let w = setup(home.path(), 8080, "x").unwrap();
        assert!(w[0].ends_with("opencode.json") && w[0].exists() && w[1].ends_with("AGENTS.md"));
        // re-running updates the managed file in place
        assert_eq!(setup(home.path(), 9090, "x").unwrap()[0], w[0]);
        assert!(std::fs::read_to_string(&w[0]).unwrap().contains("9090"));
        // a user-owned file is left alone
        let own = home.path().join(".config/opencode/opencode.json");
        std::fs::write(&own, r#"{"theme":"mine"}"#).unwrap();
        let w2 = setup(home.path(), 8080, "x").unwrap();
        assert!(w2[0].to_string_lossy().ends_with("opencode.json.hcs"));
        assert_eq!(
            std::fs::read_to_string(&own).unwrap(),
            r#"{"theme":"mine"}"#
        );
    }

    #[test]
    fn agent_notes_carry_the_safety_rules() {
        assert!(
            AGENTS_TEMPLATE.contains("destructive")
                && AGENTS_TEMPLATE.contains("secrets")
                && AGENTS_TEMPLATE.contains("abliterated")
        );
    }
}
