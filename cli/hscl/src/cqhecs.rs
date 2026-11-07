//! `hscl cqhecs status`: a read-only view of the CQ-HECS runtime that the `hscl-cqhecs` package manages.
//!
//! It does not detect anything itself. It runs the package launcher's own `doctor --json` (fixed argv, no shell, short
//! timeout, bounded output) and reports what the launcher says, or that the package is not installed. It never starts the
//! Studio, installs a runtime or opens a network connection.

use serde_json::{json, Value};
use std::io::Read;
use std::path::{Path, PathBuf};
use std::process::{Command, Stdio};
use std::time::{Duration, Instant};

const LAUNCHER: &str = "hscl-cqhecs";
const TIMEOUT: Duration = Duration::from_secs(10);
/// After the launcher has exited or been killed, how long to wait for its remaining output.
const OUTPUT_GRACE: Duration = Duration::from_secs(1);
const MAX_OUTPUT: usize = 64 * 1024;
const MAX_FIELD: usize = 512;

/// Where the launcher is: an absolute override (for tests and unusual installs), `/usr/bin`, or `PATH`.
pub fn locate_launcher(
    override_path: Option<&str>,
    path_var: Option<&std::ffi::OsStr>,
) -> Option<PathBuf> {
    if let Some(p) = override_path {
        let p = PathBuf::from(p);
        // an override must be an absolute path to an existing file; anything else is ignored, not guessed
        return (p.is_absolute() && p.is_file()).then_some(p);
    }
    let fixed = Path::new("/usr/bin").join(LAUNCHER);
    if fixed.is_file() {
        return Some(fixed);
    }
    path_var.and_then(|p| {
        std::env::split_paths(p)
            .map(|d| d.join(LAUNCHER))
            .find(|c| c.is_file())
    })
}

/// Text from another program is shown to a terminal: drop control characters and bound the length.
fn clean(s: &str) -> String {
    s.chars()
        .filter(|c| !c.is_control())
        .take(MAX_FIELD)
        .collect()
}

/// Turn the launcher's `doctor --json` output (and exit code) into the status we report.
pub fn interpret(stdout: &str, exit_code: Option<i32>) -> Value {
    let parsed: Result<Value, _> = serde_json::from_str(stdout.trim());
    let Ok(Value::Object(map)) = parsed else {
        return json!({
            "runtime": "unknown",
            "detail": "the launcher did not return a JSON object",
            "launcher_exit_code": exit_code,
        });
    };
    let field = |k: &str| map.get(k).and_then(Value::as_str).map(clean);
    let runtime = match field("runtime").as_deref() {
        Some("ok") => "ok",
        Some("missing") => "missing",
        Some("broken") => "broken",
        _ => "unknown",
    };
    json!({
        "runtime": runtime,
        "venv": field("venv"),
        "data_dir": field("data_dir"),
        "network": field("network"),
        "launcher_exit_code": exit_code,
    })
}

fn hint(package_installed: bool, runtime: &str) -> &'static str {
    match (package_installed, runtime) {
        (false, _) => "the hscl-cqhecs package is not installed",
        (true, "ok") => "runtime ready",
        (true, "missing") => {
            "run `hscl-cqhecs install-runtime` (it shows the download size and asks first)"
        }
        (true, "broken") => "run `hscl-cqhecs doctor` for details",
        _ => "status could not be read; run `hscl-cqhecs doctor`",
    }
}

fn run_doctor(launcher: &Path) -> std::io::Result<(String, Option<i32>)> {
    let mut child = Command::new(launcher)
        .args(["doctor", "--json"])
        .stdin(Stdio::null())
        .stdout(Stdio::piped())
        .stderr(Stdio::null())
        .spawn()?;
    let mut out = child.stdout.take().expect("piped");
    // Read on a helper thread that reports through a channel. Killing the launcher does not close the pipe if it
    // started a child of its own (a grandchild keeps the write end open), so the wait for the output must be bounded
    // too; the helper thread is then left to finish on its own.
    let (tx, rx) = std::sync::mpsc::channel();
    std::thread::spawn(move || {
        let mut buf = Vec::new();
        let _ = (&mut out).take(MAX_OUTPUT as u64).read_to_end(&mut buf);
        let _ = tx.send(buf);
    });
    let start = Instant::now();
    let code = loop {
        if let Some(status) = child.try_wait()? {
            break status.code();
        }
        if start.elapsed() > TIMEOUT {
            let _ = child.kill();
            let _ = child.wait();
            break None;
        }
        std::thread::sleep(Duration::from_millis(20));
    };
    let bytes = rx.recv_timeout(OUTPUT_GRACE).unwrap_or_default();
    Ok((String::from_utf8_lossy(&bytes).into_owned(), code))
}

