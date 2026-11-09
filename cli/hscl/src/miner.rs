//! `hscl miner` — guarded contact with Bitaxe/ESP-Miner devices on the local network.
//!
//! Design rules (root AGENTS.md 0.3.7, 6.6 and the miner ADR):
//! - Nothing here touches the internet. Only private/loopback hosts are accepted.
//! - No hidden shell execution: `flash` builds a fixed argv for `esptool`/`python -m esptool`.
//! - Every mutating action needs an explicit authorization phrase and refuses a dry run otherwise.
//! - OTA is honest about what the firmware does: no auth beyond the LAN rule, no TLS, no signature
//!   check, no downgrade protection (see docs/miner/FIRMWARE_RESEARCH.md).
//! - The firmware image is hashed before it is sent, and the hash is printed for the operator.

use std::io::{Read, Write};
use std::net::{TcpStream, ToSocketAddrs};
use std::path::{Path, PathBuf};
use std::time::Duration;

use anyhow::{bail, Context, Result};
use serde::{Deserialize, Serialize};

pub const AUTH_PHRASE: &str = "I am authorized to flash this device";
const MAX_BODY: usize = 256 * 1024;
const TIMEOUT: Duration = Duration::from_secs(6);
/// An OTA upload over Wi-Fi needs room for a multi-megabyte image plus the device's flash write.
const OTA_TIMEOUT: Duration = Duration::from_secs(240);

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct MinerConfig {
    pub receiver_port: u16,
    pub last_device: Option<String>,
    pub esptool: Option<String>,
}

impl Default for MinerConfig {
    fn default() -> Self {
        Self {
            receiver_port: 8765,
            last_device: None,
            esptool: None,
        }
    }
}

pub fn config_dir() -> PathBuf {
    crate::appearance::config_dir()
}

pub fn load_config(dir: &Path) -> MinerConfig {
    let path = dir.join("miner.json");
    std::fs::read_to_string(path)
        .ok()
        .and_then(|t| serde_json::from_str(&t).ok())
        .unwrap_or_default()
}

pub fn save_config(dir: &Path, cfg: &MinerConfig) -> Result<()> {
    std::fs::create_dir_all(dir)?;
    std::fs::write(dir.join("miner.json"), serde_json::to_vec_pretty(cfg)?)?;
    Ok(())
}

/// True for loopback, RFC1918, link-local, unique-local and `*.local` names.
/// A public address or a routable name is refused: this tool is not a remote miner controller.
pub fn is_private_host(host: &str) -> bool {
    let h = host.trim().trim_matches(['[', ']']).to_ascii_lowercase();
    if h.is_empty() {
        return false;
    }
    if h == "localhost" || h.ends_with(".local") {
        return true;
    }
    if let Ok(ip) = h.parse::<std::net::IpAddr>() {
        return match ip {
            std::net::IpAddr::V4(v4) => v4.is_loopback() || v4.is_private() || v4.is_link_local(),
            std::net::IpAddr::V6(v6) => {
                v6.is_loopback()
                    || (v6.segments()[0] & 0xffc0) == 0xfe80 // link-local fe80::/10
                    || (v6.segments()[0] & 0xfe00) == 0xfc00 // unique local fc00::/7
            }
        };
    }
    false
}

/// Minimal HTTP/1.1 request over TCP (AxeOS is plain HTTP on port 80). No TLS by design: the
/// firmware has none either, and pretending otherwise would be dishonest.
pub fn http_request(
    host: &str,
    port: u16,
    method: &str,
    path: &str,
    content_type: Option<&str>,
    body: Option<&[u8]>,
) -> Result<(u16, Vec<u8>)> {
    http_request_timeout(host, port, method, path, content_type, body, TIMEOUT)
}

