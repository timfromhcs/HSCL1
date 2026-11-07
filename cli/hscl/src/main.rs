//! `hscl` - HSCL1 command line interface. Made with love by hcsmedia.
//!
//! Only commands with real implementations are exposed (AGENTS.md section 8.2).

mod agent;
mod ai;
mod appearance;
mod catalog;
mod code;
mod doctor;
mod download;
mod gguf;
mod governor;
mod graphics;
mod hw;
mod lab;
mod mcp;
mod memory;
mod profile;
mod redact;
mod report;
mod security;
mod serve;
mod sysinfo;
mod toolcall;
mod updates;
mod wallpaper;

use clap::{Parser, Subcommand};
use serde_json::json;
use std::process::ExitCode;

pub const PRODUCT: &str = "HSCL1";
pub const CREDIT: &str = "Made with love by hcsmedia";
/// What HSCL1 stands for (owner decision 2026-11-06). The product name stays written `HSCL1`.
pub const EXPANSION: &str = "Hypercharged Supreme Computing Layout 1";

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
    command: Option<Cmd>,
}

#[derive(Subcommand)]
enum Cmd {
    /// Friendly overview of HSCL1 and where to start (also what `hscl1` with no arguments prints).
    Overview,
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
    /// Write a support report with user/host/MAC/private IP redacted.
    Report {
        /// Write JSON to this new file instead of stdout (never overwrites).
        #[arg(long, value_name = "PATH")]
        output: Option<std::path::PathBuf>,
    },
    /// Memory status and the AI RAM budget.
    Memory {
        #[command(subcommand)]
        cmd: MemoryCmd,
    },
    /// Low-VRAM mode for weak GPUs: caps the desktop effects and makes `ai profile` offload less.
    LowVram {
        /// on, off or status
        mode: String,
    },
    /// Wallpaper Studio: presets for the animated HSCL1 wallpaper effects.
    Wallpaper {
        #[command(subcommand)]
        cmd: WallpaperCmd,
    },
    /// HCS Coder: install, configure and launch open-source coding agents for the local model.
    Code {
        #[command(subcommand)]
        cmd: CodeCmd,
    },
    /// Print a shell completion script (bash, zsh, fish, elvish, powershell) for `hscl` and `hscl1`.
    Completions {
        /// Target shell.
        #[arg(value_enum)]
        shell: clap_complete::Shell,
    },
    /// Write roff man pages for `hscl`, `hscl1` and every command into DIR (packaged under /usr/share/man/man1).
    Man {
        /// Target directory; created when missing, refused when it is a file.
        #[arg(long)]
        out: std::path::PathBuf,
    },
    /// Model Context Protocol server on stdio for local agents (read-only unless --allow-write).
    Mcp {
        /// Also expose write tools (theme set, graphics apply).
        #[arg(long)]
        allow_write: bool,
    },
    /// Detect the graphics hardware and tune the desktop for it (Qt Quick backend, animations, blur, rain density).
    Graphics {
        #[command(subcommand)]
        cmd: GraphicsCmd,
    },
    /// Detect this machine and apply every automatic tuning (graphics now; AI profile is shown).
    Autotune {
        /// Print the plan only.
        #[arg(long)]
        dry_run: bool,
        /// Re-apply even if the hardware did not change.
        #[arg(long)]
        force: bool,
    },
    /// Hardware inventory from sysfs/procfs (read-only, no root): GPUs, CPU features, memory, firmware, Secure Boot.
    Hw {
        #[command(subcommand)]
        cmd: HwCmd,
    },
    /// Security Lab: isolated rootless-container workspaces (authorized testing only). Shows the podman command, never runs a shell.
    Lab {
        #[command(subcommand)]
        cmd: LabCmd,
    },
    /// Desktop appearance.
    Appearance {
        #[command(subcommand)]
        cmd: AppearanceCmd,
    },
}

#[derive(Subcommand)]
enum HwCmd {
    /// Detect devices and report them (nothing is installed or changed).
    Detect,
}

#[derive(Subcommand)]
enum LabCmd {
    /// Is podman present, is the lab folder there, and which toolsets exist.
    Status,
    /// Create the lab root folder (~/SecurityLabs, mode 0700).
    Setup,
    /// List the toolsets and the packages each installs (inside the container only).
    Toolsets,
    /// Print the exact podman command for a project (nothing is executed).
    Spec {
        /// Project name: lowercase letters, digits and `-`.
        #[arg(long)]
        project: String,
        /// Image pinned by digest: registry/name@sha256:<64 hex> (needed for `run` and `install`).
        #[arg(long, default_value = "")]
        image: String,
        /// `run` (default), `install` (toolset into a local image), `commit` (turn the install container into the local image) or `destroy`.
        #[arg(long, default_value = "run")]
        phase: String,
        /// Toolset for the install phase.
        #[arg(long, default_value = "basic")]
        toolset: String,
        /// One folder below ~/SecurityLabs to mount at /work (run phase only).
        #[arg(long)]
        workspace: Option<String>,
        /// `none` (default) or `outbound`; host networking does not exist.
        #[arg(long, default_value = "none")]
        network: String,
        #[arg(long, default_value_t = 2048)]
        memory_mib: u32,
        #[arg(long, default_value_t = 2)]
        cpus: u32,
        #[arg(long, default_value_t = 512)]
        pids: u32,
    },
}

#[derive(Subcommand)]
enum MemoryCmd {
    /// RAM, swap, zram devices and the AI budget.
    Status,
    /// Show or set the share of RAM local AI may use (10-90, default 60).
    Budget { percent: Option<u8> },
}

#[derive(Subcommand)]
enum WallpaperCmd {
    /// All presets (system and yours).
    List,
    /// One preset as JSON.
    Show { id: String },
    /// Save a preset of your own.
    Create {
        id: String,
        #[arg(long)]
        name: Option<String>,
        /// rain, starfield, aurora or grid
        #[arg(long, default_value = "rain")]
        effect: String,
        #[arg(long, default_value_t = 2)]
        density: u8,
        #[arg(long, default_value_t = 2)]
        speed: u8,
        #[arg(long)]
        no_mark: bool,
        /// #rrggbb
        #[arg(long, default_value = "")]
        accent: String,
        /// #rrggbb
        #[arg(long, default_value = "")]
        background: String,
        #[arg(long)]
        overwrite: bool,
    },
    /// Make a preset the wallpaper (low-VRAM mode caps density and speed).
    Apply {
        id: String,
        #[arg(long)]
        dry_run: bool,
    },
    /// Delete one of your presets.
    Delete { id: String },
    /// Copy a preset to a new file.
    Export {
        id: String,
        path: std::path::PathBuf,
    },
}

#[derive(Subcommand)]
enum CodeCmd {
    /// Known coding tools, licences and whether they are installed.
    List,
    /// Install a tool into your home directory (never system-wide).
    Install {
        id: String,
        /// Install even though the licence is not yet confirmed from the upstream repository.
        #[arg(long)]
        accept_unconfirmed_licence: bool,
    },
    /// Write the OpenCode config (local provider + hscl MCP) and the HCS agent notes.
    Setup {
        #[arg(long, default_value_t = 8080)]
        port: u16,
        #[arg(long, default_value = "local model")]
        model: String,
    },
    /// Start a tool against the local model server (default: opencode). Extra arguments go to the tool after `--`.
    Launch {
        id: Option<String>,
        #[arg(long, default_value_t = 8080)]
        port: u16,
        #[arg(last = true)]
        args: Vec<String>,
    },
}

#[derive(Subcommand)]
enum GraphicsCmd {
    /// What was detected and which profile it maps to.
    Detect,
    /// Apply the profile for this machine (skipped when unchanged or locked).
    Apply {
        #[arg(long)]
        dry_run: bool,
        #[arg(long)]
        force: bool,
    },
    /// Never auto-tune again (keeps your manual settings).
    Lock,
    /// Allow auto-tuning again.
    Unlock,
}

