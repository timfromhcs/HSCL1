//! `hcsuda` — capability probe, planner inspection, differential self-test and
//! benchmark. Every command has a `--json` form because a number without context
//! is not evidence.

mod gpu;

use std::path::PathBuf;
use std::time::Instant;

use anyhow::{Context, Result};
use clap::{Parser, Subcommand};
use hcsuda_core::planner::{self, Op, PathKind, Shape};
use hcsuda_core::report::{BenchRow, BenchSuite};
use hcsuda_core::{reference, DType};
use hcsuda_vk::DeviceCaps;

#[derive(Parser)]
#[command(
    name = "hcsuda",
    version,
    about = "HCSUDA — Vulkan-first compute runtime. Made with love by hcsmedia",
    long_about = None
)]
struct Cli {
    #[command(subcommand)]
    command: Command,
}

#[derive(Subcommand)]
enum Command {
    /// Report the device capability record (dtypes, heaps, features).
    Caps {
        #[arg(long)]
        json: bool,
        /// Physical device index; omit to pick the best one.
        #[arg(long)]
        device: Option<usize>,
        /// Write the JSON record to this path (implies nothing about stdout).
        #[arg(long)]
        out: Option<PathBuf>,
    },
    /// Ask the conservative planner what it would run for an op/dtype/shape.
    Plan {
        /// Op name, e.g. gemm, gemv, saxpy.
        op: String,
        /// Dtype name, e.g. f32, f16, i8, fp8e4m3.
        dtype: String,
        #[arg(long, default_value_t = 64)]
        m: usize,
        #[arg(long, default_value_t = 64)]
        n: usize,
        #[arg(long, default_value_t = 64)]
        k: usize,
        #[arg(long)]
        json: bool,
        #[arg(long)]
        device: Option<usize>,
    },
    /// Run GPU kernels against the CPU oracle and report the differential error.
    Selftest {
        #[arg(long)]
        json: bool,
        #[arg(long)]
        device: Option<usize>,
        /// Write the JSON result to this path.
        #[arg(long)]
        out: Option<PathBuf>,
    },
    /// Measure the same kernels on GPU and CPU and emit a benchmark suite.
    Bench {
        /// Comma-separated op list; supported: saxpy,triad,gemv.
        #[arg(long, default_value = "saxpy,triad,gemv")]
        suite: String,
        #[arg(long, default_value_t = 5)]
        runs: u32,
        /// Dispatches per sample; each sample is their mean. A sustained burst
        /// is required on an integrated GPU: short bursts measure the clock
        /// ramp, not the kernel (measured on the 680M: spread 0.87 at 5 reps,
        /// 0.08 at 50).
        #[arg(long, default_value_t = 50)]
        reps: u32,
        #[arg(long)]
        json: bool,
        #[arg(long)]
        device: Option<usize>,
        /// Write the JSON suite to this path.
        #[arg(long)]
        out: Option<PathBuf>,
    },
}

fn main() {
    if let Err(err) = run() {
        eprintln!("hcsuda: {err:#}");
        std::process::exit(1);
    }
}

fn run() -> Result<()> {
    let cli = Cli::parse();
    match cli.command {
        Command::Caps { json, device, out } => cmd_caps(json, device, out),
        Command::Plan {
            op,
            dtype,
            m,
            n,
            k,
            json,
            device,
        } => cmd_plan(&op, &dtype, Shape::new(m, n, k), json, device),
        Command::Selftest { json, device, out } => cmd_selftest(json, device, out),
        Command::Bench {
            suite,
            runs,
            reps,
            json,
            device,
            out,
        } => cmd_bench(&suite, runs, reps, json, device, out),
    }
}

/// Write a JSON document, creating the parent directory when needed.
fn write_json<T: serde::Serialize>(path: &PathBuf, value: &T) -> Result<()> {
    if let Some(parent) = path.parent() {
        if !parent.as_os_str().is_empty() {
            std::fs::create_dir_all(parent).ok();
        }
    }
    std::fs::write(path, serde_json::to_string_pretty(value)?)
        .with_context(|| format!("writing {}", path.display()))
}

