//! Parser for the AREX tool-call protocol (`<tool_call>` blocks, JSON or `<function=..><parameter=..>` body).
//!
//! The model proposes, the caller executes: this module only turns text into validated `Call`s. Names must be on the
//! allow-list (plus the built-in `finish`); nothing here runs anything.

// Temporary, tracked in docs/superpowers/plans/2026-11-06-ai-api-updates-stress.md (Task D4): the consumer
// (`hscl agent run`, via agent.rs) lands in the next tasks; remove this allow when it is wired.
#![allow(dead_code)]

use serde_json::Value;

pub const MAX_BODY: usize = 64 * 1024;

#[derive(Debug, PartialEq)]
pub enum Call {
    Tool { name: String, args: Value },
    Finish { answer: String },
}

#[derive(Debug, PartialEq)]
pub enum ParseError {
    Incomplete,
    UnknownTool(String),
    Duplicate(String),
    TooLarge,
    Nested,
    Malformed(String),
}

const OPEN: &str = "<tool_call>";
const CLOSE: &str = "</tool_call>";

fn valid_name(n: &str) -> bool {
    !n.is_empty() && n.len() <= 40 && n.bytes().all(|b| b.is_ascii_alphanumeric() || b == b'_')
}

/// Text between the markers, with one leading and one trailing newline removed (as models print values on their own lines).
fn trim_value(v: &str) -> String {
    let v = v.strip_prefix('\n').unwrap_or(v);
    v.strip_suffix('\n').unwrap_or(v).to_string()
}

fn parse_xml(body: &str) -> Result<(String, Value), ParseError> {
    let b = body.trim();
    let rest = b
        .strip_prefix("<function=")
        .ok_or_else(|| ParseError::Malformed("expected <function=NAME>".into()))?;
    let (name, mut rest) = rest
        .split_once('>')
        .ok_or_else(|| ParseError::Malformed("unterminated function tag".into()))?;
    if !valid_name(name) {
        return Err(ParseError::Malformed(format!("bad tool name {name:?}")));
    }
    let mut args = serde_json::Map::new();
    loop {
        rest = rest.trim_start();
        if let Some(r) = rest.strip_prefix("<parameter=") {
            let (key, r) = r
                .split_once('>')
                .ok_or_else(|| ParseError::Malformed("unterminated parameter tag".into()))?;
            if !valid_name(key) {
                return Err(ParseError::Malformed(format!("bad parameter name {key:?}")));
            }
            let (val, r) = r.split_once("</parameter>").ok_or(ParseError::Incomplete)?;
            if args.contains_key(key) {
                return Err(ParseError::Duplicate(key.to_string()));
            }
            args.insert(key.to_string(), Value::String(trim_value(val)));
            rest = r;
        } else if rest.starts_with("</function>") {
            return Ok((name.to_string(), Value::Object(args)));
        } else if rest.is_empty() {
            return Err(ParseError::Incomplete);
        } else {
            return Err(ParseError::Malformed(
                "unexpected text inside function".into(),
            ));
        }
    }
}

fn parse_json(body: &str) -> Result<(String, Value), ParseError> {
    let v: Value =
        serde_json::from_str(body.trim()).map_err(|e| ParseError::Malformed(e.to_string()))?;
    let name = v
        .get("name")
        .and_then(Value::as_str)
        .ok_or_else(|| ParseError::Malformed("missing name".into()))?;
    if !valid_name(name) {
        return Err(ParseError::Malformed(format!("bad tool name {name:?}")));
    }
    let args = v
        .get("arguments")
        .cloned()
        .unwrap_or_else(|| Value::Object(Default::default()));
    if !args.is_object() {
        return Err(ParseError::Malformed("arguments must be an object".into()));
    }
    Ok((name.to_string(), args))
}