/// Same as [`http_request`] with an explicit I/O timeout. An OTA uploads a multi-megabyte image to an
/// ESP32 over Wi-Fi; the short probe timeout would abort it mid-flight long before the device answers.
pub fn http_request_timeout(
    host: &str,
    port: u16,
    method: &str,
    path: &str,
    content_type: Option<&str>,
    body: Option<&[u8]>,
    io_timeout: Duration,
) -> Result<(u16, Vec<u8>)> {
    if !is_private_host(host) {
        bail!("refusing {host}: only private/loopback hosts are allowed");
    }
    let addr = format!("{host}:{port}");
    let mut stream = TcpStream::connect_timeout(
        &addr
            .to_socket_addrs()
            .with_context(|| format!("cannot resolve {addr}"))?
            .next()
            .context("no address")?,
        TIMEOUT,
    )
    .with_context(|| format!("cannot connect to {addr}"))?;
    stream.set_read_timeout(Some(io_timeout))?;
    stream.set_write_timeout(Some(io_timeout))?;

    let mut head = format!(
        "{method} {path} HTTP/1.1\r\nHost: {host}\r\nConnection: close\r\nAccept: application/json\r\n"
    );
    if let Some(ct) = content_type {
        head.push_str(&format!("Content-Type: {ct}\r\n"));
    }
    if let Some(b) = body {
        head.push_str(&format!("Content-Length: {}\r\n", b.len()));
    }
    head.push_str("\r\n");
    stream.write_all(head.as_bytes())?;
    if let Some(b) = body {
        stream.write_all(b)?;
    }
    stream.flush()?;

    let mut raw = Vec::new();
    let mut buf = [0u8; 8192];
    loop {
        match stream.read(&mut buf) {
            Ok(0) => break,
            Ok(n) => {
                raw.extend_from_slice(&buf[..n]);
                if raw.len() > MAX_BODY {
                    bail!("response larger than {} bytes", MAX_BODY);
                }
            }
            Err(e) if e.kind() == std::io::ErrorKind::WouldBlock => break,
            Err(e) if e.kind() == std::io::ErrorKind::TimedOut => break,
            Err(e) => return Err(e).context("read failed"),
        }
    }
    parse_http_response(&raw)
}

pub fn parse_http_response(raw: &[u8]) -> Result<(u16, Vec<u8>)> {
    let split = raw
        .windows(4)
        .position(|w| w == b"\r\n\r\n")
        .context("malformed HTTP response (no header terminator)")?;
    let head = String::from_utf8_lossy(&raw[..split]).to_string();
    let status = head
        .lines()
        .next()
        .and_then(|l| l.split_whitespace().nth(1))
        .and_then(|s| s.parse::<u16>().ok())
        .context("malformed HTTP status line")?;
    let mut body = raw[split + 4..].to_vec();
    // Transfer-Encoding: chunked (AxeOS uses it for some endpoints)
    if head
        .to_ascii_lowercase()
        .contains("transfer-encoding: chunked")
    {
        body = dechunk(&body)?;
    }
    Ok((status, body))
}