fn parse_dtype(name: &str) -> Result<DType> {
    DType::ALL
        .iter()
        .copied()
        .find(|d| d.name().eq_ignore_ascii_case(name))
        .with_context(|| {
            let known: Vec<&str> = DType::ALL.iter().map(|d| d.name()).collect();
            format!("unknown dtype '{name}' (known: {})", known.join(", "))
        })
}

fn parse_op(name: &str) -> Result<Op> {
    Op::ALL
        .iter()
        .copied()
        .find(|o| o.name().eq_ignore_ascii_case(name))
        .with_context(|| {
            let known: Vec<&str> = Op::ALL.iter().map(|o| o.name()).collect();
            format!("unknown op '{name}' (known: {})", known.join(", "))
        })
}

/// Take `runs` samples, each the mean of `reps` dispatches.
fn sample<F>(runs: u32, reps: u32, mut f: F) -> Result<Vec<hcsuda_vk::Timed>>
where
    F: FnMut() -> Result<hcsuda_vk::Timed>,
{
    let mut out = Vec::with_capacity(runs as usize);
    for _ in 0..runs {
        let mut wall = 0.0f64;
        let mut gpu_sum = 0.0f64;
        let mut gpu_n = 0u32;
        for _ in 0..reps {
            let t = f()?;
            wall += t.wall_ms;
            if let Some(g) = t.gpu_ms {
                gpu_sum += g;
                gpu_n += 1;
            }
        }
        out.push(hcsuda_vk::Timed {
            wall_ms: wall / reps as f64,
            gpu_ms: if gpu_n > 0 {
                Some(gpu_sum / gpu_n as f64)
            } else {
                None
            },
        });
    }
    Ok(out)
}

/// Wall-clock samples plus GPU-side median and spread, when timestamps exist.
fn split_timings(timings: Vec<hcsuda_vk::Timed>) -> (Vec<f64>, Option<(f64, f64)>) {
    let wall = timings.iter().map(|t| t.wall_ms).collect();
    let gpu: Vec<f64> = timings.iter().filter_map(|t| t.gpu_ms).collect();
    let median = BenchRow::median_of(gpu.clone());
    let spread = BenchRow::spread_of(gpu);
    match (median, spread) {
        (Some(m), Some(s)) => (wall, Some((m, s))),
        _ => (wall, None),
    }
}

fn cmd_caps(json: bool, device: Option<usize>, out: Option<PathBuf>) -> Result<()> {
    let caps = hcsuda_vk::probe(device).context("probing Vulkan devices")?;
    if let Some(path) = &out {
        write_json(path, &caps)?;
    }
    if json {
        println!("{}", serde_json::to_string_pretty(&caps)?);
        return Ok(());
    }
    print_caps_human(&caps);
    Ok(())
}

fn print_caps_human(caps: &DeviceCaps) {
    println!("device      {}", caps.name);
    println!(
        "type        {}  vendor {:#06x}  device {:#06x}",
        caps.device_type, caps.vendor_id, caps.device_id
    );
    println!("api         Vulkan {}", caps.api_version);
    println!("driver      {} {}", caps.driver_name, caps.driver_info);
    println!(
        "limits      {} invocations/workgroup, {} B shared, storage range {} B",
        caps.max_workgroup_invocations, caps.max_shared_memory, caps.max_storage_range
    );
    println!("timestamps  {} ns period", caps.timestamp_period_ns);
    println!(
        "memory      usable {:.2} GiB (budget, before headroom)",
        caps.usable_device_bytes(0) as f64 / (1u64 << 30) as f64
    );
    for heap in &caps.heaps {
        println!(
            "  heap{:<2} {:>8.2} GiB{}{}",
            heap.index,
            heap.size_bytes as f64 / (1u64 << 30) as f64,
            if heap.device_local {
                " device-local"
            } else {
                ""
            },
            if heap.host_visible {
                " host-visible"
            } else {
                ""
            }
        );
    }
    println!("dtypes      storage / compute");
    for (name, path) in &caps.dtypes {
        println!("  {:<8} {:?} / {:?}", name, path.storage, path.compute);
    }
    let f = &caps.features;
    let mut on = Vec::new();
    for (flag, value) in [
        ("f16", f.shader_f16),
        ("i8", f.shader_i8),
        ("f64", f.shader_f64),
        ("bda", f.buffer_device_address),
        ("int8-dot", f.int8_dot),
        ("int4-dot", f.int4_dot),
        ("coopmat", f.cooperative_matrix),
        ("fp8-ext", f.float8_ext),
        ("timestamps", f.timestamps),
    ] {
        if value {
            on.push(flag);
        }
    }
    println!("features    {}", on.join(", "));
    if caps.verified_paths.is_empty() {
        println!("verified    none yet (run `hcsuda selftest`)");
    } else {
        let mut paths: Vec<&String> = caps.verified_paths.iter().collect();
        paths.sort();
        println!(
            "verified    {}",
            paths
                .iter()
                .map(|s| s.as_str())
                .collect::<Vec<_>>()
                .join(", ")
        );
    }
}

