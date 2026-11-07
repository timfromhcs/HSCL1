//! Dequantisation of ggml tensor blocks to f32 (CPU reference).
//!
//! These follow the block layouts of ggml and are checked against fixtures from
//! the official `gguf` Python package. Supported: F32, F16, BF16, Q8_0, Q4_0,
//! Q4_K, Q6_K. Other types return [`DequantError::Unsupported`] instead of a
//! guess.

use hcsuda_core::tensor::f16_bits_to_f32;

use crate::GgmlType;

#[derive(Debug, thiserror::Error, PartialEq, Eq)]
pub enum DequantError {
    #[error("dequantisation of {0} is not implemented")]
    Unsupported(String),
    #[error("{ty}: {n_elements} elements need {expected} bytes, got {got}")]
    SizeMismatch {
        ty: String,
        n_elements: usize,
        expected: usize,
        got: usize,
    },
}

fn f16(b: &[u8]) -> f32 {
    f16_bits_to_f32(u16::from_le_bytes([b[0], b[1]]))
}

/// `(scale, min)` for sub-block `j` (0..8) of a Q4_K/Q5_K super-block.
fn scale_min_k4(j: usize, q: &[u8]) -> (u8, u8) {
    if j < 4 {
        (q[j] & 63, q[j + 4] & 63)
    } else {
        (
            (q[j + 4] & 0x0f) | ((q[j - 4] >> 6) << 4),
            (q[j + 4] >> 4) | ((q[j] >> 6) << 4),
        )
    }
}

/// Convert `n_elements` values stored as `ty` in `raw` to f32.
pub fn dequantize(ty: GgmlType, raw: &[u8], n_elements: usize) -> Result<Vec<f32>, DequantError> {
    let Some((block_elems, block_bytes)) = ty.block() else {
        return Err(DequantError::Unsupported(format!("{ty:?}")));
    };
    let supported = matches!(
        ty,
        GgmlType::F32
            | GgmlType::F16
            | GgmlType::Bf16
            | GgmlType::Q8_0
            | GgmlType::Q4_0
            | GgmlType::Q4K
            | GgmlType::Q6K
    );
    if !supported {
        return Err(DequantError::Unsupported(format!("{ty:?}")));
    }
    let be = block_elems as usize;
    let bb = block_bytes as usize;
    let expected = (n_elements / be)
        .checked_mul(bb)
        .filter(|_| n_elements % be == 0);
    if expected != Some(raw.len()) {
        return Err(DequantError::SizeMismatch {
            ty: format!("{ty:?}"),
            n_elements,
            expected: expected.unwrap_or(usize::MAX),
            got: raw.len(),
        });
    }

    let mut out = Vec::with_capacity(n_elements);
    match ty {
        GgmlType::F32 => {
            out.extend(
                raw.chunks_exact(4)
                    .map(|c| f32::from_le_bytes([c[0], c[1], c[2], c[3]])),
            );
        }
        GgmlType::F16 => out.extend(raw.chunks_exact(2).map(f16)),
        GgmlType::Bf16 => out.extend(
            raw.chunks_exact(2)
                .map(|c| f32::from_bits((u16::from_le_bytes([c[0], c[1]]) as u32) << 16)),
        ),
        GgmlType::Q8_0 => {
            for blk in raw.chunks_exact(bb) {
                let d = f16(&blk[0..2]);
                out.extend(blk[2..34].iter().map(|q| d * (*q as i8) as f32));
            }
        }
        GgmlType::Q4_0 => {
            for blk in raw.chunks_exact(bb) {
                let d = f16(&blk[0..2]);
                let qs = &blk[2..18];
                out.extend(qs.iter().map(|q| d * ((q & 0x0f) as i32 - 8) as f32));
                out.extend(qs.iter().map(|q| d * ((q >> 4) as i32 - 8) as f32));
            }
        }
        GgmlType::Q4K => {
            for blk in raw.chunks_exact(bb) {
                let d = f16(&blk[0..2]);
                let dmin = f16(&blk[2..4]);
                let scales = &blk[4..16];
                let qs = &blk[16..144];
                for (g, q) in qs.chunks_exact(32).enumerate() {
                    let (sc1, m1) = scale_min_k4(2 * g, scales);
                    let (sc2, m2) = scale_min_k4(2 * g + 1, scales);
                    let (d1, mn1) = (d * sc1 as f32, dmin * m1 as f32);
                    let (d2, mn2) = (d * sc2 as f32, dmin * m2 as f32);
                    out.extend(q.iter().map(|b| d1 * (b & 0x0f) as f32 - mn1));
                    out.extend(q.iter().map(|b| d2 * (b >> 4) as f32 - mn2));
                }
            }
        }
        GgmlType::Q6K => {
            for blk in raw.chunks_exact(bb) {
                let ql = &blk[0..128];
                let qh = &blk[128..192];
                let sc = &blk[192..208];
                let d = f16(&blk[208..210]);
                let mut y = [0.0f32; 256];
                for half in 0..2 {
                    let ql = &ql[half * 64..];
                    let qh = &qh[half * 32..];
                    let sc = &sc[half * 8..];
                    let y = &mut y[half * 128..half * 128 + 128];
                    for l in 0..32 {
                        let is = l / 16;
                        let q1 = ((ql[l] & 0x0f) | ((qh[l] & 3) << 4)) as i32 - 32;
                        let q2 = ((ql[l + 32] & 0x0f) | (((qh[l] >> 2) & 3) << 4)) as i32 - 32;
                        let q3 = ((ql[l] >> 4) | (((qh[l] >> 4) & 3) << 4)) as i32 - 32;
                        let q4 = ((ql[l + 32] >> 4) | (((qh[l] >> 6) & 3) << 4)) as i32 - 32;
                        y[l] = d * (sc[is] as i8) as f32 * q1 as f32;
                        y[l + 32] = d * (sc[is + 2] as i8) as f32 * q2 as f32;
                        y[l + 64] = d * (sc[is + 4] as i8) as f32 * q3 as f32;
                        y[l + 96] = d * (sc[is + 6] as i8) as f32 * q4 as f32;
                    }
                }
                out.extend_from_slice(&y);
            }
        }
        _ => unreachable!("filtered above"),
    }
    Ok(out)
}