#[derive(Subcommand)]
enum AppearanceCmd {
    /// HCS themes (colour scheme + wallpaper).
    Theme {
        #[command(subcommand)]
        cmd: ThemeCmd,
    },
}

#[derive(Subcommand)]
enum ThemeCmd {
    /// List available themes.
    List,
    /// Show the design tokens of one theme.
    Show { name: String },
    /// Print the selected theme.
    Current,
    /// Apply a theme (backs up the previous selection first).
    Set {
        name: String,
        /// Print the plan without changing anything.
        #[arg(long)]
        dry_run: bool,
    },
    /// Restore the default theme (hcs-midnight).
    Restore {
        #[arg(long)]
        dry_run: bool,
    },
}

#[derive(Subcommand)]
enum SystemCmd {
    /// OS, kernel, CPU, memory (identifiers redacted).
    Info,
    /// Pending APT updates (read-only simulation; installs nothing).
    Updates {
        /// Required: only checking is implemented.
        #[arg(long, required = true)]
        check: bool,
    },
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
    /// Curated small open models (GGUF) that fit this machine.
    Model {
        #[command(subcommand)]
        cmd: ModelCmd,
    },
    /// Estimate RAM/VRAM for a GGUF file at a context size (reads only the metadata; an estimate, not a measurement).
    Fit {
        /// Path to a .gguf file.
        path: std::path::PathBuf,
        /// Context length in tokens.
        #[arg(long, default_value_t = 8192)]
        ctx: u64,
        /// KV cache type: f16, q8_0 or q4_0.
        #[arg(long, default_value = "f16")]
        kv: String,
        /// RAM budget in MiB (default: the AI budget from `hscl memory budget`).
        #[arg(long)]
        ram_mib: Option<u64>,
        /// GPU memory budget in MiB (dedicated VRAM; shared memory is not counted unless you pass it).
        #[arg(long)]
        vram_mib: Option<u64>,
    },
    /// Hardware-adapted run plan for a model (backend, offload, context, KV cache, threads).
    Profile {
        /// Catalog model id (default: the best recommendation for this machine).
        model: Option<String>,
        /// Force low-VRAM mode (partial offload, denser KV cache).
        #[arg(long)]
        low_vram: bool,
        /// Path to llama-server to read its capabilities (TurboQuant, MTP); default: `llama-server` on PATH.
        #[arg(long, value_name = "PATH")]
        backend: Option<std::path::PathBuf>,
    },
    /// Print the exact llama-server command for a local model (loopback only, API key as a file, measured defaults). Nothing is started.
    Serve {
        /// Model file (.gguf) inside the model storage directory (see `hscl ai model path`); not needed with --router-dir.
        model: Option<std::path::PathBuf>,
        /// TCP port on 127.0.0.1 (1024 or higher).
        #[arg(long, default_value_t = 8081)]
        port: u16,
        /// Context length in tokens (512 to 262144).
        #[arg(long, default_value_t = 4096)]
        ctx: u32,
        /// File with the API key, one line (default: ai-server.key in the hscl config directory). The key is never put on the command line.
        #[arg(long, value_name = "PATH")]
        api_key_file: Option<std::path::PathBuf>,
        /// Router mode: serve the models in this directory (must be inside the model storage), loaded on demand.
        #[arg(long, value_name = "DIR")]
        router_dir: Option<std::path::PathBuf>,
        /// Router mode only: models kept in memory at the same time (1 or 2).
        #[arg(long)]
        models_max: Option<u32>,
        /// Also expose the Prometheus /metrics endpoint.
        #[arg(long)]
        metrics: bool,
    },
}

#[derive(Subcommand)]
enum ModelCmd {
    /// All catalog models with fit information for this machine.
    List,
    /// Models that fit this machine, best first.
    Recommend {
        /// chat or coder
        #[arg(long)]
        role: Option<String>,
    },
    /// Details, licence and warning of one model.
    Info { id: String },
    /// Download a model (sha256 verified). Abliterated models need --accept-warning.
    Download {
        id: String,
        /// Target directory (default: ~/AI/Models or HSCL_MODELS_DIR).
        #[arg(long, value_name = "DIR")]
        dir: Option<std::path::PathBuf>,
        /// Also download the vision projector (image input) when the catalog has one.
        #[arg(long)]
        with_vision: bool,
        /// Confirm that you read the community-derivative warning of abliterated models.
        #[arg(long)]
        accept_warning: bool,
    },
    /// Re-check size and sha256 of a downloaded model.
    Verify {
        id: String,
        #[arg(long, value_name = "DIR")]
        dir: Option<std::path::PathBuf>,
    },
    /// Delete a downloaded model file (nothing else).
    Remove {
        id: String,
        #[arg(long, value_name = "DIR")]
        dir: Option<std::path::PathBuf>,
    },
    /// Show the model storage directory.
    Path,
}

fn labs_root() -> std::path::PathBuf {
    std::path::PathBuf::from(std::env::var_os("HOME").unwrap_or_default()).join("SecurityLabs")
}

fn on_path(bin: &str) -> bool {
    std::env::var_os("PATH")
        .is_some_and(|p| std::env::split_paths(&p).any(|d| d.join(bin).is_file()))
}

fn run_lab(j: bool, cmd: LabCmd) -> anyhow::Result<u8> {
    match cmd {
        LabCmd::Status => {
            let root = labs_root();
            let v = json!({
                "podman_installed": on_path("podman"),
                "labs_root": root.display().to_string(),
                "labs_root_exists": root.is_dir(),
                "toolsets": lab::TOOLSETS.iter().map(|(n, _)| *n).collect::<Vec<_>>(),
                "defaults": {"network": "none", "run_phase_capabilities": "none (cap-drop=ALL)", "image": "must be pinned by sha256 digest"},
                "note": "Kali tools run only inside rootless containers; the host never gets Kali repositories. Authorized testing only."
            });
            print_value(j, &v, || {
                format!(
                    "podman: {}
lab folder: {} ({})
toolsets: {}",
                    if on_path("podman") {
                        "installed"
                    } else {
                        "NOT installed"
                    },
                    root.display(),
                    if root.is_dir() {
                        "exists"
                    } else {
                        "missing - run `hscl lab setup`"
                    },
                    lab::TOOLSETS
                        .iter()
                        .map(|(n, _)| *n)
                        .collect::<Vec<_>>()
                        .join(", ")
                )
            });
        }
        LabCmd::Setup => {
            let root = labs_root();
            std::fs::create_dir_all(&root)?;
            #[cfg(unix)]
            {
                use std::os::unix::fs::PermissionsExt;
                std::fs::set_permissions(&root, std::fs::Permissions::from_mode(0o700))?;
            }
            print_value(
                j,
                &json!({"labs_root": root.display().to_string(), "created": true}),
                || format!("lab folder ready: {}", root.display()),
            );
        }
        LabCmd::Toolsets => {
            let v = json!(lab::TOOLSETS
                .iter()
                .map(|(n, p)| json!({"name": n, "packages": p}))
                .collect::<Vec<_>>());
            print_value(j, &v, || {
                lab::TOOLSETS
                    .iter()
                    .map(|(n, p)| format!("{n}: {}", p.join(" ")))
                    .collect::<Vec<_>>()
                    .join(
                        "
",
                    )
            });
        }
        LabCmd::Spec {
            project,
            image,
            phase,
            toolset,
            workspace,
            network,
            memory_mib,
            cpus,
            pids,
        } => {
            let limits = lab::Limits {
                memory_mib,
                cpus,
                pids,
            };
            let cmds: Vec<Vec<String>> = match phase.as_str() {
                "install" => {
                    if workspace.is_some() {
                        anyhow::bail!("the install phase mounts no host folder; --workspace is for the run phase");
                    }
                    vec![lab::install_argv(&project, &image, &toolset, limits)?]
                }
                "commit" => vec![lab::commit_argv(&project)?],
                "destroy" => lab::destroy_argv(&project)?,
                "run" => {
                    let root = labs_root();
                    let ws = workspace.as_deref().map(std::path::Path::new);
                    vec![lab::run_argv(&lab::RunSpec {
                        project: &project,
                        image: &image,
                        workspace: ws,
                        labs_root: &root,
                        network: lab::Network::parse(&network)?,
                        limits,
                        command: &[],
                    })?]
                }
                other => anyhow::bail!(
                    "phase must be `run`, `install`, `commit` or `destroy`, not `{other}`"
                ),
            };
            print_value(j, &json!({"commands": cmds, "executed": false}), || {
                cmds.iter()
                    .map(|c| lab::display(c))
                    .collect::<Vec<_>>()
                    .join(
                        "
",
                    )
            });
        }
    }
    Ok(exit::OK)
}

