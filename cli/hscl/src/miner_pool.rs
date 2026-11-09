//! Pool-slot writes for AxeOS (`PUT /api/system/pools/<0..7>`), kept in their own module so the
//! read-only miner code stays free of configuration writes.

use anyhow::{bail, Result};
use serde::{Deserialize, Serialize};
use std::time::Duration;

use crate::miner::{authorized, is_private_host, DeviceInfo, AUTH_PHRASE};

const POOL_TIMEOUT: Duration = Duration::from_secs(20);

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct PoolSpec {
    pub index: u8,
    pub protocol: String,
    pub url: String,
    pub port: u16,
    pub user: String,
    pub password: String,
    pub suggested_difficulty: u32,
    pub tls: u8,
}

impl PoolSpec {
    /// Payload exactly as `openapi.yaml#/components/schemas/Pool` defines it.
    pub fn payload(&self) -> serde_json::Value {
        serde_json::json!({
            "stratumProtocol": self.protocol,
            "stratumURL": self.url,
            "stratumPort": self.port,
            "stratumUser": self.user,
            "stratumPassword": self.password,
            "stratumSuggestedDifficulty": self.suggested_difficulty,
            "stratumTLS": self.tls,
            "stratumExtranonceSubscribe": false,
            "stratumDecodeCoinbase": true,
            "stratumV2ChannelType": "extended",
        })
    }

    pub fn masked(&self) -> serde_json::Value {
        let mut v = self.payload();
        if let Some(o) = v.as_object_mut() {
            o.insert("stratumUser".into(), serde_json::json!(mask(&self.user)));
            o.insert("stratumPassword".into(), serde_json::json!("<set>"));
        }
        serde_json::json!({"index": self.index, "pool": v})
    }
}

fn mask(value: &str) -> String {
    if value.len() <= 8 {
        "*".repeat(value.len())
    } else {
        format!(
            "{}…{} ({} chars)",
            &value[..4],
            &value[value.len() - 4..],
            value.len()
        )
    }
}

pub fn validate(index: u8, url: &str, port: u16, protocol: &str) -> Result<()> {
    if index > 7 {
        bail!("pool index must be 0..=7 (AxeOS has 8 slots)");
    }
    if port == 0 {
        bail!("port must be 1..=65535");
    }
    if protocol != "SV1" && protocol != "SV2" {
        bail!("protocol must be SV1 or SV2");
    }
    let u = url.trim();
    if u.is_empty() || u.len() > 128 {
        bail!("pool url must be 1..128 characters");
    }
    if u.chars()
        .any(|c| c.is_whitespace() || c == '/' || c == '\0')
    {
        bail!("pool url must be a bare host name (no scheme, no path, no spaces)");
    }
    Ok(())
}

pub fn spec(
    index: u8,
    url: &str,
    port: u16,
    user: &str,
    password: &str,
    protocol: &str,
    difficulty: u32,
    tls: u8,
) -> Result<PoolSpec> {
    validate(index, url, port, protocol)?;
    if user.trim().is_empty() {
        bail!("pool user must not be empty (that is the payout address or worker name)");
    }
    if tls > 2 {
        bail!("tls must be 0, 1 or 2");
    }
    Ok(PoolSpec {
        index,
        protocol: protocol.to_string(),
        url: url.trim().to_string(),
        port,
        user: user.trim().to_string(),
        password: if password.is_empty() {
            "x".into()
        } else {
            password.to_string()
        },
        suggested_difficulty: difficulty,
        tls,
    })
}