/// The full report for `hscl cqhecs status`.
pub fn status(override_path: Option<&str>, path_var: Option<&std::ffi::OsStr>) -> Value {
    let Some(launcher) = locate_launcher(override_path, path_var) else {
        return json!({
            "package": "not_installed",
            "launcher": Value::Null,
            "runtime": "unknown",
            "hint": hint(false, "unknown"),
        });
    };
    let mut report = match run_doctor(&launcher) {
        Ok((stdout, code)) => interpret(&stdout, code),
        Err(_) => json!({"runtime": "unknown", "detail": "the launcher could not be started"}),
    };
    let runtime = report["runtime"].as_str().unwrap_or("unknown").to_string();
    if let Value::Object(m) = &mut report {
        m.insert("package".into(), json!("installed"));
        m.insert("launcher".into(), json!(launcher.display().to_string()));
        m.insert("hint".into(), json!(hint(true, &runtime)));
    }
    report
}

pub fn render(v: &Value) -> String {
    let s = |k: &str| v.get(k).and_then(Value::as_str).unwrap_or("-").to_string();
    format!(
        "package: {}\nlauncher: {}\nruntime: {}\ndata dir: {}\nnetwork: {}\n{}",
        s("package"),
        s("launcher"),
        s("runtime"),
        s("data_dir"),
        s("network"),
        s("hint")
    )
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn interprets_the_three_launcher_states() {
        for (rt, want) in [("ok", "ok"), ("missing", "missing"), ("broken", "broken")] {
            let out = format!(
                r#"{{"runtime":"{rt}","venv":"/home/u/.local/share/hscl/cqhecs/venv","data_dir":"/home/u/.local/share/hscl/cqhecs","network":"not used"}}"#
            );
            let v = interpret(&out, Some(0));
            assert_eq!(v["runtime"], want);
            assert_eq!(v["network"], "not used");
            assert_eq!(v["data_dir"], "/home/u/.local/share/hscl/cqhecs");
        }
    }

    #[test]
    fn anything_that_is_not_a_json_object_is_unknown_not_ok() {
        for bad in [
            "",
            "not json",
            "[1,2]",
            "\"ok\"",
            "42",
            "null",
            "{\"runtime\":",
        ] {
            assert_eq!(interpret(bad, Some(0))["runtime"], "unknown", "{bad:?}");
        }
    }

    #[test]
    fn an_unrecognised_runtime_value_is_unknown() {
        for rt in ["OK", "okay", "", "ok; rm -rf", "1", "true"] {
            let out = format!(r#"{{"runtime":"{rt}"}}"#);
            assert_eq!(interpret(&out, Some(0))["runtime"], "unknown", "{rt:?}");
        }
        assert_eq!(interpret(r#"{"runtime":5}"#, None)["runtime"], "unknown");
    }

    #[test]
    fn control_characters_and_long_values_from_the_launcher_are_not_passed_to_the_terminal() {
        let nasty = format!(
            r#"{{"runtime":"ok","venv":"/x\u001b[31mred\u0007\u0000","data_dir":"{}"}}"#,
            "a".repeat(5000)
        );
        let v = interpret(&nasty, Some(0));
        let venv = v["venv"].as_str().unwrap();
        assert!(!venv.chars().any(char::is_control), "{venv:?}");
        assert!(v["data_dir"].as_str().unwrap().len() <= MAX_FIELD);
    }

    #[test]
    fn the_override_must_be_an_absolute_existing_file() {
        assert!(locate_launcher(Some("relative/hscl-cqhecs"), None).is_none());
        assert!(locate_launcher(Some("/definitely/not/here"), None).is_none());
        let dir = std::env::temp_dir();
        assert!(
            locate_launcher(Some(dir.to_str().unwrap()), None).is_none(),
            "a directory is not a launcher"
        );
    }

    #[test]
    fn a_missing_package_is_reported_as_such() {
        let v = status(Some("/definitely/not/here"), Some(std::ffi::OsStr::new("")));
        assert_eq!(v["package"], "not_installed");
        assert_eq!(v["runtime"], "unknown");
        assert!(v["hint"].as_str().unwrap().contains("not installed"));
    }

    #[test]
    fn hints_never_claim_a_working_runtime_without_ok() {
        for rt in ["missing", "broken", "unknown"] {
            assert!(!hint(true, rt).contains("ready"));
        }
        assert!(hint(true, "ok").contains("ready"));
    }

    #[cfg(unix)]
    mod launcher_process {
        use super::*;
        use std::os::unix::fs::PermissionsExt;

        fn fake(body: &str) -> (tempdir_lite::Dir, PathBuf) {
            let dir = tempdir_lite::Dir::new();
            let path = dir.path().join("hscl-cqhecs");
            std::fs::write(&path, format!("#!/bin/sh\n{body}\n")).unwrap();
            std::fs::set_permissions(&path, std::fs::Permissions::from_mode(0o755)).unwrap();
            (dir, path)
        }

        /// Minimal temp dir (no extra dependency): removed on drop.
        mod tempdir_lite {
            use std::path::{Path, PathBuf};
            pub struct Dir(PathBuf);
            impl Dir {
                pub fn new() -> Self {
                    let p = std::env::temp_dir().join(format!(
                        "hscl-cqhecs-test-{}-{:?}",
                        std::process::id(),
                        std::thread::current().id()
                    ));
                    let _ = std::fs::remove_dir_all(&p);
                    std::fs::create_dir_all(&p).unwrap();
                    Dir(p)
                }
                pub fn path(&self) -> &Path {
                    &self.0
                }
            }
            impl Drop for Dir {
                fn drop(&mut self) {
                    let _ = std::fs::remove_dir_all(&self.0);
                }
            }
        }

        #[test]
        fn runs_the_launcher_with_fixed_arguments_and_reports_its_answer() {
            let (_d, p) = fake(
                r#"[ "$1" = doctor ] && [ "$2" = --json ] && [ "$#" -eq 2 ] || exit 9
printf '{"runtime":"missing","venv":"/v","data_dir":"/d","network":"not used"}\n'
exit 3"#,
            );
            let v = status(Some(p.to_str().unwrap()), None);
            assert_eq!(v["package"], "installed");
            assert_eq!(v["runtime"], "missing");
            assert_eq!(v["launcher_exit_code"], 3);
            assert!(v["hint"].as_str().unwrap().contains("install-runtime"));
        }

        #[test]
        fn a_launcher_that_prints_garbage_gives_unknown() {
            let (_d, p) = fake("echo this is not json; exit 0");
            assert_eq!(
                status(Some(p.to_str().unwrap()), None)["runtime"],
                "unknown"
            );
        }

        #[test]
        fn a_hung_launcher_is_killed_at_the_timeout() {
            let (_d, p) = fake("sleep 60");
            let t = Instant::now();
            let v = status(Some(p.to_str().unwrap()), None);
            assert!(
                t.elapsed() < TIMEOUT + OUTPUT_GRACE + Duration::from_secs(4),
                "{:?}",
                t.elapsed()
            );
            assert_eq!(v["runtime"], "unknown");
        }

        #[test]
        fn an_output_flood_is_bounded() {
            let (_d, p) = fake("head -c 5000000 /dev/zero | tr '\\0' 'a'; exit 0");
            let t = Instant::now();
            let v = status(Some(p.to_str().unwrap()), None);
            assert_eq!(v["runtime"], "unknown");
            assert!(t.elapsed() < Duration::from_secs(15));
        }

        #[test]
        fn the_launcher_is_found_on_path_when_there_is_no_override() {
            let (d, _p) = fake(r#"printf '{"runtime":"ok"}'"#);
            let found = locate_launcher(None, Some(d.path().as_os_str()));
            // /usr/bin/hscl-cqhecs wins when the package is really installed on this machine
            assert!(found.is_some());
        }
    }
}