fn print_value(as_json: bool, v: &serde_json::Value, human: impl FnOnce() -> String) {
    if as_json {
        println!("{}", serde_json::to_string_pretty(v).unwrap_or_default());
    } else {
        println!("{}", human());
    }
}

fn completions_script(shell: clap_complete::Shell, prog: &str) -> String {
    let mut cmd = <Cli as clap::CommandFactory>::command();
    let mut buf = Vec::new();
    clap_complete::generate(shell, &mut cmd, prog, &mut buf);
    String::from_utf8_lossy(&buf).into_owned()
}

/// Roff man pages straight from the clap tree: `hscl.1`, `hscl1.1` (same binary, second name) and
/// one `hscl-<command>.1` per top-level command. Nothing is templated by hand, so a page cannot
/// describe a flag the binary does not have.
fn write_man_pages(out: &std::path::Path) -> anyhow::Result<Vec<std::path::PathBuf>> {
    if out.exists() && !out.is_dir() {
        anyhow::bail!("{} exists and is not a directory", out.display());
    }
    std::fs::create_dir_all(out)
        .map_err(|e| anyhow::anyhow!("cannot create {}: {e}", out.display()))?;
    let root = <Cli as clap::CommandFactory>::command();
    let mut written = Vec::new();
    let mut emit = |cmd: clap::Command, file: String| -> anyhow::Result<()> {
        let mut buf = Vec::new();
        clap_mangen::Man::new(cmd).render(&mut buf)?;
        let path = out.join(file);
        std::fs::write(&path, &buf)
            .map_err(|e| anyhow::anyhow!("cannot write {}: {e}", path.display()))?;
        written.push(path);
        Ok(())
    };
    for prog in ["hscl", "hscl1"] {
        emit(
            root.clone().name(prog.to_string()).bin_name(prog),
            format!("{prog}.1"),
        )?;
    }
    for sub in root.get_subcommands().filter(|c| c.get_name() != "help") {
        let name = format!("hscl-{}", sub.get_name());
        emit(
            sub.clone().name(name.clone()).bin_name(name.clone()),
            format!("{name}.1"),
        )?;
    }
    Ok(written)
}

