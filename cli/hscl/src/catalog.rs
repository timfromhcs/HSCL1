//! Model catalog (ai/catalog/models.json, generated from the Hugging Face API by scripts/build_model_catalog.py).
//! The catalog is embedded at build time; `HSCL_MODEL_CATALOG` overrides it for development and tests.

use anyhow::{bail, Context, Result};
use serde::{Deserialize, Serialize};

const EMBEDDED: &str = include_str!("../../../ai/catalog/models.json");

#[derive(Debug, Clone, Deserialize, Serialize, PartialEq)]
pub struct Mmproj {
    pub file: String,
    pub size_bytes: u64,
    pub sha256: String,
}

#[derive(Debug, Clone, Deserialize, Serialize, PartialEq)]
pub struct Model {
    pub id: String,
    pub repo: String,
    pub file: String,
    pub size_bytes: u64,
    pub sha256: String,
    pub quant: String,
    pub tier: String,
    pub role: String,
    pub variant: String,
    pub base_model: String,
    pub licence: String,
    pub mtp: bool,
    pub min_ram_gb: u64,
    pub warning: String,
    pub source_url: Option<String>,
    pub mmproj: Option<Mmproj>,
}

#[derive(Deserialize)]
struct File {
    models: Vec<Model>,
}

pub fn parse(text: &str) -> Result<Vec<Model>> {
    let f: File = serde_json::from_str(text).context("model catalog is not valid JSON")?;
    for m in &f.models {
        validate(m)?;
    }
    Ok(f.models)
}

/// Structural checks every entry must pass before it is ever used for a download.
pub fn validate(m: &Model) -> Result<()> {
    if m.sha256.len() != 64 || !m.sha256.bytes().all(|b| b.is_ascii_hexdigit()) {
        bail!("{}: sha256 must be 64 hex characters", m.id);
    }
    if !m.file.ends_with(".gguf")
        || m.file.contains('/')
        || m.file.contains("..")
        || m.file.contains('\\')
    {
        bail!("{}: file must be a plain .gguf file name", m.id);
    }
    if m.repo.matches('/').count() != 1 || m.repo.contains("..") {
        bail!("{}: repo must be owner/name", m.id);
    }
    if m.licence.is_empty() || m.licence == "unknown" {
        bail!("{}: licence unknown", m.id);
    }
    if m.variant == "abliterated" && m.warning.is_empty() {
        bail!("{}: abliterated entries must carry the warning text", m.id);
    }
    Ok(())
}

pub fn load() -> Result<Vec<Model>> {
    match std::env::var_os("HSCL_MODEL_CATALOG") {
        Some(p) => parse(
            &std::fs::read_to_string(&p)
                .with_context(|| format!("cannot read {}", std::path::Path::new(&p).display()))?,
        ),
        None => parse(EMBEDDED),
    }
}

pub fn find<'a>(models: &'a [Model], id: &str) -> Result<&'a Model> {
    models
        .iter()
        .find(|m| m.id == id)
        .with_context(|| format!("unknown model id {id:?}; run `hscl ai model list`"))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn embedded_catalog_is_valid_and_complete() {
        let m = parse(EMBEDDED).unwrap();
        assert!(m.len() >= 6);
        for e in &m {
            assert!(e.size_bytes > 100_000_000, "{}", e.id);
            assert_eq!(
                e.licence, "apache-2.0",
                "licences are reviewed before an entry is added: {}",
                e.id
            );
            assert!(
                e.min_ram_gb as f64 * 1e9 > e.size_bytes as f64,
                "{}: min_ram must exceed the file size",
                e.id
            );
        }
        let ids: std::collections::BTreeSet<_> = m.iter().map(|e| &e.id).collect();
        assert_eq!(ids.len(), m.len(), "ids are unique");
    }

    #[test]
    fn rejects_bad_entries() {
        let mut m = parse(EMBEDDED).unwrap().remove(0);
        for mutate in [
            (|m: &mut Model| m.sha256 = "abc".into()) as fn(&mut Model),
            |m| m.file = "../evil.gguf".into(),
            |m| m.file = "model.bin".into(),
            |m| m.repo = "no-slash".into(),
            |m| m.licence = "unknown".into(),
            |m| m.warning.clear(),
        ] {
            let mut x = m.clone();
            mutate(&mut x);
            assert!(validate(&x).is_err());
        }
        m.variant = "original".into();
        m.warning.clear();
        assert!(
            validate(&m).is_ok(),
            "non-abliterated entries need no warning"
        );
    }

    #[test]
    fn find_reports_unknown_ids() {
        let m = parse(EMBEDDED).unwrap();
        assert!(find(&m, "qwen3.5-4b-abliterated").is_ok());
        assert!(find(&m, "nope").is_err());
    }
}
