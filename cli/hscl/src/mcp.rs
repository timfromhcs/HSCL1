//! `hscl mcp` - a Model Context Protocol server (stdio, JSON-RPC 2.0, newline-delimited) that exposes the `hscl` CLI to local agents.
//!
//! Read-only by default. Write tools exist only with `--allow-write`. Every tool maps to a fixed `hscl` argument vector built from
//! validated arguments (no shell, no free-form command text); the server re-runs its own binary, so there is one code path and one
//! set of safety checks. Nothing listens on a network port.

use anyhow::{anyhow, Result};
use serde_json::{json, Value};
use std::io::{BufRead, Write};

pub const PROTOCOL: &str = "2024-11-05";

pub trait Exec {
    /// Run `hscl <args> --json` and return (exit code, stdout).
    fn run(&self, args: &[String]) -> Result<(i32, String)>;
}

pub struct SelfExec;

impl Exec for SelfExec {
    fn run(&self, args: &[String]) -> Result<(i32, String)> {
        let out = std::process::Command::new(std::env::current_exe()?)
            .args(args)
            .arg("--json")
            .output()?;
        Ok((
            out.status.code().unwrap_or(-1),
            String::from_utf8_lossy(&out.stdout).into_owned(),
        ))
    }
}

struct Tool {
    name: &'static str,
    desc: &'static str,
    write: bool,
    schema: fn() -> Value,
    args: fn(&Value) -> Result<Vec<String>>,
}

fn empty() -> Value {
    json!({"type": "object", "properties": {}, "additionalProperties": false})
}

fn valid_id(s: &str, max: usize) -> bool {
    !s.is_empty()
        && s.len() <= max
        && s.bytes()
            .all(|b| b.is_ascii_lowercase() || b.is_ascii_digit() || b == b'-' || b == b'.')
}

fn str_arg<'a>(a: &'a Value, k: &str) -> Result<&'a str> {
    a.get(k)
        .and_then(Value::as_str)
        .ok_or_else(|| anyhow!("missing string argument: {k}"))
}

fn no_extra(a: &Value, allowed: &[&str]) -> Result<()> {
    if let Some(o) = a.as_object() {
        for k in o.keys() {
            if !allowed.contains(&k.as_str()) {
                return Err(anyhow!("unknown argument: {k}"));
            }
        }
    }
    Ok(())
}

fn v(parts: &[&str]) -> Vec<String> {
    parts.iter().map(|s| s.to_string()).collect()
}