fn cmd_plan(op: &str, dtype: &str, shape: Shape, json: bool, device: Option<usize>) -> Result<()> {
    let op = parse_op(op)?;
    let dtype = parse_dtype(dtype)?;
    let caps = hcsuda_vk::probe(device).context("probing Vulkan devices")?;
    let plan = planner::plan(op, dtype, shape, &caps);
    if json {
        println!("{}", serde_json::to_string_pretty(&plan)?);
        return Ok(());
    }
    println!("op      {}", plan.op.name());
    println!("dtype   {}", plan.dtype.name());
    println!("path    {}", plan.kind.name());
    println!(
        "tile    {}x{}x{} ({} B shared)",
        plan.tile.x, plan.tile.y, plan.tile.k, plan.tile.shared_bytes
    );
    println!("reason  {}", plan.reason);
    if plan.kind == PathKind::Reference {
        println!("\nThe reference kernel is correct but single-threaded. Run `hcsuda selftest`");
        println!("to verify the GPU path for this op, then `hcsuda bench` to promote it.");
    }
    Ok(())
}

struct Case {
    op: &'static str,
    path: &'static str,
    max_error: f64,
    tolerance: f64,
    ok: bool,
    deterministic: bool,
    gpu_ms: Option<f64>,
}

fn cmd_selftest(json: bool, device: Option<usize>, out: Option<PathBuf>) -> Result<()> {
    let mut runner = gpu::Runner::new(device)?;
    let mut cases: Vec<Case> = Vec::new();

    // --- saxpy: y = alpha*x + y
    let n = 4096usize;
    let x: Vec<f32> = (0..n).map(|i| (i as f32 * 0.5).sin()).collect();
    let y0: Vec<f32> = (0..n).map(|i| (i as f32 * 0.25).cos()).collect();
    let alpha = 2.5f32;
    let gx = runner.upload(&x)?;
    let mut want = y0.clone();
    reference::saxpy(alpha, &x, &mut want);
    // saxpy accumulates into `y`, so every run needs a fresh copy of the input;
    // reusing the buffer would test three chained applications against one.
    let mut got_runs = Vec::new();
    let mut timed = None;
    for _ in 0..3 {
        let gy = runner.upload(&y0)?;
        timed = Some(runner.saxpy(alpha, &gx, &gy)?);
        got_runs.push(runner.download(&gy)?);
    }
    let tol = gpu::f32_tolerance(n);
    let got = got_runs.last().expect("three runs").clone();
    let max_error = tol.max_error(&want, &got).unwrap_or(f64::INFINITY);
    let deterministic = got_runs.windows(2).all(|w| w[0] == w[1]);
    cases.push(Case {
        op: "saxpy",
        path: "vulkan_scalar",
        max_error,
        tolerance: tol.abs + tol.rel * 1.0,
        ok: max_error <= tol.abs + tol.rel,
        deterministic,
        gpu_ms: timed.and_then(|t| t.gpu_ms),
    });

    // --- triad: a = b + alpha*c
    let b: Vec<f32> = (0..n).map(|i| (i as f32 * 0.125).sin()).collect();
    let c: Vec<f32> = (0..n).map(|i| (i as f32 * 0.375).cos()).collect();
    let ga = runner.upload(&vec![0.0f32; n])?;
    let gb = runner.upload(&b)?;
    let gc = runner.upload(&c)?;
    let mut want = vec![0.0f32; n];
    reference::triad(&mut want, &b, &c, alpha);
    let mut got_runs = Vec::new();
    let mut timed = None;
    for _ in 0..3 {
        timed = Some(runner.triad(alpha, &ga, &gb, &gc)?);
        got_runs.push(runner.download(&ga)?);
    }
    let got = got_runs.last().expect("three runs").clone();
    let max_error = tol.max_error(&want, &got).unwrap_or(f64::INFINITY);
    let deterministic = got_runs.windows(2).all(|w| w[0] == w[1]);
    cases.push(Case {
        op: "triad",
        path: "vulkan_scalar",
        max_error,
        tolerance: tol.abs + tol.rel,
        ok: max_error <= tol.abs + tol.rel,
        deterministic,
        gpu_ms: timed.and_then(|t| t.gpu_ms),
    });

    // --- gemv: y = A*x
    let rows = 64usize;
    let cols = 512usize;
    let a: Vec<f32> = (0..rows * cols)
        .map(|i| ((i % 97) as f32 - 48.0) * 0.01)
        .collect();
    let xv: Vec<f32> = (0..cols).map(|i| ((i % 31) as f32 - 15.0) * 0.05).collect();
    let want = reference::gemv(&a, &xv, rows, cols);
    let ga = runner.upload(&a)?;
    let gx = runner.upload(&xv)?;
    let gy = runner.upload(&vec![0.0f32; rows])?;
    let mut got_runs = Vec::new();
    let mut timed = None;
    for _ in 0..3 {
        timed = Some(runner.gemv(&ga, &gx, &gy, rows, cols)?);
        got_runs.push(runner.download(&gy)?);
    }
    let got = got_runs.last().expect("three runs").clone();
    let gtol = gpu::f32_tolerance(cols);
    let max_error = gtol.max_error(&want, &got).unwrap_or(f64::INFINITY);
    let deterministic = got_runs.windows(2).all(|w| w[0] == w[1]);
    cases.push(Case {
        op: "gemv",
        path: "vulkan_scalar",
        max_error,
        tolerance: gtol.abs + gtol.rel,
        ok: max_error <= gtol.abs + gtol.rel,
        deterministic,
        gpu_ms: timed.and_then(|t| t.gpu_ms),
    });

    let all_ok = cases.iter().all(|c| c.ok && c.deterministic);

    let verified: Vec<String> = cases
        .iter()
        .filter(|c| c.ok && c.deterministic)
        .map(|c| format!("{}:{}:f32", c.path, c.op))
        .collect();
    let payload = serde_json::json!({
        "schema": hcsuda_core::SCHEMA_VERSION,
        "device": runner.dev.name(),
        "driver": format!("{:#x}", runner.dev.props.driver_version),
        "api_version": runner.dev.api_version(),
        "ok": all_ok,
        "cases": cases.iter().map(|c| serde_json::json!({
            "op": c.op,
            "path": c.path,
            "dtype": "f32",
            "max_error": c.max_error,
            "tolerance": c.tolerance,
            "deterministic": c.deterministic,
            "ok": c.ok,
            "gpu_ms": c.gpu_ms,
        })).collect::<Vec<_>>(),
        "verified_paths": verified,
    });
    if let Some(path) = &out {
        write_json(path, &payload)?;
    }
    if json {
        println!("{}", serde_json::to_string_pretty(&payload)?);
    } else {
        println!("{}", runner.label());
        println!();
        println!(
            "{:<8} {:<14} {:>12} {:>12} {:>6} {:>9}",
            "op", "path", "max_error", "tolerance", "det", "gpu_ms"
        );
        for c in &cases {
            println!(
                "{:<8} {:<14} {:>12.3e} {:>12.3e} {:>6} {:>9}",
                c.op,
                c.path,
                c.max_error,
                c.tolerance,
                if c.deterministic { "yes" } else { "NO" },
                c.gpu_ms
                    .map(|v| format!("{v:.3}"))
                    .unwrap_or_else(|| "-".into())
            );
        }
        println!();
        if all_ok {
            println!("result      PASS — every kernel is within tolerance of the CPU oracle");
            println!(
                "verified    {}",
                cases
                    .iter()
                    .map(|c| format!("{}:{}:f32", c.path, c.op))
                    .collect::<Vec<_>>()
                    .join(", ")
            );
        } else {
            println!("result      FAIL — see the rows above");
        }
    }

    if !all_ok {
        std::process::exit(1);
    }
    Ok(())
}

