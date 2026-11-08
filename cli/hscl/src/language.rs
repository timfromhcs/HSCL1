//! Language configuration and switching for HSCL1 (AGENTS.md section 10.3).
//!
//! HSCL1 supports three Tier-1 languages: English (en), Deutsch (de), and Français (fr).
//! Language changes modify per-user configuration (~/.config/plasma-localerc and
//! ~/.config/locale.conf) without requiring root privileges, without reinstalling
//! the OS, and preserving all user data.

use anyhow::{Context, Result};
use serde::{Deserialize, Serialize};
use std::path::{Path, PathBuf};

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub struct SupportedLanguage {
    pub id: &'static str,
    pub name: &'static str,
    pub locale: &'static str,
    pub plasma_translations: &'static str,
}

pub const SUPPORTED: &[SupportedLanguage] = &[
    SupportedLanguage {
        id: "en",
        name: "English",
        locale: "en_US.UTF-8",
        plasma_translations: "en_US:en",
    },
    SupportedLanguage {
        id: "de",
        name: "Deutsch",
        locale: "de_DE.UTF-8",
        plasma_translations: "de_DE:de:en_US",
    },
    SupportedLanguage {
        id: "fr",
        name: "Français",
        locale: "fr_FR.UTF-8",
        plasma_translations: "fr_FR:fr:en_US",
    },
];

/// Resolve an input language specifier (e.g. "en", "de", "fr", "de_DE", "en_US.UTF-8")
/// to a supported language entry.
pub fn resolve_supported(lang_str: &str) -> Option<&'static SupportedLanguage> {
    let s = lang_str.trim().to_ascii_lowercase();
    let norm = s.strip_suffix(".utf-8").unwrap_or(&s);
    let base = norm.split(['_', '-']).next().unwrap_or(norm);

    SUPPORTED
        .iter()
        .find(|l| l.id == norm || l.id == base || l.locale.to_ascii_lowercase().starts_with(norm))
}

/// Directory where user desktop configuration lives (`~/.config`).
/// Overridden by `HSCL_CONFIG_DIR` (used in tests) or `XDG_CONFIG_HOME`.
pub fn config_dir() -> PathBuf {
    if let Some(d) = std::env::var_os("HSCL_CONFIG_DIR") {
        return PathBuf::from(d);
    }
    if let Some(x) = std::env::var_os("XDG_CONFIG_HOME") {
        return PathBuf::from(x);
    }
    PathBuf::from(std::env::var_os("HOME").unwrap_or_default()).join(".config")
}

pub fn plasma_localerc_path(cfg_dir: &Path) -> PathBuf {
    cfg_dir.join("plasma-localerc")
}