/// PUT the slot. Requires the same authorization phrase as flashing; a dry run sends nothing.
pub fn write(
    device: &str,
    spec: &PoolSpec,
    phrase: &str,
    dry_run: bool,
) -> Result<serde_json::Value> {
    if !is_private_host(device) {
        bail!("refusing {device}: only private/loopback hosts are allowed");
    }
    if !authorized(phrase) {
        bail!("refusing to change the pool: pass --yes=\"{AUTH_PHRASE}\" after you verified the device");
    }
    if dry_run {
        return Ok(
            serde_json::json!({"dry_run": true, "endpoint": format!("PUT http://{device}/api/system/pools/{}", spec.index), "body": spec.masked()}),
        );
    }
    let body = serde_json::to_vec(&spec.payload())?;
    let (status, resp) = crate::miner::http_request_timeout(
        device,
        80,
        "PUT",
        &format!("/api/system/pools/{}", spec.index),
        Some("application/json"),
        Some(&body),
        POOL_TIMEOUT,
    )?;
    if !(200..300).contains(&status) {
        bail!(
            "device rejected the pool: HTTP {status}: {}",
            String::from_utf8_lossy(&resp)
                .chars()
                .take(200)
                .collect::<String>()
        );
    }
    Ok(serde_json::json!({"dry_run": false, "status": status, "body": spec.masked()}))
}

/// Read the pools back from a device (read-only).
pub fn list(device: &str) -> Result<Vec<serde_json::Value>> {
    let info: DeviceInfo = crate::miner::probe(device)?;
    let _ = info;
    let (status, body) = crate::miner::http_request_timeout(
        device,
        80,
        "GET",
        "/api/system/info",
        None,
        None,
        POOL_TIMEOUT,
    )?;
    if !(200..300).contains(&status) {
        bail!("device answered HTTP {status}");
    }
    let json: serde_json::Value = serde_json::from_slice(&body)?;
    let pools = json
        .get("pools")
        .and_then(|p| p.as_array())
        .cloned()
        .unwrap_or_default();
    Ok(pools
        .into_iter()
        .map(|mut p| {
            if let Some(o) = p.as_object_mut() {
                if let Some(u) = o.get("stratumUser").and_then(|v| v.as_str()) {
                    o.insert("stratumUser".into(), serde_json::json!(mask(u)));
                }
                o.insert("stratumPassword".into(), serde_json::json!("<hidden>"));
            }
            p
        })
        .collect())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn validation_rejects_bad_slots_and_urls() {
        assert!(validate(0, "solo.ckpool.org", 3333, "SV1").is_ok());
        assert!(validate(8, "solo.ckpool.org", 3333, "SV1").is_err());
        assert!(validate(0, "stratum+tcp://pool:3333", 3333, "SV1").is_err());
        assert!(validate(0, "pool/path", 3333, "SV1").is_err());
        assert!(validate(0, "pool", 0, "SV1").is_err());
        assert!(validate(0, "pool", 3333, "SV3").is_err());
        assert!(validate(0, "", 3333, "SV1").is_err());
    }

    #[test]
    fn an_empty_user_is_refused_but_the_password_defaults() {
        assert!(spec(0, "pool", 3333, "  ", "x", "SV1", 1000, 0).is_err());
        let s = spec(0, "pool", 3333, "addr.worker", "", "SV1", 1000, 0).unwrap();
        assert_eq!(s.password, "x");
    }

    #[test]
    fn dry_run_never_opens_a_socket_and_masks_the_wallet() {
        let s = spec(
            0,
            "solo.ckpool.org",
            3333,
            "bc1qexampleaddress000000000",
            "x",
            "SV1",
            1000,
            0,
        )
        .unwrap();
        let out = write("192.168.178.61", &s, AUTH_PHRASE, true).unwrap();
        assert_eq!(out["dry_run"], true);
        let user = out["body"]["pool"]["stratumUser"].as_str().unwrap();
        assert!(!user.contains("bc1qexampleaddress000000000"), "{user}");
        assert_eq!(out["body"]["pool"]["stratumPassword"], "<set>");
    }

    #[test]
    fn the_phrase_and_the_private_host_are_required() {
        let s = spec(0, "pool", 3333, "addr", "x", "SV1", 1000, 0).unwrap();
        assert!(write("1.1.1.1", &s, AUTH_PHRASE, true).is_err());
        assert!(write("192.168.178.61", &s, "yes", true).is_err());
    }
}