fn run(cli: Cli) -> anyhow::Result<u8> {
    let j = cli.json;
    match cli.command.unwrap_or(Cmd::Overview) {
        Cmd::Version => {
            let v = json!({"product": PRODUCT, "expansion": EXPANSION, "version": env!("CARGO_PKG_VERSION")});
            print_value(j, &v, || format!("{PRODUCT} {}", env!("CARGO_PKG_VERSION")));
        }
        Cmd::Overview => {
            let prog = program_name(&std::env::args().next().unwrap_or_default());
            let v = overview_json(prog);
            print_value(j, &v, || overview_text(prog));
        }
        Cmd::About => {
            let v = json!({
                "product": PRODUCT, "expansion": EXPANSION, "version": env!("CARGO_PKG_VERSION"),
                "publisher": "HCSMEDIA", "credit": CREDIT,
                "notice": "HSCL1 is not Tails and not an official Kali release. KALI LINUX™ is a trademark of OffSec. HSCL1 is not affiliated with or endorsed by the Tails project."
            });
            print_value(j, &v, || {
                format!(
                    "{PRODUCT} {}\n{CREDIT}\nHSCL1 is not Tails and not an official Kali release.\nKALI LINUX™ is a trademark of OffSec. HSCL1 is not affiliated with or endorsed by the Tails project.",
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
        Cmd::System {
            cmd: SystemCmd::Updates { .. },
        } => {
            let u = updates::check()?;
            let v = serde_json::to_value(&u)?;
            print_value(j, &v, || updates::render(&u));
        }
        Cmd::Security {
            cmd: SecurityCmd::Status,
        } => {
            let sec = security::collect();
            let v = serde_json::to_value(&sec)?;
            print_value(j, &v, || security::render(&sec));
        }
        Cmd::Ai {
            cmd:
                AiCmd::Serve {
                    model,
                    port,
                    ctx,
                    api_key_file,
                    router_dir,
                    models_max,
                    metrics,
                },
        } => {
            let o = serve::ServeOpts {
                model: model.unwrap_or_default(),
                port,
                ctx,
                api_key_file: api_key_file
                    .unwrap_or_else(|| appearance::config_dir().join("ai-server.key")),
                router_dir,
                models_max,
                metrics,
            };
            let argv = serve::serve_argv(&o, &download::models_dir())?;
            let v = json!({"argv": argv, "executed": false, "note": "Printed only. Create the key file yourself (one random line, mode 0600) before starting the server."});
            print_value(j, &v, || serve::render(&argv));
        }
        Cmd::Ai {
            cmd: AiCmd::Model { cmd },
        } => return run_model(j, cmd),
        Cmd::Ai {
            cmd:
                AiCmd::Profile {
                    model,
                    low_vram,
                    backend,
                },
        } => return run_profile(j, model, low_vram, backend),
        Cmd::Ai {
            cmd:
                AiCmd::Fit {
                    path,
                    ctx,
                    kv,
                    ram_mib,
                    vram_mib,
                },
        } => {
            let g = gguf::parse_file(&path)?;
            let sum = gguf::summarize(&g)?;
            let ram = ram_mib.or_else(|| {
                Some(memory::status(&appearance::config_dir()).ai_budget_mib).filter(|m| *m > 0)
            });
            let f = gguf::fit(&sum, ctx, gguf::KvType::parse(&kv)?, ram, vram_mib);
            let v = json!({"model": sum, "fit": f, "estimate": true});
            print_value(j, &v, || gguf::render(&sum, &f));
        }
        Cmd::Ai { cmd: AiCmd::Detect } => {
            let d = ai::detect();
            let v = serde_json::to_value(&d)?;
            print_value(j, &v, || ai::render(&d));
        }
        Cmd::Report { output } => {
            let r = report::build()?;
            match output {
                Some(p) => {
                    report::write_new(&p, &r)?;
                    println!("report written to {}", p.display());
                }
                None => println!("{}", serde_json::to_string_pretty(&r)?),
            }
        }
        Cmd::Memory { cmd } => {
            let cfg = appearance::config_dir();
            match cmd {
                MemoryCmd::Status => {
                    let s = memory::status(&cfg);
                    print_value(j, &serde_json::to_value(&s)?, || {
                        format!("RAM {} MiB total, {} MiB available; swap {} MiB ({} free); zram: {}; AI budget {} % = {} MiB", s.total_mib, s.available_mib, s.swap_total_mib, s.swap_free_mib, if s.zram_devices.is_empty() { "none".to_string() } else { s.zram_devices.join(", ") }, s.ai_budget_percent, s.ai_budget_mib)
                    });
                }
                MemoryCmd::Budget { percent } => {
                    if let Some(p) = percent {
                        memory::write_percent(&cfg, p)?;
                    }
                    let p = memory::read_percent(&cfg);
                    print_value(j, &json!({"ai_budget_percent": p}), || {
                        format!("AI RAM budget: {p} %")
                    });
                }
            }
        }
        Cmd::LowVram { mode } => {
            let marker = appearance::config_dir().join("low-vram");
            match mode.as_str() {
                "on" => {
                    std::fs::create_dir_all(appearance::config_dir())?;
                    std::fs::write(
                        &marker, "1
",
                    )?;
                }
                "off" => {
                    let _ = std::fs::remove_file(&marker);
                }
                "status" => {}
                _ => anyhow::bail!("mode must be on, off or status"),
            }
            let on = marker.exists();
            print_value(j, &json!({"low_vram": on}), || {
                format!(
                    "low-VRAM mode is {}{}",
                    if on { "on" } else { "off" },
                    if mode == "status" {
                        ""
                    } else {
                        " - run `hscl graphics apply --force` to re-tune the desktop"
                    }
                )
            });
        }
        Cmd::Wallpaper { cmd } => return run_wallpaper(j, cmd),
        Cmd::Code { cmd } => return run_code(j, cmd),
        Cmd::Mcp { allow_write } => {
            mcp::serve(
                allow_write,
                std::io::stdin().lock(),
                std::io::stdout().lock(),
                &mcp::SelfExec,
            )?;
            return Ok(exit::OK);
        }
        Cmd::Completions { shell } => {
            let prog = program_name(&std::env::args().next().unwrap_or_default());
            print!("{}", completions_script(shell, prog));
            return Ok(exit::OK);
        }
        Cmd::Man { out } => {
            let files = write_man_pages(&out)?;
            let paths: Vec<String> = files.iter().map(|p| p.display().to_string()).collect();
            print_value(
                j,
                &json!({ "out": out.display().to_string(), "pages": paths }),
                || format!("{} man pages written to {}", paths.len(), out.display()),
            );
            return Ok(exit::OK);
        }
        Cmd::Graphics { cmd } => return run_graphics(j, cmd),
        Cmd::Lab { cmd } => return run_lab(j, cmd),
        Cmd::Hw { cmd: HwCmd::Detect } => {
            let r = hw::detect(std::path::Path::new("/"));
            print_value(j, &serde_json::to_value(&r)?, || hw::render(&r));
        }
        Cmd::Autotune { dry_run, force } => {
            return run_graphics(j, GraphicsCmd::Apply { dry_run, force });
        }
        Cmd::Appearance {
            cmd: AppearanceCmd::Theme { cmd },
        } => return run_theme(j, cmd),
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

fn run_wallpaper(j: bool, cmd: WallpaperCmd) -> anyhow::Result<u8> {
    let (sys, usr) = (wallpaper::system_dir(), wallpaper::user_dir());
    let all = wallpaper::load_all(&sys, &usr);
    let low_vram = std::fs::read_to_string(appearance::config_dir().join("low-vram")).is_ok();
    match cmd {
        WallpaperCmd::List => {
            print_value(j, &json!({"presets": all, "low_vram": low_vram}), || {
                all.iter()
                    .map(|p| {
                        format!(
                            "{:<16} {:<10} density {} speed {}  {}",
                            p.id, p.effect, p.density, p.speed, p.name
                        )
                    })
                    .collect::<Vec<_>>()
                    .join("\n")
            });
        }
        WallpaperCmd::Show { id } => {
            let p = wallpaper::find(&all, &id)?;
            print_value(j, &serde_json::to_value(p)?, || {
                serde_json::to_string_pretty(p).unwrap_or_default()
            });
        }
        WallpaperCmd::Create {
            id,
            name,
            effect,
            density,
            speed,
            no_mark,
            accent,
            background,
            overwrite,
        } => {
            let p = wallpaper::Preset {
                name: name.unwrap_or_else(|| id.clone()),
                id,
                effect,
                density,
                speed,
                show_mark: !no_mark,
                accent,
                background,
            };
            let path = wallpaper::save(&usr, &p, overwrite)?;
            print_value(j, &json!({"saved": path}), || {
                format!("saved {}", path.display())
            });
        }
        WallpaperCmd::Apply { id, dry_run } => {
            let p = wallpaper::find(&all, &id)?;
            if dry_run {
                let cmds = wallpaper::apply_commands(&wallpaper::capped(p, low_vram))?;
                print_value(
                    j,
                    &json!({"dry_run": true, "low_vram": low_vram, "commands": cmds}),
                    || {
                        cmds.iter()
                            .map(|c| c.join(" "))
                            .collect::<Vec<_>>()
                            .join("\n")
                    },
                );
            } else {
                wallpaper::apply(p, low_vram, &mut appearance::SystemRunner)?;
                print_value(j, &json!({"applied": id, "low_vram": low_vram}), || {
                    format!(
                        "applied {id}{}",
                        if low_vram { " (low-VRAM caps)" } else { "" }
                    )
                });
            }
        }
        WallpaperCmd::Delete { id } => {
            wallpaper::delete(&usr, &id)?;
            print_value(j, &json!({"deleted": id}), || format!("deleted {id}"));
        }
        WallpaperCmd::Export { id, path } => {
            wallpaper::export(wallpaper::find(&all, &id)?, &path)?;
            print_value(j, &json!({"exported": path}), || {
                format!("wrote {}", path.display())
            });
        }
    }
    Ok(exit::OK)
}

fn run_code(j: bool, cmd: CodeCmd) -> anyhow::Result<u8> {
    let tools = code::catalog()?;
    let home = std::path::PathBuf::from(std::env::var_os("HOME").unwrap_or_default());
    match cmd {
        CodeCmd::List => {
            let rows: Vec<_> = tools.iter().map(|t| json!({"id": t.id, "name": t.name, "licence": t.licence, "licence_confirmed": t.licence_confirmed, "installed": code::installed(t, &home), "install": t.install.kind, "homepage": t.homepage})).collect();
            print_value(j, &json!({"tools": rows}), || {
                tools
                    .iter()
                    .map(|t| {
                        format!(
                            "{} {:<10} {:<9} {}{}",
                            if code::installed(t, &home) { "*" } else { " " },
                            t.id,
                            t.install.kind,
                            t.licence,
                            if t.licence_confirmed {
                                ""
                            } else {
                                "  [licence not confirmed]"
                            }
                        )
                    })
                    .collect::<Vec<_>>()
                    .join("\n")
            });
        }
        CodeCmd::Install {
            id,
            accept_unconfirmed_licence,
        } => {
            let t = code::find(&tools, &id)?;
            code::run_install(
                t,
                &home,
                accept_unconfirmed_licence,
                &mut appearance::SystemRunner,
            )?;
            print_value(j, &json!({"installed": t.id}), || {
                format!("installed {} for your user", t.name)
            });
        }
        CodeCmd::Setup { port, model } => {
            let written = code::setup(&home, port, &model)?;
            print_value(j, &json!({"written": written}), || {
                written
                    .iter()
                    .map(|p| format!("wrote {}", p.display()))
                    .collect::<Vec<_>>()
                    .join("\n")
            });
        }
        CodeCmd::Launch { id, port, args } => {
            let t = match &id {
                Some(i) => code::find(&tools, i)?,
                None => tools
                    .iter()
                    .find(|t| t.default)
                    .ok_or_else(|| anyhow::anyhow!("no default tool"))?,
            };
            if !code::installed(t, &home) {
                anyhow::bail!(
                    "{} is not installed: run `hscl code install {}`",
                    t.name,
                    t.id
                );
            }
            eprintln!("{}", code::banner(t));
            let mut c = std::process::Command::new(&t.bin);
            c.args(&args);
            for (k, v) in code::tool_env(port) {
                c.env(k, v);
            }
            let local_bin = home.join(".local").join("bin");
            if let Some(p) = std::env::var_os("PATH") {
                let mut paths = vec![local_bin];
                paths.extend(std::env::split_paths(&p));
                c.env("PATH", std::env::join_paths(paths)?);
            }
            let st = c
                .status()
                .map_err(|e| anyhow::anyhow!("cannot start {}: {e}", t.bin))?;
            return Ok(st.code().unwrap_or(1) as u8);
        }
    }
    Ok(exit::OK)
}

fn detect_machine() -> graphics::Machine {
    let d = ai::detect();
    let gpu = d.gpus.first();
    let driver = gpu.and_then(|g| g.driver.clone());
    let discrete_hint = gpu.is_some_and(|g| {
        g.vendor == "NVIDIA" || (g.vendor == "AMD" && g.vram_mib.is_some_and(|v| v > 2048))
    });
    let cfg_low = std::fs::read_to_string(appearance::config_dir().join("low-vram")).is_ok();
    graphics::Machine {
        gpu: graphics::classify(driver.as_deref(), !d.render_nodes.is_empty(), discrete_hint),
        driver,
        ram_total_mib: d.mem_total_mib,
        cpu_threads: d.cpu_threads as u32,
        pixels: largest_display_pixels(),
        on_battery_device: std::fs::read_dir("/sys/class/power_supply")
            .map(|r| {
                r.flatten()
                    .any(|e| e.file_name().to_string_lossy().starts_with("BAT"))
            })
            .unwrap_or(false),
        low_vram_mode: cfg_low,
    }
}

fn largest_display_pixels() -> Option<u64> {
    let mut best = None;
    for e in std::fs::read_dir("/sys/class/drm").ok()?.flatten() {
        let p = e.path();
        if std::fs::read_to_string(p.join("status"))
            .map(|s| s.trim() == "connected")
            .unwrap_or(false)
        {
            if let Some(first) = std::fs::read_to_string(p.join("modes"))
                .ok()
                .and_then(|m| m.lines().next().map(str::to_string))
            {
                let mut it = first.split('x');
                if let (Some(w), Some(h)) = (
                    it.next().and_then(|v| v.parse::<u64>().ok()),
                    it.next().and_then(|v| v.trim().parse::<u64>().ok()),
                ) {
                    best = best.max(Some(w * h));
                }
            }
        }
    }
    best
}

fn run_graphics(j: bool, cmd: GraphicsCmd) -> anyhow::Result<u8> {
    let machine = detect_machine();
    let cfg = appearance::config_dir();
    match cmd {
        GraphicsCmd::Detect => {
            let p = graphics::profile(&machine);
            let v = json!({"machine": machine, "profile": p, "environment": graphics::environment_file(&p), "state": {"fingerprint": graphics::fingerprint(&machine)}});
            print_value(j, &v, || {
                format!("{:?} GPU, {} MiB RAM, {} threads -> profile {} (Qt Quick: {}, animations x{}, blur {}, rain density {})\n{}", machine.gpu, machine.ram_total_mib, machine.cpu_threads, p.level.name(), p.qt_quick, p.animation_factor, p.blur, p.rain_density, p.notes.join("\n"))
            });
        }
        GraphicsCmd::Apply { dry_run, force } => {
            let p = graphics::profile(&machine);
            if dry_run {
                let v = json!({"dry_run": true, "profile": p, "commands": graphics::commands(&p)});
                print_value(j, &v, || {
                    graphics::commands(&p)
                        .iter()
                        .map(|c| c.join(" "))
                        .collect::<Vec<_>>()
                        .join("\n")
                });
            } else {
                let ran = graphics::apply(&machine, &cfg, &mut appearance::SystemRunner, force)?;
                print_value(j, &json!({"applied": ran, "level": p.level.name()}), || {
                    if ran {
                        format!("applied profile {}", p.level.name())
                    } else {
                        "nothing to do (unchanged hardware or locked)".to_string()
                    }
                });
            }
        }
        GraphicsCmd::Lock | GraphicsCmd::Unlock => {
            let lock = matches!(cmd, GraphicsCmd::Lock);
            let mut st = graphics::load_state(&cfg);
            st.locked = lock;
            std::fs::create_dir_all(&cfg)?;
            std::fs::write(
                cfg.join("graphics.json"),
                serde_json::to_string_pretty(&st)?,
            )?;
            print_value(j, &json!({"locked": lock}), || {
                format!("auto-tuning {}", if lock { "locked" } else { "unlocked" })
            });
        }
    }
    Ok(exit::OK)
}

fn home_free_disk() -> Option<u64> {
    let home = std::env::var("HOME").unwrap_or_else(|_| "/".into());
    let out = std::process::Command::new("df")
        .args(["--output=avail", "-k", &home])
        .output()
        .ok()?;
    String::from_utf8_lossy(&out.stdout)
        .lines()
        .nth(1)?
        .trim()
        .parse::<u64>()
        .ok()
        .map(|k| k / 1024)
}

fn probe_backend(path: Option<std::path::PathBuf>) -> profile::BackendCaps {
    let exe = path.unwrap_or_else(|| "llama-server".into());
    match std::process::Command::new(exe).arg("--help").output() {
        Ok(o) => profile::probe_caps(&format!(
            "{}{}",
            String::from_utf8_lossy(&o.stdout),
            String::from_utf8_lossy(&o.stderr)
        )),
        Err(_) => profile::BackendCaps::default(),
    }
}

fn run_model(j: bool, cmd: ModelCmd) -> anyhow::Result<u8> {
    let models = catalog::load()?;
    let mut hw = ai::to_hw(&ai::detect(), home_free_disk());
    memory::cap_hw(&mut hw, memory::read_percent(&appearance::config_dir()));
    let tier = profile::tier_for(hw.ram_total_mib).name();
    match cmd {
        ModelCmd::List => {
            let rows: Vec<_> = models
                .iter()
                .map(|m| json!({"id": m.id, "tier": m.tier, "role": m.role, "variant": m.variant, "size_gb": (m.size_bytes as f64 / 1e7).round() / 100.0, "fits": profile::fits(&hw, m), "mtp": m.mtp, "vision": m.mmproj.is_some()}))
                .collect();
            let v = json!({"machine_tier": tier, "models": rows});
            print_value(j, &v, || {
                let mut s = format!("machine tier: {tier}\n");
                for m in &models {
                    let mark = if profile::fits(&hw, m) { "+" } else { "-" };
                    s += &format!(
                        "{mark} {:<34} {:<7} {:<6} {:>6.2} GB  {}\n",
                        m.id,
                        m.tier,
                        m.role,
                        m.size_bytes as f64 / 1e9,
                        m.variant
                    );
                }
                s + "(+ fits this machine, - does not)"
            });
        }
        ModelCmd::Recommend { role } => {
            let rec = profile::recommend(&hw, &models, role.as_deref());
            let items: Vec<_> = rec
                .iter()
                .map(|m| json!({"id": m.id, "variant": m.variant, "warning": m.warning}))
                .collect();
            let v = json!({"machine_tier": tier, "recommended": items, "note": "Nothing is downloaded. Abliterated variants are community derivatives - read the warning."});
            print_value(j, &v, || {
                if rec.is_empty() {
                    return "no catalog model fits the available memory".to_string();
                }
                let mut s = String::new();
                for m in &rec {
                    s += &format!(
                        "{}  ({}, {:.2} GB)\n",
                        m.id,
                        m.variant,
                        m.size_bytes as f64 / 1e9
                    );
                }
                if rec.iter().any(|m| m.variant == "abliterated") {
                    s += "\nWARNING: abliterated models are community derivatives with refusal behaviour removed; quality and safety are not guaranteed.";
                }
                s
            });
        }
        ModelCmd::Path => {
            let d = download::models_dir();
            print_value(j, &json!({"models_dir": d}), || d.display().to_string());
        }
        ModelCmd::Download {
            id,
            dir,
            with_vision,
            accept_warning,
        } => {
            let m = catalog::find(&models, &id)?;
            if !m.warning.is_empty() && !accept_warning {
                anyhow::bail!(
                    "{}\nRe-run with --accept-warning to confirm you read this.",
                    m.warning
                );
            }
            let dir = dir.unwrap_or_else(download::models_dir);
            let (p, mm) = download::download(
                m,
                &dir,
                with_vision,
                home_free_disk(),
                &download::CurlFetcher,
            )?;
            print_value(
                j,
                &json!({"model": p, "mmproj": mm, "verified": true}),
                || format!("verified: {}", p.display()),
            );
        }
        ModelCmd::Verify { id, dir } => {
            let m = catalog::find(&models, &id)?;
            let p = dir.unwrap_or_else(download::models_dir).join(&m.file);
            download::verify_file(&p, m.size_bytes, &m.sha256)?;
            print_value(j, &json!({"model": p, "verified": true}), || {
                format!("ok: {}", p.display())
            });
        }
        ModelCmd::Remove { id, dir } => {
            let m = catalog::find(&models, &id)?;
            let gone = download::remove(m, &dir.unwrap_or_else(download::models_dir))?;
            print_value(j, &json!({"removed": gone}), || {
                format!("removed {} file(s)", gone.len())
            });
        }
        ModelCmd::Info { id } => {
            let m = catalog::find(&models, &id)?;
            let v = serde_json::to_value(m)?;
            print_value(j, &v, || {
                format!(
                    "{}\nrepo: {}\nfile: {} ({:.2} GB, sha256 {})\nlicence: {}\nbase: {}\n{}",
                    m.id,
                    m.repo,
                    m.file,
                    m.size_bytes as f64 / 1e9,
                    m.sha256,
                    m.licence,
                    m.base_model,
                    m.warning
                )
            });
        }
    }
    Ok(exit::OK)
}

fn run_profile(
    j: bool,
    model: Option<String>,
    low_vram: bool,
    backend: Option<std::path::PathBuf>,
) -> anyhow::Result<u8> {
    let models = catalog::load()?;
    let mut hw = ai::to_hw(&ai::detect(), home_free_disk());
    memory::cap_hw(&mut hw, memory::read_percent(&appearance::config_dir()));
    let caps = probe_backend(backend);
    let m = match &model {
        Some(id) => catalog::find(&models, id)?,
        None => *profile::recommend(&hw, &models, None)
            .first()
            .ok_or_else(|| anyhow::anyhow!("no catalog model fits the available memory"))?,
    };
    let low_vram = low_vram || appearance::config_dir().join("low-vram").exists();
    let p = profile::plan(&hw, m, &caps, low_vram);
    let command = profile::server_args(&p, "<MODEL_PATH>", &caps, 8080, None);
    let v = json!({"hardware": hw, "backend_caps": caps, "plan": p, "llama_server_args": command, "speed": "not measured"});
    print_value(j, &v, || {
        format!(
            "{}: backend {}, offload {}, context {}, KV {}, threads {}{}{}\n{}",
            p.model_id,
            p.backend,
            p.ngl,
            p.ctx,
            p.kv_type,
            p.threads,
            if p.low_vram { ", LOW-VRAM" } else { "" },
            if p.feasible { "" } else { " (does not fit)" },
            p.notes.join("\n")
        )
    });
    Ok(if p.feasible { exit::OK } else { exit::FAILURE })
}

fn run_theme(j: bool, cmd: ThemeCmd) -> anyhow::Result<u8> {
    let catalog = appearance::load_catalog()?;
    let cfg = appearance::config_dir();
    let now = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map(|d| d.as_secs())
        .unwrap_or(0);
    match cmd {
        ThemeCmd::List => {
            let cur = appearance::current(&cfg);
            let v = json!({"current": cur, "themes": catalog});
            print_value(j, &v, || {
                catalog
                    .iter()
                    .map(|t| {
                        let mark = if cur.as_deref() == Some(&t.id) {
                            "*"
                        } else {
                            " "
                        };
                        format!("{mark} {:<14} {}", t.id, t.title)
                    })
                    .collect::<Vec<_>>()
                    .join(
                        "
",
                    )
            });
        }
        ThemeCmd::Current => {
            let cur = appearance::current(&cfg);
            let v = json!({"current": cur});
            print_value(j, &v, || {
                cur.clone().unwrap_or_else(|| "none selected".into())
            });
        }
        ThemeCmd::Show { name } => {
            appearance::find(&catalog, &name)?;
            let text = std::fs::read_to_string(appearance::tokens_path())?;
            let all: serde_json::Value = serde_json::from_str(&text)?;
            let tokens = all["themes"][&name].clone();
            print_value(j, &tokens, || {
                tokens
                    .as_object()
                    .map(|o| {
                        o.iter()
                            .map(|(k, v)| format!("{k:<16} {}", v.as_str().unwrap_or("")))
                            .collect::<Vec<_>>()
                            .join(
                                "
",
                            )
                    })
                    .unwrap_or_default()
            });
        }
        ThemeCmd::Set { name, dry_run } => {
            return set_theme(j, &catalog, &cfg, &name, dry_run, now)
        }
        ThemeCmd::Restore { dry_run } => {
            return set_theme(j, &catalog, &cfg, appearance::DEFAULT_THEME, dry_run, now)
        }
    }
    Ok(exit::OK)
}

fn set_theme(
    j: bool,
    catalog: &[appearance::Theme],
    cfg: &std::path::Path,
    name: &str,
    dry_run: bool,
    now: u64,
) -> anyhow::Result<u8> {
    let theme = appearance::find(catalog, name)?;
    let plan = appearance::plan(theme, cfg, now);
    if dry_run {
        let v = json!({"dry_run": true, "plan": plan});
        print_value(j, &v, || {
            let cmds: Vec<String> = plan
                .commands
                .iter()
                .map(|c| format!("  {}", c.join(" ")))
                .collect();
            format!(
                "would apply {} (backup: {})
{}",
                theme.id,
                plan.backup_file.display(),
                cmds.join(
                    "
"
                )
            )
        });
        return Ok(exit::OK);
    }
    appearance::apply(&plan, cfg, &mut appearance::SystemRunner, now)?;
    let v = json!({"applied": theme.id});
    print_value(j, &v, || format!("applied {}", theme.id));
    Ok(exit::OK)
}

/// `hscl1` and `hscl` are the same program: the name HSCL1 is also a command. Returns the name to show in usage text.
fn program_name(argv0: &str) -> &'static str {
    let base = argv0
        .rsplit(['/', '\\'])
        .next()
        .unwrap_or(argv0)
        .to_ascii_lowercase();
    let stem = base.strip_suffix(".exe").unwrap_or(&base);
    if stem == "hscl1" {
        "hscl1"
    } else {
        "hscl"
    }
}

const OVERVIEW_COMMANDS: &[(&str, &str)] = &[
    ("status", "system summary"),
    ("doctor", "health checks (exit code 3 when one fails)"),
    (
        "hw detect",
        "hardware inventory: GPU, CPU features, memory, firmware",
    ),
    (
        "ai fit MODEL.gguf",
        "will this model fit? RAM/VRAM and context estimate",
    ),
    (
        "ai profile",
        "run plan for the local AI model on this machine",
    ),
    ("graphics detect", "how the desktop is tuned for this GPU"),
    (
        "lab status",
        "Security Lab (rootless containers, authorized testing only)",
    ),
    ("memory status", "RAM, swap, zram and the AI memory budget"),
    ("--help", "every command"),
];

fn overview_json(prog: &str) -> serde_json::Value {
    json!({
        "product": PRODUCT, "expansion": EXPANSION, "version": env!("CARGO_PKG_VERSION"), "credit": CREDIT, "program": prog,
        "stage": "pre-alpha: tested in virtual machines only, see docs/KNOWN_LIMITATIONS.md",
        "commands": OVERVIEW_COMMANDS.iter().map(|(c, d)| json!({"command": format!("{prog} {c}"), "what": d})).collect::<Vec<_>>()
    })
}

fn overview_text(prog: &str) -> String {
    let mut s = format!(
        "{PRODUCT} - {EXPANSION}
{CREDIT} | version {} | pre-alpha, tested in virtual machines only

Start here:
",
        env!("CARGO_PKG_VERSION")
    );
    for (c, d) in OVERVIEW_COMMANDS {
        s.push_str(&format!(
            "  {prog} {c:<20} {d}
"
        ));
    }
    s.push_str(
        "
`hscl` and `hscl1` are the same program. HSCL1 is not Tails and not an official Kali release.\n\nKALI LINUX™ is a trademark of OffSec. HSCL1 is not affiliated with or endorsed by the Tails project.",
    );
    s
}

fn main() -> ExitCode {
    tracing_subscriber::fmt()
        .with_env_filter(tracing_subscriber::EnvFilter::from_default_env())
        .with_writer(std::io::stderr)
        .init();
    let args: Vec<std::ffi::OsString> = std::env::args_os().collect();
    let prog = program_name(
        &args
            .first()
            .map(|a| a.to_string_lossy().into_owned())
            .unwrap_or_default(),
    );
    let matches = <Cli as clap::CommandFactory>::command()
        .name(prog)
        .bin_name(prog)
        .get_matches_from(args);
    let cli = match <Cli as clap::FromArgMatches>::from_arg_matches(&matches) {
        Ok(c) => c,
        Err(e) => e.exit(),
    };
    match run(cli) {
        Ok(code) => ExitCode::from(code),
        Err(e) => {
            eprintln!("hscl: error: {e:#}");
            ExitCode::from(exit::FAILURE)
        }
    }
}

#[cfg(test)]
mod brand_tests {
    use super::*;

    #[test]
    fn the_name_hscl1_is_also_a_program() {
        for (argv0, want) in [
            ("hscl1", "hscl1"),
            ("/usr/bin/hscl1", "hscl1"),
            (r"C:\tools\hscl1.exe", "hscl1"),
            ("HSCL1.EXE", "hscl1"),
            ("hscl", "hscl"),
            ("/usr/bin/hscl", "hscl"),
            ("hscl1-old", "hscl"),
            ("", "hscl"),
            ("xhscl1", "hscl"),
        ] {
            assert_eq!(program_name(argv0), want, "{argv0}");
        }
    }

    #[test]
    fn overview_names_the_product_in_full_and_uses_the_program_name() {
        let t = overview_text("hscl1");
        assert!(
            t.starts_with("HSCL1 - Hypercharged Supreme Computing Layout 1"),
            "{t}"
        );
        assert!(
            t.contains("hscl1 hw detect")
                && t.contains("hscl1 ai fit MODEL.gguf")
                && t.contains("pre-alpha")
        );
        let v = overview_json("hscl");
        assert_eq!(v["expansion"], "Hypercharged Supreme Computing Layout 1");
        assert!(v["commands"]
            .as_array()
            .unwrap()
            .iter()
            .all(|c| c["command"].as_str().unwrap().starts_with("hscl ")));
    }

    #[test]
    fn expansion_is_the_exact_owner_given_text() {
        assert_eq!(EXPANSION, "Hypercharged Supreme Computing Layout 1");
        assert_eq!(PRODUCT, "HSCL1");
    }
}

#[cfg(test)]
mod doc_drift_tests {
    use super::*;

    fn leaves(cmd: &clap::Command, prefix: &str, out: &mut Vec<String>) {
        let subs: Vec<&clap::Command> = cmd
            .get_subcommands()
            .filter(|c| c.get_name() != "help")
            .collect();
        if subs.is_empty() {
            out.push(prefix.to_string());
        }
        for c in subs {
            leaves(c, &format!("{prefix} {}", c.get_name()), out);
        }
    }

    /// G12: every leaf command of the clap tree must appear in docs/CLI.md.
    #[test]
    fn cli_doc_lists_every_command() {
        let doc =
            std::fs::read_to_string(concat!(env!("CARGO_MANIFEST_DIR"), "/../../docs/CLI.md"))
                .expect("docs/CLI.md");
        let mut all = Vec::new();
        let root = <Cli as clap::CommandFactory>::command();
        for c in root.get_subcommands().filter(|c| c.get_name() != "help") {
            leaves(c, &format!("hscl {}", c.get_name()), &mut all);
        }
        assert!(all.len() > 10, "command tree not walked: {all:?}");
        let missing: Vec<&String> = all.iter().filter(|p| !doc.contains(p.as_str())).collect();
        assert!(missing.is_empty(), "docs/CLI.md misses: {missing:#?}");
    }
}

#[cfg(test)]
mod completion_tests {
    use super::*;

    #[test]
    fn completion_scripts_cover_every_top_level_command_for_both_program_names() {
        let root = <Cli as clap::CommandFactory>::command();
        for prog in ["hscl", "hscl1"] {
            for shell in [
                clap_complete::Shell::Bash,
                clap_complete::Shell::Zsh,
                clap_complete::Shell::Fish,
            ] {
                let s = completions_script(shell, prog);
                for c in root.get_subcommands().filter(|c| c.get_name() != "help") {
                    assert!(
                        s.contains(c.get_name()),
                        "{shell:?}/{prog} misses {}",
                        c.get_name()
                    );
                }
                assert!(s.contains(prog));
            }
        }
    }
}

#[cfg(test)]
mod doc_command_tests {
    //! G24: every `hscl ...` invocation shown in a fenced code block of the user-facing docs must
    //! resolve in the real clap tree. Drift the other way (`docs/CLI.md` missing a command) is
    //! covered by `cli_doc_lists_every_command`.
    //!
    //! Excluded on purpose: `docs/BUILD_LOG.md` (an append-only engineering log quoting commands
    //! from past states), `docs/research/` and `docs/superpowers/` (plans may name commands that a
    //! later sprint implements).
    use clap::CommandFactory;
    use std::path::{Path, PathBuf};

    fn repo_root() -> PathBuf {
        Path::new(env!("CARGO_MANIFEST_DIR")).join("../..")
    }

    fn collect_md(dir: &Path, out: &mut Vec<PathBuf>) {
        let Ok(entries) = std::fs::read_dir(dir) else {
            return;
        };
        for entry in entries.flatten() {
            let p = entry.path();
            if p.is_dir() {
                collect_md(&p, out);
            } else if p.extension().is_some_and(|e| e == "md") {
                out.push(p);
            }
        }
    }

    fn markdown_files(root: &Path) -> Vec<PathBuf> {
        let mut out = Vec::new();
        for name in ["README.md", "CONTRIBUTING.md", "SECURITY.md"] {
            let p = root.join(name);
            if p.is_file() {
                out.push(p);
            }
        }
        if let Ok(entries) = std::fs::read_dir(root.join("docs")) {
            for entry in entries.flatten() {
                let p = entry.path();
                if p.extension().is_some_and(|e| e == "md")
                    && p.file_name().is_some_and(|n| n != "BUILD_LOG.md")
                {
                    out.push(p);
                }
            }
        }
        collect_md(&root.join("handbook"), &mut out);
        out.sort();
        out
    }

    /// Commands inside fenced code blocks, as the token list after the program name.
    fn commands_in(text: &str) -> Vec<String> {
        let mut out = Vec::new();
        let mut in_block = false;
        for line in text.lines() {
            let trimmed = line.trim();
            if trimmed.starts_with("```") {
                in_block = !in_block;
                continue;
            }
            if !in_block {
                continue;
            }
            if trimmed.starts_with('#') {
                continue; // shell comment, not an invocation
            }
            let mut s = trimmed;
            for prompt in ["$ ", "> "] {
                if let Some(rest) = s.strip_prefix(prompt) {
                    s = rest;
                    break;
                }
            }
            let words: Vec<&str> = s
                .split_whitespace()
                .take_while(|w| !w.contains('|') && !w.contains("&&") && !w.starts_with(';'))
                .collect();
            let mut words = words.as_slice();
            if words.first() == Some(&"sudo") {
                words = &words[1..];
            }
            if matches!(words.first(), Some(&"hscl") | Some(&"hscl1")) {
                out.push(words[1..].join(" "));
            }
        }
        out
    }

    /// Commands written as inline code spans (`sudo hscl ...`), which is how prose recommends them.
    fn inline_commands(text: &str) -> Vec<String> {
        let mut out = Vec::new();
        let mut rest = text;
        while let Some(start) = rest.find('`') {
            rest = &rest[start + 1..];
            let Some(end) = rest.find('`') else { break };
            let span = &rest[..end];
            rest = &rest[end + 1..];
            let mut words: Vec<&str> = span
                .split_whitespace()
                .take_while(|w| !w.contains('|') && !w.contains("&&") && !w.starts_with(';'))
                .collect();
            if words.first() == Some(&"sudo") {
                words.remove(0);
            }
            if matches!(words.first(), Some(&"hscl") | Some(&"hscl1")) && words.len() > 1 {
                out.push(words[1..].join(" "));
            }
        }
        out
    }

    /// Longest subcommand chain the tokens start with; a bare word under a node that has no
    /// positionals is reported instead of silently accepted.
    fn resolve(root: &clap::Command, command: &str) -> Result<String, String> {
        let mut cur = root;
        let mut path = vec!["hscl".to_string()];
        for token in command.split_whitespace() {
            if token.starts_with('-') || token.starts_with('#') {
                break;
            }
            match cur.get_subcommands().find(|c| c.get_name() == token) {
                Some(sub) => {
                    path.push(token.to_string());
                    cur = sub;
                }
                None => {
                    let has_subs = cur.get_subcommands().any(|c| c.get_name() != "help");
                    let has_positionals = cur.get_arguments().any(|a| a.get_index().is_some());
                    if has_subs && !has_positionals {
                        return Err(format!(
                            "'{}' is not a subcommand of `{}`",
                            token,
                            path.join(" ")
                        ));
                    }
                    break;
                }
            }
        }
        Ok(path.join(" "))
    }

    #[test]
    fn documented_hscl_commands_resolve_in_the_cli() {
        let root = repo_root();
        let files = markdown_files(&root);
        assert!(
            files.len() > 10,
            "only {} markdown files scanned - the gate would pass without looking",
            files.len()
        );
        let cli = <crate::Cli as CommandFactory>::command();
        let mut checked = 0usize;
        let mut problems = Vec::new();
        for file in &files {
            let text = std::fs::read_to_string(file).expect("read markdown");
            let mut all = commands_in(&text);
            all.extend(inline_commands(&text));
            for command in all {
                if command.trim().is_empty() {
                    continue;
                }
                checked += 1;
                if let Err(why) = resolve(&cli, &command) {
                    let rel = file.strip_prefix(&root).unwrap_or(file);
                    problems.push(format!("{}: hscl {} ({})", rel.display(), command, why));
                }
            }
        }
        assert!(
            checked > 25,
            "only {checked} documented commands found - the scan is probably broken"
        );
        assert!(
            problems.is_empty(),
            "documented commands that do not exist:\n{}",
            problems.join("\n")
        );
    }

    #[test]
    fn the_command_scanner_reads_fenced_blocks_only_and_handles_prompts() {
        let text = "text `hscl nope` inline\n```bash\n$ hscl status --json | jq .\nsudo hscl1 ainet detect\n```\n```\n# hscl comment only\n```\n";
        let got = commands_in(text);
        assert_eq!(
            got,
            vec!["status --json".to_string(), "ainet detect".to_string()]
        );
    }
}

#[cfg(test)]
mod man_tests {
    //! `hscl man --out DIR` (plan task 2b): the packaged man pages come from the same clap tree as
    //! the binary, so a new command cannot ship without documentation (docs/CLI.md is the other half).
    use super::*;

    fn names(dir: &std::path::Path) -> Vec<String> {
        std::fs::read_dir(dir)
            .unwrap()
            .flatten()
            .map(|e| e.file_name().to_string_lossy().into_owned())
            .collect()
    }

    #[test]
    fn writes_a_page_for_the_program_and_every_top_level_command() {
        let dir = tempfile::tempdir().unwrap();
        let files = write_man_pages(dir.path()).unwrap();
        let got = names(dir.path());
        for want in ["hscl.1", "hscl1.1"] {
            assert!(got.iter().any(|n| n == want), "{want} missing: {got:?}");
        }
        let root = <Cli as clap::CommandFactory>::command();
        let mut expected = 2;
        for c in root.get_subcommands().filter(|c| c.get_name() != "help") {
            let want = format!("hscl-{}.1", c.get_name());
            assert!(got.iter().any(|n| n == &want), "{want} missing: {got:?}");
            expected += 1;
        }
        assert_eq!(files.len(), expected);
        for f in &files {
            let text = std::fs::read_to_string(f).unwrap();
            // roff pages may open with a quoting preamble (dot-ie, dot-el), so look for the title
            // line and the mandatory NAME section rather than the first byte.
            assert!(
                text.lines().any(|l| l.starts_with(".TH ")),
                "{f:?} has no .TH title line"
            );
            assert!(text.contains(".SH NAME"), "{f:?} has no NAME section");
            assert!(text.len() > 100, "{f:?} is suspiciously short");
            assert!(
                !text.contains("PLACEHOLDER"),
                "{f:?} contains a placeholder"
            );
        }
        let root_page = std::fs::read_to_string(dir.path().join("hscl.1")).unwrap();
        assert!(
            root_page.contains(PRODUCT),
            "the root page should name the product"
        );
        assert!(
            root_page.contains(&format!("hscl {}", env!("CARGO_PKG_VERSION")))
                || root_page.contains(env!("CARGO_PKG_VERSION"))
        );
    }

    #[test]
    fn a_path_that_is_a_file_is_refused_without_touching_it() {
        let dir = tempfile::tempdir().unwrap();
        let file = dir.path().join("not-a-directory");
        std::fs::write(&file, b"keep me").unwrap();
        assert!(write_man_pages(&file).is_err());
        assert_eq!(std::fs::read(&file).unwrap(), b"keep me");
    }

    #[test]
    fn the_pages_are_deterministic() {
        let a = tempfile::tempdir().unwrap();
        let b = tempfile::tempdir().unwrap();
        write_man_pages(a.path()).unwrap();
        write_man_pages(b.path()).unwrap();
        for name in ["hscl.1", "hscl-ai.1"] {
            assert_eq!(
                std::fs::read(a.path().join(name)).unwrap(),
                std::fs::read(b.path().join(name)).unwrap(),
                "{name} differs between two runs"
            );
        }
    }
}