fn tools() -> Vec<Tool> {
    vec![
        Tool { name: "hscl_version", desc: "HSCL1 version.", write: false, schema: empty, args: |a| { no_extra(a, &[])?; Ok(v(&["version"])) } },
        Tool { name: "hscl_status", desc: "OS, architecture and security summary.", write: false, schema: empty, args: |a| { no_extra(a, &[])?; Ok(v(&["status"])) } },
        Tool { name: "hscl_doctor", desc: "Diagnostics (read-only).", write: false, schema: empty, args: |a| { no_extra(a, &[])?; Ok(v(&["doctor"])) } },
        Tool { name: "hscl_system_info", desc: "OS, kernel, CPU, memory (identifiers redacted).", write: false, schema: empty, args: |a| { no_extra(a, &[])?; Ok(v(&["system", "info"])) } },
        Tool { name: "hscl_security_status", desc: "Firewall, AppArmor, Secure Boot, encryption, APT source hygiene.", write: false, schema: empty, args: |a| { no_extra(a, &[])?; Ok(v(&["security", "status"])) } },
        Tool { name: "hscl_updates_check", desc: "Pending APT updates (simulation, installs nothing).", write: false, schema: empty, args: |a| { no_extra(a, &[])?; Ok(v(&["system", "updates", "--check"])) } },
        Tool { name: "hscl_ai_detect", desc: "CPU/RAM/GPU/Vulkan detection for local inference.", write: false, schema: empty, args: |a| { no_extra(a, &[])?; Ok(v(&["ai", "detect"])) } },
        Tool { name: "hscl_ai_models", desc: "Catalog models with fit information for this machine.", write: false, schema: empty, args: |a| { no_extra(a, &[])?; Ok(v(&["ai", "model", "list"])) } },
        Tool {
            name: "hscl_ai_profile",
            desc: "Hardware-adapted llama.cpp run plan for a catalog model (default: best recommendation).",
            write: false,
            schema: || json!({"type": "object", "properties": {"model": {"type": "string"}, "low_vram": {"type": "boolean"}}, "additionalProperties": false}),
            args: |a| {
                no_extra(a, &["model", "low_vram"])?;
                let mut r = v(&["ai", "profile"]);
                if let Some(m) = a.get("model") {
                    let m = m.as_str().ok_or_else(|| anyhow!("model must be a string"))?;
                    if !valid_id(m, 64) {
                        return Err(anyhow!("invalid model id"));
                    }
                    r.push(m.into());
                }
                if a.get("low_vram").and_then(Value::as_bool).unwrap_or(false) {
                    r.push("--low-vram".into());
                }
                Ok(r)
            },
        },
        Tool { name: "hscl_graphics_detect", desc: "Detected graphics hardware and the profile it maps to.", write: false, schema: empty, args: |a| { no_extra(a, &[])?; Ok(v(&["graphics", "detect"])) } },
        Tool { name: "hscl_memory_status", desc: "RAM, zram swap, and local AI memory headroom.", write: false, schema: empty, args: |a| { no_extra(a, &[])?; Ok(v(&["memory", "status"])) } },
        Tool { name: "hscl_cqhecs_status", desc: "CQ-HECS runtime status (read-only, wraps doctor --json).", write: false, schema: empty, args: |a| { no_extra(a, &[])?; Ok(v(&["cqhecs", "status"])) } },
        Tool { name: "hscl_lab_status", desc: "Security Lab container engine and toolset configuration.", write: false, schema: empty, args: |a| { no_extra(a, &[])?; Ok(v(&["lab", "status"])) } },
        Tool { name: "hscl_wallpaper_list", desc: "Available wallpaper shader presets and current settings.", write: false, schema: empty, args: |a| { no_extra(a, &[])?; Ok(v(&["wallpaper", "list"])) } },
        Tool {
            name: "hscl_wallpaper_apply",
            desc: "Switch the active desktop wallpaper preset. Needs --allow-write.",
            write: true,
            schema: || json!({"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"], "additionalProperties": false}),
            args: |a| {
                no_extra(a, &["name"])?;
                let n = str_arg(a, "name")?;
                if !valid_id(n, 32) {
                    return Err(anyhow!("invalid wallpaper preset name"));
                }
                Ok(v(&["wallpaper", "apply", n]))
            },
        },
        Tool { name: "hscl_theme_list", desc: "Available HCS themes and the current one.", write: false, schema: empty, args: |a| { no_extra(a, &[])?; Ok(v(&["appearance", "theme", "list"])) } },
        Tool {
            name: "hscl_theme_set",
            desc: "Apply an HCS theme (writes a backup first). Needs --allow-write.",
            write: true,
            schema: || json!({"type": "object", "properties": {"name": {"type": "string"}, "dry_run": {"type": "boolean"}}, "required": ["name"], "additionalProperties": false}),
            args: |a| {
                no_extra(a, &["name", "dry_run"])?;
                let n = str_arg(a, "name")?;
                if !n.starts_with("hcs-") || !valid_id(n, 24) {
                    return Err(anyhow!("invalid theme name"));
                }
                let mut r = v(&["appearance", "theme", "set", n]);
                if a.get("dry_run").and_then(Value::as_bool).unwrap_or(false) {
                    r.push("--dry-run".into());
                }
                Ok(r)
            },
        },
        Tool {
            name: "hscl_graphics_apply",
            desc: "Apply the graphics profile for this machine. Needs --allow-write.",
            write: true,
            schema: || json!({"type": "object", "properties": {"force": {"type": "boolean"}, "dry_run": {"type": "boolean"}}, "additionalProperties": false}),
            args: |a| {
                no_extra(a, &["force", "dry_run"])?;
                let mut r = v(&["graphics", "apply"]);
                for k in ["force", "dry_run"] {
                    if a.get(k).and_then(Value::as_bool).unwrap_or(false) {
                        r.push(format!("--{}", k.replace('_', "-")));
                    }
                }
                Ok(r)
            },
        },
    ]
}

fn ok(id: &Value, result: Value) -> Value {
    json!({"jsonrpc": "2.0", "id": id, "result": result})
}

fn err(id: &Value, code: i64, msg: &str) -> Value {
    json!({"jsonrpc": "2.0", "id": id, "error": {"code": code, "message": msg}})
}

