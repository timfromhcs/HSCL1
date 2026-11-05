//! Safe model downloads: explicit target directory, free-space check, sha256 + size verification against the catalog,
//! partial files never promoted, nothing is deleted except the model file itself.

use crate::catalog::Model;
use anyhow::{bail, Context, Result};
use sha2::{Digest, Sha256};
use std::io::Read;
use std::path::{Path, PathBuf};

/// Where models live: `HSCL_MODELS_DIR`, else `~/AI/Models` (AGENTS.md 9.4).
pub fn models_dir() -> PathBuf {
    if let Some(d) = std::env::var_os("HSCL_MODELS_DIR") {
        return PathBuf::from(d);
    }
    PathBuf::from(std::env::var_os("HOME").unwrap_or_default())
        .join("AI")
        .join("Models")
}

pub fn url_for(repo: &str, file: &str) -> String {
    format!("https://huggingface.co/{repo}/resolve/main/{file}")
}

pub fn sha256_file(p: &Path) -> Result<String> {
    let mut f = std::fs::File::open(p).with_context(|| format!("cannot open {}", p.display()))?;
    let mut h = Sha256::new();
    let mut buf = vec![0u8; 1 << 20];
    loop {
        let n = f.read(&mut buf)?;
        if n == 0 {
            break;
        }
        h.update(&buf[..n]);
    }
    Ok(h.finalize().iter().map(|b| format!("{b:02x}")).collect())
}

/// Check size and hash of a file against expected values.
pub fn verify_file(p: &Path, size: u64, sha: &str) -> Result<()> {
    let actual = std::fs::metadata(p)
        .with_context(|| format!("missing {}", p.display()))?
        .len();
    if actual != size {
        bail!(
            "size mismatch for {}: expected {size}, found {actual}",
            p.display()
        );
    }
    let h = sha256_file(p)?;
    if !h.eq_ignore_ascii_case(sha) {
        bail!("sha256 mismatch for {}", p.display());
    }
    Ok(())
}

/// A file name that stays inside the model directory.
fn safe_name(name: &str) -> Result<()> {
    if name.is_empty()
        || name.contains('/')
        || name.contains('\\')
        || name.contains("..")
        || name.contains('\0')
    {
        bail!("unsafe file name {name:?}");
    }
    Ok(())
}

pub trait Fetcher {
    /// Download `url` to `dest` (a `.part` file). Real implementation: curl with fixed arguments.
    fn fetch(&self, url: &str, dest: &Path) -> Result<()>;
}

pub struct CurlFetcher;

impl Fetcher for CurlFetcher {
    fn fetch(&self, url: &str, dest: &Path) -> Result<()> {
        if !url.starts_with("https://huggingface.co/") {
            bail!("refusing to download from {url}");
        }
        let st = std::process::Command::new("curl")
            .args([
                "--location",
                "--fail",
                "--retry",
                "2",
                "--continue-at",
                "-",
                "--output",
            ])
            .arg(dest)
            .arg(url)
            .status()
            .context("cannot run curl")?;
        if !st.success() {
            bail!("curl failed with {st}");
        }
        Ok(())
    }
}

fn one(
    dir: &Path,
    repo: &str,
    file: &str,
    size: u64,
    sha: &str,
    free_mib: Option<u64>,
    fetcher: &dyn Fetcher,
) -> Result<PathBuf> {
    safe_name(file)?;
    let final_path = dir.join(file);
    if final_path.exists() && verify_file(&final_path, size, sha).is_ok() {
        return Ok(final_path); // already complete and verified
    }
    if let Some(free) = free_mib {
        let need = size / (1024 * 1024) + 512;
        if free < need {
            bail!(
                "not enough free space in {}: need {need} MiB, have {free} MiB",
                dir.display()
            );
        }
    }
    std::fs::create_dir_all(dir).with_context(|| format!("cannot create {}", dir.display()))?;
    let part = dir.join(format!("{file}.part"));
    fetcher.fetch(&url_for(repo, file), &part)?;
    match verify_file(&part, size, sha) {
        Ok(()) => {
            std::fs::rename(&part, &final_path)?;
            Ok(final_path)
        }
        Err(e) => {
            let _ = std::fs::remove_file(&part); // a bad download is never kept
            Err(e.context("download rejected"))
        }
    }
}

/// Download (or re-verify) a catalog model, optionally with its vision projector. Returns the model path and mmproj path.
pub fn download(
    m: &Model,
    dir: &Path,
    with_vision: bool,
    free_mib: Option<u64>,
    fetcher: &dyn Fetcher,
) -> Result<(PathBuf, Option<PathBuf>)> {
    let model = one(
        dir,
        &m.repo,
        &m.file,
        m.size_bytes,
        &m.sha256,
        free_mib,
        fetcher,
    )?;
    let mm = match (&m.mmproj, with_vision) {
        (Some(p), true) => Some(one(
            dir,
            &m.repo,
            &p.file,
            p.size_bytes,
            &p.sha256,
            free_mib,
            fetcher,
        )?),
        (None, true) => bail!("{} has no vision projector in the catalog", m.id),
        _ => None,
    };
    Ok((model, mm))
}