fn dechunk(mut body: &[u8]) -> Result<Vec<u8>> {
    let mut out = Vec::new();
    loop {
        let pos = body
            .windows(2)
            .position(|w| w == b"\r\n")
            .context("chunked body without size line")?;
        let size_line = String::from_utf8_lossy(&body[..pos]).to_string();
        let size = usize::from_str_radix(size_line.trim().split(';').next().unwrap_or("0"), 16)
            .context("bad chunk size")?;
        body = &body[pos + 2..];
        if size == 0 {
            break;
        }
        if body.len() < size + 2 {
            bail!("truncated chunk");
        }
        out.extend_from_slice(&body[..size]);
        body = &body[size + 2..];
    }
    Ok(out)
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DeviceInfo {
    pub host: String,
    pub status: u16,
    pub asic: Option<String>,
    pub board_version: Option<String>,
    pub firmware: Option<String>,
    pub hostname: Option<String>,
    pub mac: Option<String>,
    pub frequency: Option<i64>,
    pub voltage_mv: Option<i64>,
    pub temp_c: Option<f64>,
    pub raw_keys: Vec<String>,
}

pub fn probe(host: &str) -> Result<DeviceInfo> {
    if !is_private_host(host) {
        bail!("refusing {host}: only private/loopback hosts are allowed");
    }
    let (status, body) = http_request(host, 80, "GET", "/api/system/info", None, None)?;
    let json: serde_json::Value = serde_json::from_slice(&body).unwrap_or(serde_json::Value::Null);
    let get = |k: &str| json.get(k).cloned();
    Ok(DeviceInfo {
        host: host.to_string(),
        status,
        asic: get("ASICModel").and_then(|v| v.as_str().map(str::to_owned)),
        board_version: get("boardVersion").and_then(|v| v.as_str().map(str::to_owned)),
        firmware: get("version").and_then(|v| v.as_str().map(str::to_owned)),
        hostname: get("hostname").and_then(|v| v.as_str().map(str::to_owned)),
        mac: get("macAddr").and_then(|v| v.as_str().map(str::to_owned)),
        frequency: json.get("frequency").and_then(|v| v.as_i64()),
        voltage_mv: json.get("coreVoltage").and_then(|v| v.as_i64()),
        temp_c: json.get("temp").and_then(|v| v.as_f64()),
        raw_keys: json
            .as_object()
            .map(|o| o.keys().cloned().collect())
            .unwrap_or_default(),
    })
}

pub fn sha256_file(path: &Path) -> Result<String> {
    // `sha256sum`/`certutil` are not guaranteed on every host; a small pure implementation keeps this
    // dependency-free but would be 200 lines. The workspace already ships a hashing helper for
    // downloads, so reuse it when present.
    crate::download::sha256_file(path)
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct OtaPlan {
    pub device: String,
    pub firmware: String,
    pub firmware_bytes: u64,
    pub firmware_sha256: String,
    pub url: String,
    pub dry_run: bool,
    pub rollback_hint: String,
    pub warnings: Vec<String>,
}

pub fn plan_ota(device: &str, firmware: &Path) -> Result<OtaPlan> {
    if !is_private_host(device) {
        bail!("refusing {device}: only private/loopback hosts are allowed");
    }
    let meta = std::fs::metadata(firmware)
        .with_context(|| format!("cannot read firmware {}", firmware.display()))?;
    if !meta.is_file() || meta.len() == 0 {
        bail!("firmware is not a non-empty file: {}", firmware.display());
    }
    if meta.len() > 8 * 1024 * 1024 {
        bail!("firmware is larger than 8 MiB; an ESP32-S3 app image is far smaller");
    }
    let sha = sha256_file(firmware)?;
    Ok(OtaPlan {
        device: device.to_string(),
        firmware: firmware.display().to_string(),
        firmware_bytes: meta.len(),
        firmware_sha256: sha,
        url: format!("http://{device}/api/system/OTA"),
        dry_run: true,
        rollback_hint: format!(
            "previous slot stays intact: POST http://{device}/api/system/boot {{\"partition\":\"<other>\"}} or USB flashing"
        ),
        warnings: vec![
            "OTA has no authentication beyond a network-range check, no TLS and no signature check".into(),
            "never expose the miner to an untrusted network".into(),
            "a wrong board variant replaces the factory MAC; check boardVersion and ASICModel first".into(),
        ],
    })
}

pub fn authorized(phrase: &str) -> bool {
    phrase.trim() == AUTH_PHRASE
}

/// Apply an OTA update. Requires the exact authorization phrase and a verified firmware file.
pub fn ota(plan: &OtaPlan, firmware: &Path, phrase: &str, dry_run: bool) -> Result<OtaPlan> {
    if !authorized(phrase) {
        bail!("refusing to flash: pass --yes=\"{AUTH_PHRASE}\" after you have verified the device");
    }
    if dry_run {
        return Ok(OtaPlan {
            dry_run: true,
            ..plan.clone()
        });
    }
    let body = std::fs::read(firmware)?;
    let sha = sha256_file(firmware)?;
    if sha != plan.firmware_sha256 {
        bail!("firmware changed since the plan was made (sha256 mismatch)");
    }
    let (status, resp) = http_request_timeout(
        &plan.device,
        80,
        "POST",
        "/api/system/OTA",
        Some("application/octet-stream"),
        Some(&body),
        OTA_TIMEOUT,
    )?;
    if !(200..300).contains(&status) {
        bail!(
            "device rejected the update: HTTP {status}: {}",
            String::from_utf8_lossy(&resp)
                .chars()
                .take(200)
                .collect::<String>()
        );
    }
    Ok(OtaPlan {
        dry_run: false,
        ..plan.clone()
    })
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct FlashPlan {
    pub port: String,
    pub firmware: String,
    pub firmware_sha256: String,
    pub offset: String,
    pub argv: Vec<String>,
    pub dry_run: bool,
    pub warnings: Vec<String>,
}

/// Find a usable esptool invocation without assuming a PATH entry exists.
///
/// `HSCL_ESPTOOL` wins (whitespace-separated, e.g. `C:\esp\python.exe -m esptool`), which is how the
/// ESP-IDF virtualenv is used without activating it. Otherwise the script/console entry point is
/// preferred, then `python -m esptool` (the name that actually exists on Windows), then `python3`.
pub fn esptool_command() -> Vec<String> {
    if let Ok(v) = std::env::var("HSCL_ESPTOOL") {
        let parts: Vec<String> = v.split_whitespace().map(str::to_string).collect();
        if !parts.is_empty() {
            return parts;
        }
    }
    if which("esptool.py").is_some() {
        return vec!["esptool.py".into()];
    }
    if which("esptool").is_some() {
        return vec!["esptool".into()];
    }
    for py in ["python", "python3"] {
        if which(py).is_some() {
            return vec![py.into(), "-m".into(), "esptool".into()];
        }
    }
    vec!["python".into(), "-m".into(), "esptool".into()]
}

fn which(name: &str) -> Option<PathBuf> {
    std::env::var_os("PATH").and_then(|paths| {
        std::env::split_paths(&paths)
            .map(|p| p.join(name))
            .find(|p| p.is_file())
    })
}

pub fn plan_flash(port: &str, firmware: &Path, offset: &str) -> Result<FlashPlan> {
    let meta = std::fs::metadata(firmware)
        .with_context(|| format!("cannot read firmware {}", firmware.display()))?;
    if !meta.is_file() || meta.len() == 0 {
        bail!("firmware is not a non-empty file: {}", firmware.display());
    }
    // Offset hygiene: 0x0 is a merged factory image (bootloader + partitions + app + otadata) and is
    // several MiB. Writing a bare app image at 0x0 destroys the bootloader, so a small file at 0x0 is
    // refused instead of trusted.
    let off = offset.trim().to_ascii_lowercase();
    let is_factory_offset = off == "0x0" || off == "0";
    if is_factory_offset && meta.len() < 1024 * 1024 {
        bail!(
            "refusing {} bytes at 0x0: that is an app image, not a merged factory image. \
             Use --offset 0x10000 for an app image, or build a factory image with esptool merge_bin",
            meta.len()
        );
    }
    let sha = sha256_file(firmware)?;
    let mut argv = esptool_command();
    argv.extend(
        [
            "--chip",
            "esp32s3",
            "--port",
            port,
            "--baud",
            "460800",
            "write_flash",
            "-z",
            &off,
        ]
        .iter()
        .map(|s| s.to_string()),
    );
    argv.push(firmware.display().to_string());
    Ok(FlashPlan {
        port: port.to_string(),
        firmware: firmware.display().to_string(),
        firmware_sha256: sha,
        offset: off,
        argv,
        dry_run: true,
        warnings: vec![
            "USB flashing writes the miner's flash: only do this on a device you own".into(),
            "a merged factory image at 0x0 replaces bootloader, partitions and app".into(),
            "an app-only image belongs at 0x10000".into(),
            "hold BOOT and tap RESET if the port does not appear".into(),
        ],
    })
}

pub fn flash(plan: &FlashPlan, phrase: &str, dry_run: bool) -> Result<FlashPlan> {
    if !authorized(phrase) {
        bail!("refusing to flash: pass --yes=\"{AUTH_PHRASE}\" after you have verified the device");
    }
    if dry_run {
        return Ok(FlashPlan {
            dry_run: true,
            ..plan.clone()
        });
    }
    let (prog, args) = plan.argv.split_first().context("empty argv")?;
    let status = std::process::Command::new(prog)
        .args(args)
        .status()
        .with_context(|| format!("cannot run {prog} (install esptool)"))?;
    if !status.success() {
        bail!("{prog} failed with {status}");
    }
    Ok(FlashPlan {
        dry_run: false,
        ..plan.clone()
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn only_private_hosts_are_accepted() {
        for ok in [
            "192.168.178.61",
            "10.1.2.3",
            "172.16.0.9",
            "127.0.0.1",
            "localhost",
            "bitaxe.local",
            "::1",
            "fe80::1",
            "fd00::5",
        ] {
            assert!(is_private_host(ok), "{ok} should be allowed");
        }
        for bad in ["8.8.8.8", "example.com", "172.32.0.1", "0.0.0.0", ""] {
            assert!(!is_private_host(bad), "{bad} must be refused");
        }
    }

    #[test]
    fn a_public_device_is_refused_before_any_socket() {
        let err = probe("1.1.1.1").unwrap_err().to_string();
        assert!(err.contains("private"), "{err}");
    }

    #[test]
    fn flash_requires_the_exact_authorization_phrase() {
        let dir = tempfile::tempdir().unwrap();
        let fw = dir.path().join("esp-miner.bin");
        std::fs::write(&fw, b"firmware").unwrap();
        let plan = plan_flash("COM5", &fw, "0x10000").unwrap();
        for bad in [
            "",
            "yes",
            "I am authorized",
            "i am authorized to flash this device",
        ] {
            assert!(flash(&plan, bad, false).is_err(), "{bad:?} must be refused");
        }
        let dry = flash(&plan, AUTH_PHRASE, true).unwrap();
        assert!(dry.dry_run);
        assert_eq!(dry.argv[0], esptool_command()[0]);
        assert_eq!(dry.offset, "0x10000");
    }

    #[test]
    fn an_app_image_at_offset_zero_is_refused() {
        // Writing a bare app image at 0x0 destroys the bootloader. The guard must catch it.
        let dir = tempfile::tempdir().unwrap();
        let fw = dir.path().join("esp-miner.bin");
        std::fs::write(&fw, vec![0u8; 4096]).unwrap();
        let err = plan_flash("COM5", &fw, "0x0").unwrap_err().to_string();
        assert!(err.contains("factory image"), "{err}");
        assert!(plan_flash("COM5", &fw, "0x10000").is_ok());
    }

    #[test]
    fn a_merged_factory_image_is_allowed_at_zero() {
        let dir = tempfile::tempdir().unwrap();
        let fw = dir.path().join("factory.bin");
        std::fs::write(&fw, vec![0u8; 2 * 1024 * 1024]).unwrap();
        let plan = plan_flash("COM5", &fw, "0x0").unwrap();
        assert_eq!(plan.offset, "0x0");
        assert!(plan.argv.join(" ").contains("write_flash -z 0x0"));
    }

    #[test]
    fn ota_dry_run_keeps_the_plan_and_does_not_connect() {
        let dir = tempfile::tempdir().unwrap();
        let fw = dir.path().join("esp-miner.bin");
        std::fs::write(&fw, vec![0u8; 1024]).unwrap();
        let plan = plan_ota("192.168.178.61", &fw).unwrap();
        assert_eq!(plan.firmware_bytes, 1024);
        assert_eq!(plan.firmware_sha256.len(), 64);
        assert!(plan.url.contains("/api/system/OTA"));
        let dry = ota(&plan, &fw, AUTH_PHRASE, true).unwrap();
        assert!(dry.dry_run);
        assert!(ota(&plan, &fw, "nope", true).is_err());
    }

    #[test]
    fn an_oversized_firmware_is_refused() {
        let dir = tempfile::tempdir().unwrap();
        let fw = dir.path().join("big.bin");
        std::fs::write(&fw, vec![0u8; 9 * 1024 * 1024]).unwrap();
        assert!(plan_ota("192.168.178.61", &fw).is_err());
    }

    #[test]
    fn http_response_parsing_handles_plain_and_chunked_bodies() {
        let plain = b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n\r\n{\"a\":1}";
        assert_eq!(parse_http_response(plain).unwrap().0, 200);
        let chunked =
            b"HTTP/1.1 200 OK\r\nTransfer-Encoding: chunked\r\n\r\n4\r\n{\"a\"\r\n3\r\n:1}\r\n0\r\n\r\n";
        let (status, body) = parse_http_response(chunked).unwrap();
        assert_eq!(status, 200);
        assert_eq!(body, b"{\"a\":1}");
    }

    #[test]
    fn probe_parses_a_real_axeos_shape() {
        let listener = std::net::TcpListener::bind("127.0.0.1:0").unwrap();
        let port = listener.local_addr().unwrap().port();
        std::thread::spawn(move || {
            let (mut s, _) = listener.accept().unwrap();
            let mut buf = [0u8; 1024];
            let _ = s.read(&mut buf);
            let body = r#"{"ASICModel":"BM1366","boardVersion":"401","version":"v4.0.2-rc1","hostname":"bitaxe","macAddr":"AA:BB","frequency":485}"#;
            let _ = s.write_all(
                format!(
                    "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: {}\r\n\r\n{body}",
                    body.len()
                )
                .as_bytes(),
            );
        });
        let (status, body) =
            http_request("127.0.0.1", port, "GET", "/api/system/info", None, None).unwrap();
        assert_eq!(status, 200);
        let json: serde_json::Value = serde_json::from_slice(&body).unwrap();
        assert_eq!(json["ASICModel"], "BM1366");
    }

    #[test]
    fn config_round_trips_in_a_temp_dir() {
        let dir = tempfile::tempdir().unwrap();
        let cfg = MinerConfig {
            receiver_port: 9000,
            last_device: Some("192.168.178.61".into()),
            esptool: None,
        };
        save_config(dir.path(), &cfg).unwrap();
        assert_eq!(load_config(dir.path()), cfg);
        assert_eq!(
            load_config(&dir.path().join("absent")),
            MinerConfig::default()
        );
    }
}