pub fn locale_conf_path(cfg_dir: &Path) -> PathBuf {
    cfg_dir.join("locale.conf")
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LanguageStatus {
    pub current: String,
    pub current_name: String,
    pub supported: Vec<String>,
    pub plasma_localerc: PathBuf,
    pub plasma_localerc_exists: bool,
    pub locale_conf: PathBuf,
    pub locale_conf_exists: bool,
    pub plasma_language: Option<String>,
    pub env_lang: Option<String>,
    pub env_language: Option<String>,
    pub system_default: String,
}

/// Inspect current language configuration from user files and process environment.
pub fn current_status(cfg_dir: &Path) -> LanguageStatus {
    let p_path = plasma_localerc_path(cfg_dir);
    let l_path = locale_conf_path(cfg_dir);

    let plasma_exists = p_path.is_file();
    let locale_exists = l_path.is_file();

    let mut detected_code: Option<String> = None;
    let mut plasma_lang: Option<String> = None;

    if plasma_exists {
        if let Ok(content) = std::fs::read_to_string(&p_path) {
            for line in content.lines() {
                let trimmed = line.trim();
                if let Some(rest) = trimmed.strip_prefix("LANGUAGE=") {
                    let val = rest.trim();
                    plasma_lang = Some(val.to_string());
                    if detected_code.is_none() {
                        if let Some(sup) = resolve_supported(val) {
                            detected_code = Some(sup.id.to_string());
                        }
                    }
                } else if detected_code.is_none() {
                    if let Some(rest) = trimmed.strip_prefix("LANG=") {
                        let val = rest.trim();
                        if let Some(sup) = resolve_supported(val) {
                            detected_code = Some(sup.id.to_string());
                        }
                    }
                }
            }
        }
    }

    if detected_code.is_none() && locale_exists {
        if let Ok(content) = std::fs::read_to_string(&l_path) {
            for line in content.lines() {
                let trimmed = line.trim();
                if let Some(rest) = trimmed.strip_prefix("LANGUAGE=") {
                    let val = rest.trim().trim_matches('"');
                    if let Some(sup) = resolve_supported(val) {
                        detected_code = Some(sup.id.to_string());
                        break;
                    }
                } else if let Some(rest) = trimmed.strip_prefix("LANG=") {
                    let val = rest.trim().trim_matches('"');
                    if let Some(sup) = resolve_supported(val) {
                        detected_code = Some(sup.id.to_string());
                        break;
                    }
                }
            }
        }
    }

    let env_language = std::env::var("LANGUAGE").ok();
    let env_lang = std::env::var("LANG").ok();

    if detected_code.is_none() {
        if let Some(ref val) = env_language {
            if let Some(sup) = resolve_supported(val) {
                detected_code = Some(sup.id.to_string());
            }
        }
    }

    if detected_code.is_none() {
        if let Some(ref val) = env_lang {
            if let Some(sup) = resolve_supported(val) {
                detected_code = Some(sup.id.to_string());
            }
        }
    }

    let current = detected_code.unwrap_or_else(|| "en".to_string());
    let current_name = resolve_supported(&current)
        .map(|s| s.name.to_string())
        .unwrap_or_else(|| current.clone());

    LanguageStatus {
        current,
        current_name,
        supported: SUPPORTED.iter().map(|l| l.id.to_string()).collect(),
        plasma_localerc: p_path,
        plasma_localerc_exists: plasma_exists,
        locale_conf: l_path,
        locale_conf_exists: locale_exists,
        plasma_language: plasma_lang,
        env_lang,
        env_language,
        system_default: "en_US.UTF-8".to_string(),
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LanguagePlanFile {
    pub path: PathBuf,
    pub content: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SetLanguagePlan {
    pub lang: String,
    pub name: String,
    pub locale: String,
    pub plasma_translations: String,
    pub files: Vec<LanguagePlanFile>,
}

/// Create the plan for switching the user language to `target_lang`.
pub fn plan_set(cfg_dir: &Path, target_lang: &SupportedLanguage) -> SetLanguagePlan {
    let plasma_path = plasma_localerc_path(cfg_dir);
    let locale_path = locale_conf_path(cfg_dir);

    let plasma_content = format!(
        "[Formats]\nLANG={}\n\n[Translations]\nLANGUAGE={}\n",
        target_lang.locale, target_lang.plasma_translations
    );

    let locale_content = format!(
        "LANG=\"{}\"\nLANGUAGE=\"{}\"\n",
        target_lang.locale, target_lang.plasma_translations
    );

    SetLanguagePlan {
        lang: target_lang.id.to_string(),
        name: target_lang.name.to_string(),
        locale: target_lang.locale.to_string(),
        plasma_translations: target_lang.plasma_translations.to_string(),
        files: vec![
            LanguagePlanFile {
                path: plasma_path,
                content: plasma_content,
            },
            LanguagePlanFile {
                path: locale_path,
                content: locale_content,
            },
        ],
    }
}

/// Apply a planned language switch by writing configuration files.
pub fn apply_plan(plan: &SetLanguagePlan) -> Result<Vec<PathBuf>> {
    let mut written = Vec::new();
    for f in &plan.files {
        if let Some(parent) = f.path.parent() {
            std::fs::create_dir_all(parent)
                .with_context(|| format!("creating directory {}", parent.display()))?;
        }
        std::fs::write(&f.path, &f.content)
            .with_context(|| format!("writing {}", f.path.display()))?;
        written.push(f.path.clone());
    }
    Ok(written)
}

/// Validate and switch language.
pub fn set_language(
    cfg_dir: &Path,
    lang_input: &str,
    dry_run: bool,
) -> Result<(SetLanguagePlan, Option<Vec<PathBuf>>)> {
    let sup = resolve_supported(lang_input).ok_or_else(|| {
        anyhow::anyhow!(
            "unsupported language '{}'. Supported languages: {}",
            lang_input,
            SUPPORTED
                .iter()
                .map(|l| l.id)
                .collect::<Vec<_>>()
                .join(", ")
        )
    })?;

    let plan = plan_set(cfg_dir, sup);
    if dry_run {
        Ok((plan, None))
    } else {
        let written = apply_plan(&plan)?;
        Ok((plan, Some(written)))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn resolves_supported_languages() {
        assert_eq!(resolve_supported("en").map(|s| s.id), Some("en"));
        assert_eq!(resolve_supported("de").map(|s| s.id), Some("de"));
        assert_eq!(resolve_supported("fr").map(|s| s.id), Some("fr"));

        assert_eq!(resolve_supported("EN").map(|s| s.id), Some("en"));
        assert_eq!(resolve_supported("de_DE").map(|s| s.id), Some("de"));
        assert_eq!(resolve_supported("fr_FR.UTF-8").map(|s| s.id), Some("fr"));
        assert_eq!(resolve_supported("de-DE").map(|s| s.id), Some("de"));

        assert!(resolve_supported("es").is_none());
        assert!(resolve_supported("it").is_none());
        assert!(resolve_supported("ru").is_none());
    }

    #[test]
    fn dry_run_does_not_create_files() {
        let tmp = tempfile::tempdir().unwrap();
        let (plan, written) = set_language(tmp.path(), "de", true).unwrap();
        assert!(written.is_none());
        assert_eq!(plan.lang, "de");
        assert_eq!(plan.locale, "de_DE.UTF-8");
        assert!(!plasma_localerc_path(tmp.path()).exists());
        assert!(!locale_conf_path(tmp.path()).exists());
    }

    #[test]
    fn apply_creates_expected_configuration_files() {
        let tmp = tempfile::tempdir().unwrap();
        let (plan, written) = set_language(tmp.path(), "fr", false).unwrap();
        assert!(written.is_some());
        assert_eq!(plan.lang, "fr");

        let p_path = plasma_localerc_path(tmp.path());
        let l_path = locale_conf_path(tmp.path());
        assert!(p_path.is_file());
        assert!(l_path.is_file());

        let p_content = std::fs::read_to_string(&p_path).unwrap();
        assert!(p_content.contains("LANG=fr_FR.UTF-8"));
        assert!(p_content.contains("LANGUAGE=fr_FR:fr:en_US"));

        let l_content = std::fs::read_to_string(&l_path).unwrap();
        assert!(l_content.contains("LANG=\"fr_FR.UTF-8\""));
        assert!(l_content.contains("LANGUAGE=\"fr_FR:fr:en_US\""));

        let status = current_status(tmp.path());
        assert_eq!(status.current, "fr");
        assert_eq!(status.current_name, "Français");
        assert!(status.plasma_localerc_exists);
        assert!(status.locale_conf_exists);
    }

    #[test]
    fn rejects_unsupported_language() {
        let tmp = tempfile::tempdir().unwrap();
        let res = set_language(tmp.path(), "es", false);
        assert!(res.is_err());
        assert!(res
            .unwrap_err()
            .to_string()
            .contains("unsupported language 'es'"));
    }
}
