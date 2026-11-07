//! Dequantisation against fixtures produced by the official `gguf` Python package
//! (`hcsuda/tools/gen_dequant_fixtures.py`), an implementation independent of this one.

use hcsuda_io::dequant::{dequantize, DequantError};
use hcsuda_io::GgmlType;

fn fixture(name: &str) -> Vec<u8> {
    let path = std::path::Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("tests/fixtures")
        .join(name);
    std::fs::read(&path).unwrap_or_else(|e| panic!("{}: {e}", path.display()))
}

fn floats(bytes: &[u8]) -> Vec<f32> {
    bytes
        .chunks_exact(4)
        .map(|c| f32::from_le_bytes([c[0], c[1], c[2], c[3]]))
        .collect()
}

fn check(name: &str, ty: GgmlType) {
    let raw = fixture(&format!("{name}.bin"));
    let want = floats(&fixture(&format!("{name}.f32")));
    let got = dequantize(ty, &raw, want.len()).unwrap();
    assert_eq!(got.len(), want.len(), "{name}: length");
    let mut worst = 0.0f32;
    for (i, (g, w)) in got.iter().zip(&want).enumerate() {
        let err = (g - w).abs();
        let tol = 1e-6 * w.abs().max(1.0);
        assert!(
            err <= tol,
            "{name}[{i}]: got {g}, want {w}, err {err} > {tol}"
        );
        worst = worst.max(err);
    }
    eprintln!("{name}: {} values, worst abs error {worst:e}", got.len());
}

#[test]
fn f32_f16_bf16_match() {
    check("f32", GgmlType::F32);
    check("f16", GgmlType::F16);
    check("bf16", GgmlType::Bf16);
}

#[test]
fn q8_0_matches() {
    check("q8_0", GgmlType::Q8_0);
}

#[test]
fn q4_0_matches() {
    check("q4_0", GgmlType::Q4_0);
}

#[test]
fn q4_k_matches() {
    check("q4_k", GgmlType::Q4K);
}

#[test]
fn q6_k_matches() {
    check("q6_k", GgmlType::Q6K);
}

#[test]
fn wrong_byte_length_is_an_error_not_a_panic() {
    let raw = fixture("q4_k.bin");
    assert!(matches!(
        dequantize(GgmlType::Q4K, &raw[..raw.len() - 1], 1536),
        Err(DequantError::SizeMismatch { .. })
    ));
    assert!(matches!(
        dequantize(GgmlType::Q4K, &raw, 1535),
        Err(DequantError::SizeMismatch { .. })
    ));
}

#[test]
fn unsupported_types_are_refused() {
    assert!(matches!(
        dequantize(GgmlType::Unknown(142), &[0u8; 64], 64),
        Err(DequantError::Unsupported(_))
    ));
    assert!(matches!(
        dequantize(GgmlType::Q5K, &[0u8; 176], 256),
        Err(DequantError::Unsupported(_))
    ));
}