pub fn parse(text: &str, allow: &[&str]) -> Result<Vec<Call>, ParseError> {
    let mut out = Vec::new();
    let mut rest = text;
    while let Some(i) = rest.find(OPEN) {
        let after = &rest[i + OPEN.len()..];
        let end = after.find(CLOSE);
        let body = &after[..end.unwrap_or(after.len())];
        if body.contains(OPEN) {
            return Err(ParseError::Nested);
        }
        if body.len() > MAX_BODY {
            return Err(ParseError::TooLarge);
        }
        let end = end.ok_or(ParseError::Incomplete)?;
        let (name, args) = if body.trim_start().starts_with('{') {
            parse_json(body)?
        } else {
            parse_xml(body)?
        };
        if name == "finish" {
            let answer = args
                .get("answer")
                .and_then(Value::as_str)
                .unwrap_or("")
                .to_string();
            out.push(Call::Finish { answer });
        } else if allow.contains(&name.as_str()) {
            out.push(Call::Tool { name, args });
        } else {
            return Err(ParseError::UnknownTool(name));
        }
        rest = &after[end + CLOSE.len()..];
    }
    Ok(out)
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    const ALLOW: &[&str] = &["read_doc", "update_context"];

    #[test]
    fn json_body_is_parsed() {
        let t = "thinking...\n<tool_call>\n{\"name\": \"read_doc\", \"arguments\": {\"path\": \"docs/CLI.md\"}}\n</tool_call>";
        assert_eq!(
            parse(t, ALLOW).unwrap(),
            vec![Call::Tool {
                name: "read_doc".into(),
                args: json!({"path": "docs/CLI.md"})
            }]
        );
    }

    #[test]
    fn xml_body_is_parsed_and_finish_is_builtin() {
        let t = "<tool_call>\n<function=update_context>\n<parameter=notes>\nverified A\n</parameter>\n</function>\n</tool_call>\n\
                 <tool_call><function=finish><parameter=answer>done</parameter></function></tool_call>";
        assert_eq!(
            parse(t, ALLOW).unwrap(),
            vec![
                Call::Tool {
                    name: "update_context".into(),
                    args: json!({"notes": "verified A"})
                },
                Call::Finish {
                    answer: "done".into()
                },
            ]
        );
    }

    #[test]
    fn text_without_calls_is_an_empty_list() {
        assert_eq!(parse("just an answer", ALLOW).unwrap(), vec![]);
    }

    #[test]
    fn unknown_tool_is_refused_not_executed() {
        let t =
            "<tool_call><function=bash><parameter=cmd>rm -rf /</parameter></function></tool_call>";
        assert_eq!(parse(t, ALLOW), Err(ParseError::UnknownTool("bash".into())));
    }

    #[test]
    fn truncated_block_is_incomplete() {
        assert_eq!(
            parse("<tool_call><function=read_doc><parameter=path>x", ALLOW),
            Err(ParseError::Incomplete)
        );
    }

    #[test]
    fn nested_block_is_refused() {
        let t = "<tool_call><tool_call><function=read_doc></function></tool_call></tool_call>";
        assert_eq!(parse(t, ALLOW), Err(ParseError::Nested));
    }

    #[test]
    fn duplicate_parameter_is_refused() {
        let t = "<tool_call><function=read_doc><parameter=path>a</parameter><parameter=path>b</parameter></function></tool_call>";
        assert_eq!(parse(t, ALLOW), Err(ParseError::Duplicate("path".into())));
    }

    #[test]
    fn oversized_body_is_refused() {
        let t = format!("<tool_call>{}</tool_call>", "a".repeat(MAX_BODY + 1));
        assert_eq!(parse(&t, ALLOW), Err(ParseError::TooLarge));
    }

    #[test]
    fn bad_tool_name_characters_are_malformed() {
        let t =
            "<tool_call><function=read_doc;ls><parameter=a>b</parameter></function></tool_call>";
        assert!(matches!(
            parse(t, ALLOW),
            Err(ParseError::Malformed(_)) | Err(ParseError::UnknownTool(_))
        ));
    }

    #[test]
    fn seeded_fuzz_never_panics() {
        let alphabet: Vec<&str> = vec![
            "<tool_call>",
            "</tool_call>",
            "<function=",
            "read_doc",
            ">",
            "</function>",
            "<parameter=",
            "k",
            "</parameter>",
            "{",
            "}",
            "\"name\"",
            ":",
            "\"",
            "finish",
            "\n",
            "é",
            "\u{0}",
        ];
        let mut x: u64 = 0x9E3779B97F4A7C15;
        for _ in 0..20000 {
            let mut s = String::new();
            for _ in 0..(1 + (x % 14)) {
                x ^= x << 13;
                x ^= x >> 7;
                x ^= x << 17;
                s.push_str(alphabet[(x % alphabet.len() as u64) as usize]);
            }
            let _ = parse(&s, ALLOW);
        }
    }
}
