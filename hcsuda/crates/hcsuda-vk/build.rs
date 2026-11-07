//! Compile the GLSL compute shaders to SPIR-V at build time.
//!
//! `glslc` comes from the Vulkan SDK. When it is absent (a plain CI runner), the
//! build still succeeds and the backend reports "no shaders" instead of
//! pretending: GPU tests then skip with an explicit reason.

use std::path::{Path, PathBuf};
use std::process::Command;

fn main() {
    println!("cargo:rerun-if-changed=shaders");
    println!("cargo:rerun-if-env-changed=GLSLC");

    let out_dir = PathBuf::from(std::env::var("OUT_DIR").expect("OUT_DIR"));
    let manifest = PathBuf::from(std::env::var("CARGO_MANIFEST_DIR").expect("CARGO_MANIFEST_DIR"));
    let shader_dir = manifest.join("shaders");

    let glslc = std::env::var_os("GLSLC")
        .map(PathBuf::from)
        .or_else(|| find_in_path("glslc"));
    let mut entries = String::new();
    let mut all_ok = true;
    let mut count = 0usize;

    if let Some(glslc) = glslc {
        if let Ok(read) = std::fs::read_dir(&shader_dir) {
            let mut paths: Vec<PathBuf> = read.flatten().map(|e| e.path()).collect();
            paths.sort();
            for path in paths {
                if path.extension().and_then(|s| s.to_str()) != Some("comp") {
                    continue;
                }
                let stem = path
                    .file_stem()
                    .map(|s| s.to_string_lossy().replace('-', "_"))
                    .unwrap_or_default();
                let spv = out_dir.join(format!("{stem}.spv"));
                let status = Command::new(&glslc)
                    .arg("--target-env=vulkan1.3")
                    .arg("-O")
                    .arg(&path)
                    .arg("-o")
                    .arg(&spv)
                    .status();
                match status {
                    Ok(s) if s.success() => {
                        let literal = spv.to_string_lossy().replace('\\', "/");
                        entries.push_str(&format!(
                            "    (\"{stem}\", include_bytes!(\"{literal}\").as_slice()),\n"
                        ));
                        count += 1;
                    }
                    _ => {
                        all_ok = false;
                        println!("cargo:warning=glslc failed for {}", path.display());
                    }
                }
            }
        }
    } else {
        println!("cargo:warning=glslc not found: GPU pipelines disabled, GPU tests will skip");
        all_ok = false;
    }

    let available = all_ok && count > 0;
    let body = format!(
        "/// Shaders compiled into the binary, keyed by file stem.\npub static SHADERS: &[(&str, &[u8])] = &[\n{entries}];\n/// True when every shader compiled during this build.\npub const SHADERS_AVAILABLE: bool = {available};\n"
    );
    std::fs::write(out_dir.join("shaders.rs"), body).expect("write shaders.rs");
    if !available {
        println!("cargo:rustc-cfg=hcsuda_no_shaders");
    }
}

fn find_in_path(name: &str) -> Option<PathBuf> {
    let path = std::env::var_os("PATH")?;
    let exe = if cfg!(windows) {
        format!("{name}.exe")
    } else {
        name.to_string()
    };
    std::env::split_paths(&path)
        .map(|dir| dir.join(&exe))
        .find(|candidate| is_file(candidate))
}

fn is_file(path: &Path) -> bool {
    path.is_file()
}