fn cmd_bench(
    suite: &str,
    runs: u32,
    reps: u32,
    json: bool,
    device: Option<usize>,
    out: Option<PathBuf>,
) -> Result<()> {
    if runs < 3 {
        anyhow::bail!("--runs must be at least 3 (a single number is not evidence)");
    }
    if reps == 0 {
        anyhow::bail!("--reps must be at least 1");
    }
    let ops: Vec<&str> = suite
        .split(',')
        .map(|s| s.trim())
        .filter(|s| !s.is_empty())
        .collect();
    if ops.is_empty() {
        anyhow::bail!("--suite is empty");
    }

    let mut runner = gpu::Runner::new(device)?;
    let driver = format!("{:#x}", runner.dev.props.driver_version);
    let mut out_suite = BenchSuite::new(runner.dev.name(), driver.clone());

    let n = 4 << 20; // 4 Mi elements = 16 MiB per f32 vector
    let rows = 512usize;
    let cols = 8192usize;

    for op in &ops {
        match *op {
            "saxpy" => {
                let x: Vec<f32> = (0..n).map(|i| ((i % 251) as f32 - 125.0) * 0.01).collect();
                let y: Vec<f32> = (0..n).map(|i| ((i % 127) as f32 - 63.0) * 0.02).collect();
                let gx = runner.upload(&x)?;
                let gy = runner.upload(&y)?;
                runner.saxpy(1.5, &gx, &gy)?; // warm-up
                let timings = sample(runs, reps, || runner.saxpy(1.5, &gx, &gy))?;
                let (wall, gpu_stats) = split_timings(timings);
                out_suite.push(
                    BenchRow::from_samples(
                        "saxpy",
                        "f32",
                        [n, 0, 0],
                        "vulkan_scalar",
                        &runner.dev.name(),
                        &driver,
                        wall,
                        Some(2.0 * n as f64),
                        Some(12 * n as u64),
                    )
                    .with_gpu_stats(gpu_stats),
                );

                let mut cpu = Vec::with_capacity(runs as usize);
                for _ in 0..runs {
                    let mut yc = y.clone();
                    let started = Instant::now();
                    reference::saxpy(1.5, &x, &mut yc);
                    cpu.push(started.elapsed().as_secs_f64() * 1000.0);
                }
                out_suite.push(BenchRow::from_samples(
                    "saxpy",
                    "f32",
                    [n, 0, 0],
                    "reference",
                    &runner.dev.name(),
                    &driver,
                    cpu,
                    Some(2.0 * n as f64),
                    Some(12 * n as u64),
                ));
            }
            "triad" => {
                let b: Vec<f32> = (0..n).map(|i| ((i % 251) as f32 - 125.0) * 0.01).collect();
                let c: Vec<f32> = (0..n).map(|i| ((i % 127) as f32 - 63.0) * 0.02).collect();
                let ga = runner.upload(&vec![0.0f32; n])?;
                let gb = runner.upload(&b)?;
                let gc = runner.upload(&c)?;
                runner.triad(1.5, &ga, &gb, &gc)?;
                let timings = sample(runs, reps, || runner.triad(1.5, &ga, &gb, &gc))?;
                let (wall, gpu_stats) = split_timings(timings);
                out_suite.push(
                    BenchRow::from_samples(
                        "triad",
                        "f32",
                        [n, 0, 0],
                        "vulkan_scalar",
                        &runner.dev.name(),
                        &driver,
                        wall,
                        Some(2.0 * n as f64),
                        Some(16 * n as u64),
                    )
                    .with_gpu_stats(gpu_stats),
                );

                let mut cpu = Vec::with_capacity(runs as usize);
                for _ in 0..runs {
                    let mut a = vec![0.0f32; n];
                    let started = Instant::now();
                    reference::triad(&mut a, &b, &c, 1.5);
                    cpu.push(started.elapsed().as_secs_f64() * 1000.0);
                }
                out_suite.push(BenchRow::from_samples(
                    "triad",
                    "f32",
                    [n, 0, 0],
                    "reference",
                    &runner.dev.name(),
                    &driver,
                    cpu,
                    Some(2.0 * n as f64),
                    Some(16 * n as u64),
                ));
            }
            "gemv" => {
                let a: Vec<f32> = (0..rows * cols)
                    .map(|i| ((i % 97) as f32 - 48.0) * 0.01)
                    .collect();
                let xv: Vec<f32> = (0..cols).map(|i| ((i % 31) as f32 - 15.0) * 0.05).collect();
                let ga = runner.upload(&a)?;
                let gx = runner.upload(&xv)?;
                let gy = runner.upload(&vec![0.0f32; rows])?;
                runner.gemv(&ga, &gx, &gy, rows, cols)?;
                let timings = sample(runs, reps, || runner.gemv(&ga, &gx, &gy, rows, cols))?;
                let (wall, gpu_stats) = split_timings(timings);
                out_suite.push(
                    BenchRow::from_samples(
                        "gemv",
                        "f32",
                        [rows, cols, 0],
                        "vulkan_scalar",
                        &runner.dev.name(),
                        &driver,
                        wall,
                        Some(2.0 * rows as f64 * cols as f64),
                        Some(4 * (rows * cols + cols + rows) as u64),
                    )
                    .with_gpu_stats(gpu_stats),
                );

                let mut cpu = Vec::with_capacity(runs as usize);
                for _ in 0..runs {
                    let started = Instant::now();
                    let _ = reference::gemv(&a, &xv, rows, cols);
                    cpu.push(started.elapsed().as_secs_f64() * 1000.0);
                }
                out_suite.push(BenchRow::from_samples(
                    "gemv",
                    "f32",
                    [rows, cols, 0],
                    "reference",
                    &runner.dev.name(),
                    &driver,
                    cpu,
                    Some(2.0 * rows as f64 * cols as f64),
                    Some(4 * (rows * cols + cols + rows) as u64),
                ));
            }
            other => anyhow::bail!("unsupported suite op '{other}' (supported: saxpy,triad,gemv)"),
        }
    }

    if let Some(path) = &out {
        if let Some(parent) = path.parent() {
            std::fs::create_dir_all(parent).ok();
        }
        std::fs::write(path, serde_json::to_string_pretty(&out_suite)?)
            .with_context(|| format!("writing {}", path.display()))?;
    }

    if json {
        println!("{}", serde_json::to_string_pretty(&out_suite)?);
    } else {
        println!("{}", runner.label());
        println!();
        println!(
            "{:<8} {:<16} {:>10} {:>18} {:>9} {:>8} {:>8}",
            "op", "path", "median_ms", "gpu_ms (spread)", "wall_spr", "GFLOP/s", "GB/s"
        );
        for row in &out_suite.rows {
            println!(
                "{:<8} {:<16} {:>10.3} {:>18} {:>9.2} {:>8} {:>8}",
                row.op,
                row.path,
                row.median_ms,
                match (row.gpu_median_ms, row.gpu_spread) {
                    (Some(m), Some(s)) => format!("{m:.3} ({s:.2})"),
                    (Some(m), None) => format!("{m:.3}"),
                    _ => "-".to_string(),
                },
                row.spread(),
                row.gflops
                    .map(|v| format!("{v:.2}"))
                    .unwrap_or_else(|| "-".into()),
                row.gbps
                    .map(|v| format!("{v:.2}"))
                    .unwrap_or_else(|| "-".into()),
            );
        }
        let gpu_noisy: Vec<&str> = out_suite
            .rows
            .iter()
            .filter(|r| r.gpu_spread.map(|s| s > 0.25).unwrap_or(false))
            .map(|r| r.op.as_str())
            .collect();
        let wall_noisy: Vec<&str> = out_suite
            .rows
            .iter()
            .filter(|r| r.spread() > 0.25)
            .map(|r| r.op.as_str())
            .collect();
        if !gpu_noisy.is_empty() {
            println!(
                "\nnote        GPU-side spread above 25%: {}",
                gpu_noisy.join(", ")
            );
        } else if !wall_noisy.is_empty() {
            println!(
                "\nnote        wall clock is noisy (submit + fence overhead); \
                 GPU timestamps are stable, so trust the gpu_ms column"
            );
        }
    }
    Ok(())
}
