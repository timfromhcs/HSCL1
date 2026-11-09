//! Minimal WebSocket client for the AxeOS push endpoint (`/api/ws/live`).
//!
//! No external crates: the handshake, SHA-1 accept check and frame parser are implemented here, because
//! the workspace avoids new dependencies for a read-only data path. The client only reads text frames
//! and answers pings; it never sends application data.

use std::io::{Read, Write};
use std::net::{TcpStream, ToSocketAddrs};
use std::time::Duration;

use anyhow::{bail, Context, Result};

const WS_GUID: &str = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11";

/// Standard base64 with '=' padding.
pub fn base64(data: &[u8]) -> String {
    const T: &[u8; 64] = b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
    let mut out = String::new();
    for chunk in data.chunks(3) {
        let b = [
            chunk[0],
            *chunk.get(1).unwrap_or(&0),
            *chunk.get(2).unwrap_or(&0),
        ];
        let n = ((b[0] as u32) << 16) | ((b[1] as u32) << 8) | b[2] as u32;
        out.push(T[(n >> 18) as usize & 63] as char);
        out.push(T[(n >> 12) as usize & 63] as char);
        out.push(if chunk.len() > 1 {
            T[(n >> 6) as usize & 63] as char
        } else {
            '='
        });
        out.push(if chunk.len() > 2 {
            T[n as usize & 63] as char
        } else {
            '='
        });
    }
    out
}

/// SHA-1 (RFC 3174), used only to verify the handshake accept value.
pub fn sha1(data: &[u8]) -> [u8; 20] {
    let mut h: [u32; 5] = [0x67452301, 0xEFCDAB89, 0x98BADCFE, 0x10325476, 0xC3D2E1F0];
    let mut msg = data.to_vec();
    let bit_len = (data.len() as u64) * 8;
    msg.push(0x80);
    while msg.len() % 64 != 56 {
        msg.push(0);
    }
    msg.extend_from_slice(&bit_len.to_be_bytes());
    for block in msg.chunks(64) {
        let mut w = [0u32; 80];
        for i in 0..16 {
            w[i] = u32::from_be_bytes([
                block[i * 4],
                block[i * 4 + 1],
                block[i * 4 + 2],
                block[i * 4 + 3],
            ]);
        }
        for i in 16..80 {
            w[i] = (w[i - 3] ^ w[i - 8] ^ w[i - 14] ^ w[i - 16]).rotate_left(1);
        }
        let (mut a, mut b, mut c, mut d, mut e) = (h[0], h[1], h[2], h[3], h[4]);
        for (i, wi) in w.iter().enumerate() {
            let (f, k) = match i {
                0..=19 => ((b & c) | ((!b) & d), 0x5A827999),
                20..=39 => (b ^ c ^ d, 0x6ED9EBA1),
                40..=59 => ((b & c) | (b & d) | (c & d), 0x8F1BBCDC),
                _ => (b ^ c ^ d, 0xCA62C1D6),
            };
            let tmp = a
                .rotate_left(5)
                .wrapping_add(f)
                .wrapping_add(e)
                .wrapping_add(k)
                .wrapping_add(*wi);
            e = d;
            d = c;
            c = b.rotate_left(30);
            b = a;
            a = tmp;
        }
        h[0] = h[0].wrapping_add(a);
        h[1] = h[1].wrapping_add(b);
        h[2] = h[2].wrapping_add(c);
        h[3] = h[3].wrapping_add(d);
        h[4] = h[4].wrapping_add(e);
    }
    let mut out = [0u8; 20];
    for (i, v) in h.iter().enumerate() {
        out[i * 4..i * 4 + 4].copy_from_slice(&v.to_be_bytes());
    }
    out
}

fn accept_for(key: &str) -> String {
    base64(&sha1(format!("{key}{WS_GUID}").as_bytes()))
}

fn make_key() -> String {
    // Not security-relevant for a read-only client; still random enough to avoid a fixed key.
    let seed = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map(|d| d.as_nanos() as u64)
        .unwrap_or(0)
        ^ (std::process::id() as u64);
    let mut x = seed | 1;
    let mut bytes = [0u8; 16];
    for b in &mut bytes {
        x = x
            .wrapping_mul(6364136223846793005)
            .wrapping_add(1442695040888963407);
        *b = (x >> 33) as u8;
    }
    base64(&bytes)
}

#[derive(Debug)]
pub struct WsClient {
    stream: TcpStream,
}

impl WsClient {
    /// Perform the upgrade handshake. Refuses a non-101 answer and a mismatched accept key.
    pub fn connect(host: &str, port: u16, path: &str, timeout: Duration) -> Result<Self> {
        let addr = format!("{host}:{port}");
        let socket = addr
            .to_socket_addrs()
            .with_context(|| format!("cannot resolve {addr}"))?
            .next()
            .context("no address")?;
        let mut stream = TcpStream::connect_timeout(&socket, timeout)
            .with_context(|| format!("cannot connect to {addr}"))?;
        stream.set_read_timeout(Some(timeout))?;
        stream.set_write_timeout(Some(timeout))?;
        let key = make_key();
        let req = format!(
            "GET {path} HTTP/1.1\r\nHost: {host}\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n"
        );
        stream.write_all(req.as_bytes())?;
        let mut head = Vec::new();
        let mut buf = [0u8; 1];
        while !head.ends_with(b"\r\n\r\n") {
            if stream.read(&mut buf)? == 0 {
                bail!("connection closed during the handshake");
            }
            head.push(buf[0]);
            if head.len() > 8192 {
                bail!("handshake response too large");
            }
        }
        let text = String::from_utf8_lossy(&head).to_ascii_lowercase();
        if !text.starts_with("http/1.1 101") && !text.starts_with("http/1.0 101") {
            bail!(
                "server refused the upgrade: {}",
                text.lines().next().unwrap_or("")
            );
        }
        let expected = accept_for(&key).to_ascii_lowercase();
        if !text.contains(&format!("sec-websocket-accept: {expected}")) {
            bail!("handshake accept key mismatch");
        }
        Ok(Self { stream })
    }