/// Delete only the model file (and its projector) inside `dir`; never the directory.
pub fn remove(m: &Model, dir: &Path) -> Result<Vec<PathBuf>> {
    let mut gone = vec![];
    let mut names = vec![m.file.clone()];
    if let Some(p) = &m.mmproj {
        names.push(p.file.clone());
    }
    for n in names {
        safe_name(&n)?;
        let p = dir.join(&n);
        if p.is_file() {
            std::fs::remove_file(&p)?;
            gone.push(p);
        }
    }
    Ok(gone)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::catalog;

    struct Fake(Vec<u8>);
    impl Fetcher for Fake {
        fn fetch(&self, url: &str, dest: &Path) -> Result<()> {
            assert!(url.starts_with("https://huggingface.co/"));
            std::fs::write(dest, &self.0)?;
            Ok(())
        }
    }

    fn model_for(bytes: &[u8]) -> Model {
        let mut m = catalog::load().unwrap().remove(0);
        m.size_bytes = bytes.len() as u64;
        let tmp = tempfile::NamedTempFile::new().unwrap();
        std::fs::write(tmp.path(), bytes).unwrap();
        m.sha256 = sha256_file(tmp.path()).unwrap();
        m.mmproj = None;
        m
    }

    #[test]
    fn good_download_is_promoted_and_part_file_is_gone() {
        let dir = tempfile::tempdir().unwrap();
        let m = model_for(b"gguf-bytes");
        let (p, mm) = download(
            &m,
            dir.path(),
            false,
            Some(1_000_000),
            &Fake(b"gguf-bytes".to_vec()),
        )
        .unwrap();
        assert_eq!(std::fs::read(&p).unwrap(), b"gguf-bytes");
        assert!(mm.is_none());
        assert!(!dir.path().join(format!("{}.part", m.file)).exists());
    }

    #[test]
    fn tampered_download_is_rejected_and_nothing_is_kept() {
        let dir = tempfile::tempdir().unwrap();
        let m = model_for(b"gguf-bytes");
        let err = download(&m, dir.path(), false, None, &Fake(b"gguf-BYTES".to_vec())).unwrap_err();
        assert!(format!("{err:#}").contains("sha256 mismatch"));
        assert!(!dir.path().join(&m.file).exists());
        assert!(!dir.path().join(format!("{}.part", m.file)).exists());
    }

    #[test]
    fn truncated_download_is_rejected() {
        let dir = tempfile::tempdir().unwrap();
        let m = model_for(b"gguf-bytes");
        let err = download(&m, dir.path(), false, None, &Fake(b"gguf".to_vec())).unwrap_err();
        assert!(format!("{err:#}").contains("size mismatch"));
        assert!(!dir.path().join(&m.file).exists());
    }

    #[test]
    fn not_enough_disk_space_is_refused_before_fetching() {
        struct Never;
        impl Fetcher for Never {
            fn fetch(&self, _: &str, _: &Path) -> Result<()> {
                panic!("must not fetch")
            }
        }
        let dir = tempfile::tempdir().unwrap();
        let mut m = model_for(b"x");
        m.size_bytes = 5 * 1024 * 1024 * 1024;
        assert!(download(&m, dir.path(), false, Some(100), &Never).is_err());
    }

    #[test]
    fn existing_verified_file_is_not_downloaded_again() {
        struct Never;
        impl Fetcher for Never {
            fn fetch(&self, _: &str, _: &Path) -> Result<()> {
                panic!("must not fetch")
            }
        }
        let dir = tempfile::tempdir().unwrap();
        let m = model_for(b"abc");
        std::fs::write(dir.path().join(&m.file), b"abc").unwrap();
        assert!(download(&m, dir.path(), false, None, &Never).is_ok());
    }

    #[test]
    fn corrupt_existing_file_is_replaced_by_a_verified_download() {
        let dir = tempfile::tempdir().unwrap();
        let m = model_for(b"abc");
        std::fs::write(dir.path().join(&m.file), b"corrupted").unwrap();
        let (p, _) = download(&m, dir.path(), false, None, &Fake(b"abc".to_vec())).unwrap();
        assert_eq!(std::fs::read(p).unwrap(), b"abc");
    }

    #[test]
    fn unsafe_names_and_foreign_hosts_are_refused() {
        for n in ["../x.gguf", "a/b.gguf", "a\\b.gguf", ""] {
            assert!(safe_name(n).is_err(), "{n:?}");
        }
        let dir = tempfile::tempdir().unwrap();
        assert!(CurlFetcher
            .fetch("https://evil.example/x.gguf", &dir.path().join("x.part"))
            .is_err());
        assert!(CurlFetcher
            .fetch("file:///etc/passwd", &dir.path().join("x.part"))
            .is_err());
    }

    #[test]
    fn remove_deletes_only_the_model_file() {
        let dir = tempfile::tempdir().unwrap();
        let m = model_for(b"abc");
        std::fs::write(dir.path().join(&m.file), b"abc").unwrap();
        std::fs::write(dir.path().join("other.gguf"), b"keep").unwrap();
        assert_eq!(remove(&m, dir.path()).unwrap().len(), 1);
        assert!(dir.path().join("other.gguf").exists() && dir.path().exists());
        assert!(
            remove(&m, dir.path()).unwrap().is_empty(),
            "removing twice is harmless"
        );
    }

    #[test]
    fn vision_without_projector_is_an_error() {
        let dir = tempfile::tempdir().unwrap();
        let m = model_for(b"abc");
        assert!(download(&m, dir.path(), true, None, &Fake(b"abc".to_vec())).is_err());
    }
}