/// Handle one message; `None` for notifications.
pub fn handle(msg: &Value, allow_write: bool, exec: &dyn Exec) -> Option<Value> {
    let id = msg.get("id")?.clone();
    let method = msg.get("method").and_then(Value::as_str).unwrap_or("");
    let all = tools();
    Some(match method {
        "initialize" => ok(
            &id,
            json!({"protocolVersion": PROTOCOL, "capabilities": {"tools": {}}, "serverInfo": {"name": "hscl", "version": env!("CARGO_PKG_VERSION")}, "instructions": format!("HSCL1 system tools. {}", if allow_write { "Write tools are enabled." } else { "Read-only: write tools are disabled." })}),
        ),
        "ping" => ok(&id, json!({})),
        "tools/list" => ok(
            &id,
            json!({"tools": all.iter().filter(|t| allow_write || !t.write).map(|t| json!({"name": t.name, "description": t.desc, "inputSchema": (t.schema)()})).collect::<Vec<_>>()}),
        ),
        "tools/call" => {
            let p = msg.get("params").cloned().unwrap_or(json!({}));
            let name = p.get("name").and_then(Value::as_str).unwrap_or("");
            let Some(t) = all.iter().find(|t| t.name == name) else {
                return Some(err(&id, -32602, &format!("unknown tool: {name}")));
            };
            if t.write && !allow_write {
                return Some(err(
                    &id,
                    -32602,
                    "this tool needs the server to be started with --allow-write",
                ));
            }
            let args = p.get("arguments").cloned().unwrap_or(json!({}));
            if !args.is_object() {
                return Some(err(&id, -32602, "arguments must be an object"));
            }
            match (t.args)(&args) {
                Err(e) => err(&id, -32602, &e.to_string()),
                Ok(argv) => match exec.run(&argv) {
                    Ok((code, out)) => ok(
                        &id,
                        json!({"content": [{"type": "text", "text": out}], "isError": code != 0 && code != 3}),
                    ),
                    Err(e) => ok(
                        &id,
                        json!({"content": [{"type": "text", "text": format!("{e}")}], "isError": true}),
                    ),
                },
            }
        }
        _ => err(&id, -32601, &format!("method not found: {method}")),
    })
}

