//! Redaction of identifying values (AGENTS.md 8.3). Applied to everything `doctor`/`system info` prints.

/// Redact MAC addresses, IPv4 private ranges, and the given user/host names.
pub fn redact(input: &str, user: &str, host: &str) -> String {
    let mut out = input.to_string();
    for needle in [user, host] {
        if needle.len() >= 2 {
            out = out.replace(needle, "[redacted]");
        }
    }
    out.split_inclusive(char::is_whitespace)
        .map(|tok| {
            let t = tok.trim_end();
            let ws = &tok[t.len()..];
            if is_mac(t) || is_private_ipv4(t) {
                format!("[redacted]{ws}")
            } else {
                tok.to_string()
            }
        })
        .collect()
}

fn is_mac(s: &str) -> bool {
    let p: Vec<&str> = s.split(':').collect();
    p.len() == 6
        && p.iter()
            .all(|x| x.len() == 2 && x.chars().all(|c| c.is_ascii_hexdigit()))
}

fn is_private_ipv4(s: &str) -> bool {
    let p: Vec<u8> = match s
        .split('.')
        .map(|x| x.parse::<u8>())
        .collect::<Result<_, _>>()
    {
        Ok(v) => v,
        Err(_) => return false,
    };
    p.len() == 4
        && (p[0] == 10
            || (p[0] == 192 && p[1] == 168)
            || (p[0] == 172 && (16..=31).contains(&p[1])))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn redacts_mac_ip_user_host() {
        let s = redact(
            "alice@box 10.0.0.5 aa:bb:cc:dd:ee:ff 8.8.8.8",
            "alice",
            "box",
        );
        assert!(!s.contains("alice") && !s.contains("box"));
        assert!(!s.contains("10.0.0.5") && !s.contains("aa:bb"));
        assert!(s.contains("8.8.8.8"));
    }

    #[test]
    fn short_names_not_mangled() {
        assert_eq!(redact("abc", "", "x"), "abc");
    }
}
