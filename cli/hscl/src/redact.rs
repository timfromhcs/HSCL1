//! Redaction of identifying values (AGENTS.md 8.3). Applied to everything `doctor`/`system info` prints.
//!
//! Known limitation, found by the `prop_` tests below: the marker itself reads `[redacted]`, so a
//! needle that is a substring of that word (`re`, `red`, `acted`) also matches inside a marker we
//! emitted ourselves. A second pass would then rewrite the marker, i.e. redaction is idempotent only
//! for needles that are not substrings of `[redacted]`. That is cosmetic - the identifying value is
//! already gone - and the alternative (a marker built from symbols) makes the report much harder to
//! read, so the limitation is documented and tested instead of hidden.

/// Marker written in place of a redacted value.
pub const MARKER: &str = "[redacted]";

/// Redact MAC addresses, IPv4 private ranges, and the given user/host names.
///
/// The user and host names are replaced in **one** pass over the input: replacing them one after the
/// other let the second needle rewrite the marker written for the first (`host = "re"` turned
/// `[redacted]` into `[[redacted]dacted]`).
pub fn redact(input: &str, user: &str, host: &str) -> String {
    let needles: Vec<&str> = [user, host].into_iter().filter(|n| n.len() >= 2).collect();
    let mut out = String::with_capacity(input.len());
    let mut rest = input;
    'outer: while !rest.is_empty() {
        let mut best: Option<(usize, usize)> = None;
        for needle in &needles {
            if let Some(i) = rest.find(needle) {
                if best.map(|(bi, _)| i < bi).unwrap_or(true) {
                    best = Some((i, needle.len()));
                }
            }
        }
        if let Some((i, len)) = best {
            out.push_str(&rest[..i]);
            out.push_str(MARKER);
            rest = &rest[i + len..];
            continue 'outer;
        }
        out.push_str(rest);
        break;
    }
    out.split_inclusive(char::is_whitespace)
        .map(|tok| {
            let t = tok.trim_end();
            let ws = &tok[t.len()..];
            if is_mac(t) || is_private_ipv4(t) {
                format!("{MARKER}{ws}")
            } else {
                tok.to_string()
            }
        })
        .collect()
}

/// The input with every marker removed. The property tests use it to ask "does the identifying value
/// still appear anywhere a reader could see it?" without tripping over the marker's own letters.
#[cfg(test)]
pub fn without_markers(text: &str) -> String {
    text.replace(MARKER, "")
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

/// G3: properties of the redaction, checked on generated input rather than on the three examples
/// above. The examples prove the feature; these prove it does not have holes for values nobody
/// thought to write down.
#[cfg(test)]
mod proptests {
    use super::*;
    use proptest::prelude::*;

    fn ident() -> impl Strategy<Value = String> {
        "[A-Za-z][A-Za-z0-9]{1,15}"
    }

    fn mac() -> impl Strategy<Value = String> {
        proptest::collection::vec(any::<u8>(), 6).prop_map(|bytes| {
            bytes
                .iter()
                .map(|b| format!("{b:02x}"))
                .collect::<Vec<_>>()
                .join(":")
        })
    }

    fn private_ip() -> impl Strategy<Value = String> {
        prop_oneof![
            (any::<u8>(), any::<u8>()).prop_map(|(a, b)| format!("10.{a}.{b}.1")),
            (any::<u8>(), any::<u8>()).prop_map(|(a, b)| format!("192.168.{a}.{b}")),
            (16u8..=31, any::<u8>()).prop_map(|(a, b)| format!("172.{a}.{b}.9")),
        ]
    }

    fn public_ip() -> impl Strategy<Value = String> {
        (1u8..=9, any::<u8>(), any::<u8>(), any::<u8>())
            .prop_map(|(a, b, c, d)| format!("{a}.{b}.{c}.{d}"))
    }

    proptest! {
        #[test]
        fn prop_redaction_is_idempotent(text in ".{0,300}", user in ident(), host in ident()) {
            // Excluded on purpose (documented in the module header): a needle that also occurs
            // inside the marker word makes a second pass rewrite the marker itself.
            prop_assume!(!MARKER.contains(&user) && !MARKER.contains(&host));
            let once = redact(&text, &user, &host);
            let twice = redact(&once, &user, &host);
            prop_assert_eq!(once, twice, "redacting twice changed the text");
        }

        #[test]
        fn prop_planted_user_and_host_never_survive(user in ident(), host in ident()) {
            let text = format!("login {user} on {host} ok");
            let out = redact(&text, &user, &host);
            // The marker's own letters do not count: ask what a reader still sees.
            let visible = without_markers(&out);
            prop_assert!(!visible.contains(&user), "user survived: {out}");
            prop_assert!(!visible.contains(&host), "host survived: {out}");
        }

        #[test]
        fn prop_the_neighbouring_needle_does_not_corrupt_the_marker(user in ident(), host in ident()) {
            // Regression for the two-pass rewrite: with user="aA" and host="re" the marker written
            // for the user used to become "[[redacted]dacted]". A needle may legitimately match
            // more than once ("in" inside "login"), so only the marker itself is checked here.
            let out = redact(&format!("host {user} box {host} end"), &user, &host);
            prop_assert!(!out.contains("[["), "marker was rewritten: {out}");
            let visible = without_markers(&out);
            prop_assert!(!visible.contains(&user), "user survived: {out}");
            prop_assert!(!visible.contains(&host), "host survived: {out}");
        }

        #[test]
        fn prop_mac_and_private_ipv4_never_survive(addr in mac(), ip in private_ip()) {
            let text = format!("dev {addr} ip {ip} end");
            let out = redact(&text, "u1", "h1");
            prop_assert!(!out.contains(&addr), "MAC survived: {out}");
            prop_assert!(!out.contains(&ip), "private IP survived: {out}");
        }

        #[test]
        fn prop_public_ipv4_is_kept(ip in public_ip()) {
            // A support report without the public address would be useless for connectivity triage;
            // only private ranges are identifying.
            let out = redact(&format!("tls {ip} ok"), "u1", "h1");
            prop_assert!(out.contains(&ip), "public IP was redacted: {out}");
        }
    }
}
