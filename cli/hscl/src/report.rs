//! `hscl report [--output PATH]` - a support report with identifying values redacted by default.

use crate::{doctor, redact, security, sysinfo};
use anyhow::{bail, Context, Result};
use serde_json::{json, Value};
use std::io::Write;
use std::path::Path;

/// Redact every string leaf of a JSON value (user, host, MAC and private IPv4 addresses).
pub fn redact_value(v: &mut Value, user: &str, host: &str) {
    match v {
        Value::String(s) => *s = redact::redact(s, user, host),
        Value::Array(a) => a.iter_mut().for_each(|x| redact_value(x, user, host)),
        Value::Object(o) => o.values_mut().for_each(|x| redact_value(x, user, host)),
        _ => {}
    }
}

fn identity() -> (String, String) {
    let user = ["USER", "USERNAME", "LOGNAME"]
        .iter()
        .find_map(|k| std::env::var(k).ok())
        .unwrap_or_default();
    let host = std::fs::read_to_string("/etc/hostname")
        .ok()
        .map(|s| s.trim().to_string())
        .or_else(|| std::env::var("HOSTNAME").ok())
        .or_else(|| std::env::var("COMPUTERNAME").ok())
        .unwrap_or_default();
    (user, host)
}

pub fn build() -> Result<Value> {
    let sys = sysinfo::collect();
    let sec = security::collect();
    let doc = doctor::run(false);
    let mut v = json!({
        "product": crate::PRODUCT,
        "version": env!("CARGO_PKG_VERSION"),
        "redacted": true,
        "system": serde_json::to_value(&sys)?,
        "security": serde_json::to_value(&sec)?,
        "doctor": serde_json::to_value(&doc)?,
    });
    let (user, host) = identity();
    redact_value(&mut v, &user, &host);
    Ok(v)
}

/// Write `report` as pretty JSON; never overwrites an existing file.
pub fn write_new(path: &Path, report: &Value) -> Result<()> {
    let mut f = std::fs::OpenOptions::new()
        .write(true)
        .create_new(true)
        .open(path)
        .with_context(|| {
            format!(
                "cannot create {} (refusing to overwrite existing files)",
                path.display()
            )
        })?;
    f.write_all(serde_json::to_string_pretty(report)?.as_bytes())?;
    f.write_all(b"\n")?;
    if f.metadata().is_err() {
        bail!("cannot stat {}", path.display());
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn redacts_nested_strings_but_not_numbers() {
        let mut v = json!({"a": ["alice on 10.0.0.7"], "b": {"mac": "aa:bb:cc:dd:ee:ff", "n": 10}});
        redact_value(&mut v, "alice", "box");
        let s = v.to_string();
        assert!(!s.contains("alice") && !s.contains("10.0.0.7") && !s.contains("aa:bb"));
        assert_eq!(v["b"]["n"], 10);
    }

    #[test]
    fn write_new_refuses_to_overwrite() {
        let d = tempfile::tempdir().unwrap();
        let p = d.path().join("r.json");
        write_new(&p, &json!({"x": 1})).unwrap();
        assert!(write_new(&p, &json!({"x": 2})).is_err());
        let back: Value = serde_json::from_str(&std::fs::read_to_string(&p).unwrap()).unwrap();
        assert_eq!(back["x"], 1);
    }

    #[test]
    fn report_has_expected_sections_and_flag() {
        let v = build().unwrap();
        for k in [
            "product", "version", "redacted", "system", "security", "doctor",
        ] {
            assert!(v.get(k).is_some(), "missing {k}");
        }
        assert_eq!(v["redacted"], true);
    }
}
