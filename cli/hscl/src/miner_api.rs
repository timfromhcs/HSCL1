use std::io::{Read, Write};
use std::net::{TcpListener, TcpStream, ToSocketAddrs};
use std::sync::{Arc, Mutex};
use std::time::{Duration, Instant};

use anyhow::{bail, Context, Result};
use serde::{Deserialize, Serialize};

use crate::miner::{probe, DeviceInfo};

/// Shared, periodically refreshed snapshot per device.
type Cache = Arc<Mutex<Vec<(String, Option<DeviceInfo>, Instant)>>>;

/// A device seen on the LAN, identified by MAC rather than by address.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FoundMiner {
    pub host: String,
    pub hostname: Option<String>,
    pub mac: Option<String>,
    pub board: Option<String>,
    pub asic: Option<String>,
    pub version: Option<String>,
}

/// Scan a private /24 for AxeOS devices. One TCP connect per address, 250 ms timeout, 32 workers.
/// Read-only: only `GET /api/system/info` is sent, nothing is configured.
pub fn discover(prefix: &str) -> Result<Vec<FoundMiner>> {
    let base = prefix.trim_end_matches('.').to_string();
    let octets: Vec<&str> = base.split('.').collect();
    if octets.len() != 3
        || octets
            .iter()
            .any(|o| o.parse::<u16>().map(|v| v > 255).unwrap_or(true))
    {
        bail!("prefix must look like 192.168.178 (three octets)");
    }
    let first: u16 = octets[0].parse()?;
    let is_private =
        matches!(first, 10 | 127) || (first == 172) || (first == 192 && octets[1] == "168");
    if !is_private {
        bail!("refusing to scan {base}: only private prefixes are allowed");
    }
    let mut found = Vec::new();
    let queue = Arc::new(Mutex::new((1u16..=254).collect::<Vec<u16>>()));
    let results = Arc::new(Mutex::new(Vec::new()));
    let mut handles = Vec::new();
    for _ in 0..32 {
        let queue = Arc::clone(&queue);
        let results = Arc::clone(&results);
        let base = base.clone();
        handles.push(std::thread::spawn(move || loop {
            let n = {
                let mut q = queue.lock().unwrap();
                match q.pop() {
                    Some(n) => n,
                    None => break,
                }
            };
            let host = format!("{base}.{n}");
            if TcpStream::connect_timeout(
                &match format!("{host}:80")
                    .to_socket_addrs()
                    .ok()
                    .and_then(|mut a| a.next())
                {
                    Some(addr) => addr,
                    None => continue,
                },
                Duration::from_millis(250),
            )
            .is_ok()
            {
                if let Ok(info) = probe(&host) {
                    if info.asic.is_some() {
                        results.lock().unwrap().push(FoundMiner {
                            host: info.host.clone(),
                            hostname: info.hostname.clone(),
                            mac: info.mac.clone(),
                            board: info.board_version.clone(),
                            asic: info.asic.clone(),
                            version: info.firmware.clone(),
                        });
                    }
                }
            }
        }));
    }
    for h in handles {
        let _ = h.join();
    }
    let mut out = std::mem::take(&mut *results.lock().unwrap());
    out.sort_by(|a, b| a.host.cmp(&b.host));
    found.append(&mut out);
    Ok(found)
}

/// Minimal read-only HTTP API so other tools (and the Control Center) can consume miner data.
/// Endpoints: `/v1/health`, `/v1/miners`, `/v1/miner?host=192.168.178.61`.
pub fn serve(bind: &str, hosts: Vec<String>) -> Result<()> {
    let listener = TcpListener::bind(bind).with_context(|| format!("cannot bind {bind}"))?;
    let cache: Cache = Arc::new(Mutex::new(
        hosts
            .iter()
            .map(|h| (h.clone(), None, Instant::now() - Duration::from_secs(3600)))
            .collect(),
    ));
    // Polling happens in the background: a read request must never wait for a slow device (three
    // miners at 6 s timeout each would hold the socket ~18 s and the client would time out).
    {
        let cache = Arc::clone(&cache);
        std::thread::spawn(move || loop {
            let _ = refresh(&cache);
            std::thread::sleep(Duration::from_secs(5));
        });
    }
    eprintln!("hscl miner serve on http://{bind} (read-only)");
    for stream in listener.incoming() {
        let mut stream = match stream {
            Ok(s) => s,
            Err(_) => continue,
        };
        let cache = Arc::clone(&cache);
        std::thread::spawn(move || {
            let mut buf = [0u8; 1024];
            let n = stream.read(&mut buf).unwrap_or(0);
            let request = String::from_utf8_lossy(&buf[..n]).to_string();
            let path = request.split_whitespace().nth(1).unwrap_or("/").to_string();
            let (status, body) = match path.as_str() {
                "/v1/health" => (
                    200,
                    serde_json::json!({"status": "ok", "devices": hosts_len(&cache)}).to_string(),
                ),
                "/v1/miners" => {
                    let list: Vec<_> = cache
                        .lock()
                        .unwrap()
                        .iter()
                        .map(|(h, d, _)| serde_json::json!({"host": h, "info": d}))
                        .collect();
                    (200, serde_json::json!({"miners": list}).to_string())
                }
                p if p.starts_with("/v1/miner") => {
                    let host = p.split("host=").nth(1).and_then(|v| v.split('&').next());
                    let guard = cache.lock().unwrap();
                    let found = host.and_then(|h| guard.iter().find(|(c, _, _)| c == h));
                    match found {
                        Some((_, Some(d), _)) => {
                            (200, serde_json::to_string(d).unwrap_or_default())
                        }
                        _ => (404, "{\"error\":\"unknown device\"}".to_string()),
                    }
                }
                _ => (404, "{\"error\":\"not found\"}".to_string()),
            };
            let _ = stream.write_all(
                format!(
                    "HTTP/1.1 {status} OK\r\nContent-Type: application/json\r\nContent-Length: {}\r\nConnection: close\r\n\r\n{body}",
                    body.len()
                )
                .as_bytes(),
            );
        });
    }
    Ok(())
}

fn hosts_len(cache: &Cache) -> usize {
    cache.lock().unwrap().len()
}

fn refresh(cache: &Cache) -> Result<()> {
    let hosts: Vec<String> = cache
        .lock()
        .unwrap()
        .iter()
        .map(|(h, _, _)| h.clone())
        .collect();
    let mut updated = Vec::new();
    for host in hosts {
        let info = probe(&host).ok();
        updated.push((host, info, Instant::now()));
    }
    *cache.lock().unwrap() = updated;
    Ok(())
}