    /// Read one application frame as text. Returns Ok(None) on a close frame.
    pub fn read_text(&mut self) -> Result<Option<String>> {
        loop {
            let mut h = [0u8; 2];
            if self.stream.read_exact(&mut h).is_err() {
                return Ok(None);
            }
            let opcode = h[0] & 0x0f;
            let masked = h[1] & 0x80 != 0;
            let len = match h[1] & 0x7f {
                126 => {
                    let mut b = [0u8; 2];
                    self.stream.read_exact(&mut b)?;
                    u16::from_be_bytes(b) as usize
                }
                127 => {
                    let mut b = [0u8; 8];
                    self.stream.read_exact(&mut b)?;
                    u64::from_be_bytes(b) as usize
                }
                n => n as usize,
            };
            if len > 512 * 1024 {
                bail!("frame too large ({len} bytes)");
            }
            let mut mask = [0u8; 4];
            if masked {
                self.stream.read_exact(&mut mask)?;
            }
            let mut payload = vec![0u8; len];
            self.stream.read_exact(&mut payload)?;
            if masked {
                for (i, b) in payload.iter_mut().enumerate() {
                    *b ^= mask[i % 4];
                }
            }
            match opcode {
                0x1 => return Ok(Some(String::from_utf8_lossy(&payload).into_owned())),
                0x8 => return Ok(None),
                0x9 => self.send_pong(&payload)?,
                _ => continue,
            }
        }
    }

    fn send_pong(&mut self, payload: &[u8]) -> Result<()> {
        let mut frame = vec![0x8a];
        let len = payload.len();
        if len < 126 {
            frame.push(0x80 | len as u8);
        } else {
            frame.push(0x80 | 126);
            frame.extend_from_slice(&(len as u16).to_be_bytes());
        }
        frame.extend_from_slice(&[0, 0, 0, 0]); // mask key
        frame.extend_from_slice(payload);
        self.stream.write_all(&frame)?;
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn sha1_matches_the_rfc_vectors() {
        let hex = |d: [u8; 20]| d.iter().map(|b| format!("{b:02x}")).collect::<String>();
        assert_eq!(
            hex(sha1(b"abc")),
            "a9993e364706816aba3e25717850c26c9cd0d89d"
        );
        assert_eq!(hex(sha1(b"")), "da39a3ee5e6b4b0d3255bfef95601890afd80709");
    }

    #[test]
    fn base64_matches_known_values() {
        assert_eq!(base64(b""), "");
        assert_eq!(base64(b"f"), "Zg==");
        assert_eq!(base64(b"fo"), "Zm8=");
        assert_eq!(base64(b"foo"), "Zm9v");
        assert_eq!(base64(b"hello"), "aGVsbG8=");
    }

    #[test]
    fn the_accept_value_is_the_rfc_example() {
        assert_eq!(
            accept_for("dGhlIHNhbXBsZSBub25jZQ=="),
            "s3pPLMBiTxaQ9kYGzzhZRbK+xOo="
        );
    }

    #[test]
    fn a_refused_upgrade_is_an_error_not_a_silent_garbage_read() {
        let listener = std::net::TcpListener::bind("127.0.0.1:0").unwrap();
        let port = listener.local_addr().unwrap().port();
        std::thread::spawn(move || {
            if let Ok((mut s, _)) = listener.accept() {
                let mut buf = [0u8; 1024];
                let _ = s.read(&mut buf);
                let _ = s.write_all(b"HTTP/1.1 404 Not Found\r\n\r\n");
                let _ = s.flush();
                std::thread::sleep(Duration::from_millis(100));
            }
        });
        let err = WsClient::connect("127.0.0.1", port, "/api/ws/live", Duration::from_secs(2))
            .unwrap_err()
            .to_string();
        assert!(err.contains("refused"), "{err}");
    }

    #[test]
    fn a_mismatched_accept_key_is_rejected() {
        let listener = std::net::TcpListener::bind("127.0.0.1:0").unwrap();
        let port = listener.local_addr().unwrap().port();
        std::thread::spawn(move || {
            if let Ok((mut s, _)) = listener.accept() {
                let mut buf = [0u8; 1024];
                let _ = s.read(&mut buf);
                let _ = s.write_all(
                    b"HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Accept: wrong\r\n\r\n",
                );
                let _ = s.flush();
                std::thread::sleep(Duration::from_millis(100));
            }
        });
        let err = WsClient::connect("127.0.0.1", port, "/api/ws/live", Duration::from_secs(2))
            .unwrap_err()
            .to_string();
        assert!(err.contains("accept"), "{err}");
    }
}