pub fn serve(
    allow_write: bool,
    input: impl BufRead,
    mut output: impl Write,
    exec: &dyn Exec,
) -> Result<()> {
    for line in input.lines() {
        let line = line?;
        if line.trim().is_empty() {
            continue;
        }
        let resp = match serde_json::from_str::<Value>(&line) {
            Ok(m) if m.is_object() => handle(&m, allow_write, exec),
            Ok(_) => Some(err(&Value::Null, -32600, "invalid request")),
            Err(_) => Some(err(&Value::Null, -32700, "parse error")),
        };
        if let Some(r) = resp {
            writeln!(output, "{r}")?;
            output.flush()?;
        }
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::cell::RefCell;

    #[derive(Default)]
    struct Rec(RefCell<Vec<Vec<String>>>);
    impl Exec for Rec {
        fn run(&self, a: &[String]) -> Result<(i32, String)> {
            self.0.borrow_mut().push(a.to_vec());
            Ok((0, "{\"ok\":true}".into()))
        }
    }

    fn call(name: &str, args: Value, write: bool, rec: &Rec) -> Value {
        handle(&json!({"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":name,"arguments":args}}), write, rec).unwrap()
    }

    #[test]
    fn initialize_ping_and_notifications() {
        let r = Rec::default();
        let i = handle(
            &json!({"jsonrpc":"2.0","id":1,"method":"initialize"}),
            false,
            &r,
        )
        .unwrap();
        assert_eq!(i["result"]["protocolVersion"], PROTOCOL);
        assert!(i["result"]["instructions"]
            .as_str()
            .unwrap()
            .contains("Read-only"));
        assert!(handle(
            &json!({"jsonrpc":"2.0","method":"notifications/initialized"}),
            false,
            &r
        )
        .is_none());
        assert_eq!(
            handle(&json!({"jsonrpc":"2.0","id":2,"method":"ping"}), false, &r).unwrap()["result"],
            json!({})
        );
    }

    #[test]
    fn read_only_by_default_write_tools_hidden_and_refused() {
        let r = Rec::default();
        let list = handle(
            &json!({"jsonrpc":"2.0","id":1,"method":"tools/list"}),
            false,
            &r,
        )
        .unwrap();
        let names: Vec<_> = list["result"]["tools"]
            .as_array()
            .unwrap()
            .iter()
            .map(|t| t["name"].as_str().unwrap().to_string())
            .collect();
        assert!(
            names.contains(&"hscl_status".to_string())
                && !names.contains(&"hscl_theme_set".to_string())
        );
        let refused = call("hscl_theme_set", json!({"name":"hcs-nord"}), false, &r);
        assert!(refused["error"]["message"]
            .as_str()
            .unwrap()
            .contains("--allow-write"));
        assert!(r.0.borrow().is_empty(), "nothing was executed");
        let listw = handle(
            &json!({"jsonrpc":"2.0","id":1,"method":"tools/list"}),
            true,
            &r,
        )
        .unwrap();
        assert!(listw["result"]["tools"]
            .as_array()
            .unwrap()
            .iter()
            .any(|t| t["name"] == "hscl_theme_set"));
    }

    #[test]
    fn every_tool_has_a_closed_schema_and_no_tool_takes_a_command() {
        let r = Rec::default();
        let list = handle(
            &json!({"jsonrpc":"2.0","id":1,"method":"tools/list"}),
            true,
            &r,
        )
        .unwrap();
        for t in list["result"]["tools"].as_array().unwrap() {
            assert_eq!(
                t["inputSchema"]["additionalProperties"], false,
                "{}",
                t["name"]
            );
            assert!(!["exec", "shell", "run", "command"]
                .iter()
                .any(|bad| t["name"].as_str().unwrap().contains(bad)));
        }
    }

    #[test]
    fn tool_calls_map_to_fixed_argument_vectors() {
        let r = Rec::default();
        call("hscl_status", json!({}), false, &r);
        call(
            "hscl_ai_profile",
            json!({"model":"qwen3.5-4b-abliterated","low_vram":true}),
            false,
            &r,
        );
        call(
            "hscl_theme_set",
            json!({"name":"hcs-nord","dry_run":true}),
            true,
            &r,
        );
        call("hscl_graphics_apply", json!({"force":true}), true, &r);
        call("hscl_cqhecs_status", json!({}), false, &r);
        call("hscl_memory_status", json!({}), false, &r);
        call("hscl_lab_status", json!({}), false, &r);
        call("hscl_wallpaper_list", json!({}), false, &r);
        call("hscl_wallpaper_apply", json!({"name":"rain"}), true, &r);
        let c = r.0.borrow();
        assert_eq!(c[0], ["status"]);
        assert_eq!(
            c[1],
            ["ai", "profile", "qwen3.5-4b-abliterated", "--low-vram"]
        );
        assert_eq!(
            c[2],
            ["appearance", "theme", "set", "hcs-nord", "--dry-run"]
        );
        assert_eq!(c[3], ["graphics", "apply", "--force"]);
        assert_eq!(c[4], ["cqhecs", "status"]);
        assert_eq!(c[5], ["memory", "status"]);
        assert_eq!(c[6], ["lab", "status"]);
        assert_eq!(c[7], ["wallpaper", "list"]);
        assert_eq!(c[8], ["wallpaper", "apply", "rain"]);
    }

    #[test]
    fn invalid_arguments_are_rejected_before_anything_runs() {
        let r = Rec::default();
        for (name, args) in [
            ("hscl_theme_set", json!({"name":"../etc"})),
            ("hscl_theme_set", json!({"name":"hcs-a;rm -rf"})),
            ("hscl_theme_set", json!({"name":"midnight"})),
            ("hscl_theme_set", json!({})),
            ("hscl_ai_profile", json!({"model":"x y"})),
            ("hscl_ai_profile", json!({"model":"UPPER"})),
            ("hscl_status", json!({"extra":1})),
            ("hscl_cqhecs_status", json!({"extra":1})),
            ("hscl_memory_status", json!({"extra":1})),
            ("hscl_lab_status", json!({"extra":1})),
            ("hscl_wallpaper_list", json!({"extra":1})),
            ("hscl_wallpaper_apply", json!({"name":"bad/name"})),
            ("hscl_wallpaper_apply", json!({})),
            ("hscl_graphics_apply", json!({"evil":true})),
        ] {
            let resp = call(name, args, true, &r);
            assert_eq!(resp["error"]["code"], -32602, "{name}");
        }
        assert!(r.0.borrow().is_empty());
    }

    #[test]
    fn unknown_tool_method_and_bad_json_lines() {
        let r = Rec::default();
        assert_eq!(call("rm_rf", json!({}), true, &r)["error"]["code"], -32602);
        assert_eq!(
            handle(
                &json!({"jsonrpc":"2.0","id":3,"method":"resources/list"}),
                false,
                &r
            )
            .unwrap()["error"]["code"],
            -32601
        );
        let input =
            b"not json\n[1]\n{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"ping\"}\n".as_slice();
        let mut out = Vec::new();
        serve(false, input, &mut out, &r).unwrap();
        let lines: Vec<Value> = String::from_utf8(out)
            .unwrap()
            .lines()
            .map(|l| serde_json::from_str(l).unwrap())
            .collect();
        assert_eq!(lines[0]["error"]["code"], -32700);
        assert_eq!(lines[1]["error"]["code"], -32600);
        assert_eq!(lines[2]["result"], json!({}));
    }

    #[test]
    fn exit_code_3_from_doctor_is_not_a_tool_error() {
        struct Doc;
        impl Exec for Doc {
            fn run(&self, _: &[String]) -> Result<(i32, String)> {
                Ok((3, "{\"failed\":1}".into()))
            }
        }
        let resp = call("hscl_doctor", json!({}), false, &Rec::default());
        assert_eq!(resp["result"]["isError"], false);
        let resp2 = handle(&json!({"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"hscl_doctor","arguments":{}}}), false, &Doc).unwrap();
        assert_eq!(
            resp2["result"]["isError"], false,
            "a failing health check is a result, not a protocol failure"
        );
    }
}
