//! `hscl` - HSCL1 command line interface. Made with love by hcsmedia.
//!
//! Only commands with real implementations are exposed (AGENTS.md section 8.2).

mod ai;
mod doctor;
mod redact;
mod security;
mod sysinfo;

use clap::{Parser, Subcommand};
use serde_json::json;
use std::process::ExitCode;

pub const PRODUCT: &str = "HSCL1";
pub const CREDIT: &str = "Made with love by hcsmedia";

/// Stable exit codes (documented in docs/CLI.md).
pub mod exit {
    pub const OK: u8 = 0;
    pub const FAILURE: u8 = 1;
    /// `doctor` found at least one failing check.
    pub const CHECK_FAILED: u8 = 3;
}

#[derive(Parser)]
#[command(
    name = "hscl",
    version,
    about = "HSCL1 command line interface - Made with love by hcsmedia"
)]
struct Cli {
    /// Machine-readable JSON output where supported.
    #[arg(long, global = true)]
    json: bool,
    #[command(subcommand)]
    command: Cmd,
}

#[derive(Subcommand)]
enum Cmd {
    /// Print the HSCL1 version.
    Version,
    /// Short system status summary.
    Status,
    /// About HSCL1 and credits.
    About,
    /// Run diagnostics; non-zero exit when a check fails.
    Doctor {
        /// Include slower checks.
        #[arg(long)]
        full: bool,
    },
    /// System information.
    System {
        #[command(subcommand)]
        cmd: SystemCmd,
    },
    /// Security posture.
    Security {
        #[command(subcommand)]
        cmd: SecurityCmd,
    },
    /// Local AI tooling.
    Ai {
        #[command(subcommand)]
        cmd: AiCmd,
    },
}

#[derive(Subcommand)]
enum SystemCmd {
    /// OS, kernel, CPU, memory (identifiers redacted).
    Info,
}

#[derive(Subcommand)]
enum SecurityCmd {
    /// Firewall, AppArmor, Secure Boot, encryption, APT source hygiene.
    Status,
}

#[derive(Subcommand)]
enum AiCmd {
    /// Detect CPU/RAM/GPU/Vulkan for local inference.
    Detect,
}

fn print_value(as_json: bool, v: &serde_json::Value, human: impl FnOnce() -> String) {
    if as_json {
        println!("{}", serde_json::to_string_pretty(v).unwrap_or_default());
    } else {
        println!("{}", human());
    }
}

fn run(cli: Cli) -> anyhow::Result<u8> {
    let j = cli.json;
    match cli.command {
        Cmd::Version => {
            let v = json!({"product": PRODUCT, "version": env!("CARGO_PKG_VERSION")});
            print_value(j, &v, || format!("{PRODUCT} {}", env!("CARGO_PKG_VERSION")));
        }
        Cmd::About => {
            let v = json!({
                "product": PRODUCT, "version": env!("CARGO_PKG_VERSION"),
                "publisher": "HCSMEDIA", "credit": CREDIT,
                "notice": "HSCL1 is not Tails and not an official Kali release."
            });
            print_value(j, &v, || {
                format!(
                    "{PRODUCT} {}\n{CREDIT}\nHSCL1 is not Tails and not an official Kali release.",
                    env!("CARGO_PKG_VERSION")
                )
            });
        }
        Cmd::Status => {
            let s = sysinfo::collect();
            let sec = security::collect();
            let v = json!({"os": s.os_pretty, "arch": s.arch, "security": sec});
            print_value(j, &v, || {
                format!(
                    "{PRODUCT} on {} ({})\n{}",
                    s.os_pretty,
                    s.arch,
                    security::render(&sec)
                )
            });
        }
        Cmd::System {
            cmd: SystemCmd::Info,
        } => {
            let s = sysinfo::collect();
            let v = serde_json::to_value(&s)?;
            print_value(j, &v, || sysinfo::render(&s));
        }
        Cmd::Security {
            cmd: SecurityCmd::Status,
        } => {
            let sec = security::collect();
            let v = serde_json::to_value(&sec)?;
            print_value(j, &v, || security::render(&sec));
        }
        Cmd::Ai { cmd: AiCmd::Detect } => {
            let d = ai::detect();
            let v = serde_json::to_value(&d)?;
            print_value(j, &v, || ai::render(&d));
        }
        Cmd::Doctor { full } => {
            let report = doctor::run(full);
            let v = serde_json::to_value(&report)?;
            print_value(j, &v, || doctor::render(&report));
            if report.failed > 0 {
                return Ok(exit::CHECK_FAILED);
            }
        }
    }
    Ok(exit::OK)
}

fn main() -> ExitCode {
    tracing_subscriber::fmt()
        .with_env_filter(tracing_subscriber::EnvFilter::from_default_env())
        .with_writer(std::io::stderr)
        .init();
    match run(Cli::parse()) {
        Ok(code) => ExitCode::from(code),
        Err(e) => {
            eprintln!("hscl: error: {e:#}");
            ExitCode::from(exit::FAILURE)
        }
    }
}
