//! A single decoder block, CPU reference.
//!
//! RMSNorm -> Q/K/V projections -> RoPE (split-half, per head) -> causal
//! multi-head attention -> output projection + residual -> RMSNorm -> SwiGLU
//! feed-forward + residual. Weights are row-major `[in, out]` so every
//! projection is `reference::gemm(x, w, ..)`.
//!
//! This is the oracle the GPU composition is later checked against; it is itself
//! checked against an independent NumPy implementation
//! (`hcsuda/tools/gen_block_fixture.py`).

use crate::reference;

#[derive(Debug, Clone, Copy, PartialEq)]
pub struct BlockConfig {
    pub tokens: usize,
    pub dim: usize,
    pub heads: usize,
    pub ffn: usize,
    pub eps: f32,
    pub rope_base: f32,
}

#[derive(Debug, Clone, PartialEq)]
pub struct BlockWeights {
    pub g1: Vec<f32>,
    pub g2: Vec<f32>,
    pub wq: Vec<f32>,
    pub wk: Vec<f32>,
    pub wv: Vec<f32>,
    pub wo: Vec<f32>,
    pub wg: Vec<f32>,
    pub wu: Vec<f32>,
    pub wd: Vec<f32>,
}

#[derive(Debug, thiserror::Error, PartialEq, Eq)]
pub enum BlockError {
    #[error("{0}")]
    Shape(String),
}

fn expect(name: &str, got: usize, want: usize) -> Result<(), BlockError> {
    if got == want {
        Ok(())
    } else {
        Err(BlockError::Shape(format!(
            "{name}: {got} values, expected {want}"
        )))
    }
}

/// Copy columns `[c0, c0 + width)` of a `[rows, cols]` matrix.
fn cols(m: &[f32], rows: usize, cols_n: usize, c0: usize, width: usize) -> Vec<f32> {
    let mut out = Vec::with_capacity(rows * width);
    for r in 0..rows {
        out.extend_from_slice(&m[r * cols_n + c0..r * cols_n + c0 + width]);
    }
    out
}

pub fn block_forward(
    cfg: &BlockConfig,
    w: &BlockWeights,
    x: &[f32],
) -> Result<Vec<f32>, BlockError> {
    let (t, d, f) = (cfg.tokens, cfg.dim, cfg.ffn);
    if cfg.heads == 0 || d % cfg.heads != 0 {
        return Err(BlockError::Shape(format!(
            "dim {d} is not divisible by {} heads",
            cfg.heads
        )));
    }
    let hd = d / cfg.heads;
    if hd % 2 != 0 {
        return Err(BlockError::Shape(format!(
            "head dim {hd} must be even for RoPE"
        )));
    }
    expect("x", x.len(), t * d)?;
    expect("g1", w.g1.len(), d)?;
    expect("g2", w.g2.len(), d)?;
    for (name, m) in [("wq", &w.wq), ("wk", &w.wk), ("wv", &w.wv), ("wo", &w.wo)] {
        expect(name, m.len(), d * d)?;
    }
    expect("wg", w.wg.len(), d * f)?;
    expect("wu", w.wu.len(), d * f)?;
    expect("wd", w.wd.len(), f * d)?;

    let h = reference::rmsnorm(t, d, x, &w.g1, cfg.eps);
    let q = reference::gemm(&h, &w.wq, t, d, d);
    let k = reference::gemm(&h, &w.wk, t, d, d);
    let v = reference::gemm(&h, &w.wv, t, d, d);

    let mut ctx = vec![0.0f32; t * d];
    let scale = 1.0 / (hd as f32).sqrt();
    for head in 0..cfg.heads {
        let c0 = head * hd;
        let qh = reference::rope(t, hd, &cols(&q, t, d, c0, hd), 0, cfg.rope_base);
        let kh = reference::rope(t, hd, &cols(&k, t, d, c0, hd), 0, cfg.rope_base);
        let vh = cols(&v, t, d, c0, hd);
        for i in 0..t {
            // Causal: token i attends to tokens 0..=i only.
            let scores: Vec<f32> = (0..=i)
                .map(|j| {
                    let dot: f32 = (0..hd).map(|e| qh[i * hd + e] * kh[j * hd + e]).sum();
                    dot * scale
                })
                .collect();
            let weights = reference::softmax(&scores);
            for e in 0..hd {
                let acc: f32 = weights
                    .iter()
                    .enumerate()
                    .map(|(j, wj)| wj * vh[j * hd + e])
                    .sum();
                ctx[i * d + c0 + e] = acc;
            }
        }
    }

    let attn = reference::gemm(&ctx, &w.wo, t, d, d);
    let x1: Vec<f32> = x.iter().zip(&attn).map(|(a, b)| a + b).collect();

    let h2 = reference::rmsnorm(t, d, &x1, &w.g2, cfg.eps);
    let gate = reference::silu(&reference::gemm(&h2, &w.wg, t, d, f));
    let up = reference::gemm(&h2, &w.wu, t, d, f);
    let act: Vec<f32> = gate.iter().zip(&up).map(|(a, b)| a * b).collect();
    let down = reference::gemm(&act, &w.wd, t, f, d);
    Ok(x1.iter().zip(&down).map(|(a, b)| a + b).collect())
}

// ---------------------------------------------------------------------------
// Qwen3-style layer: grouped-query attention, optional QK-norm, GGUF weights.
// ---------------------------------------------------------------------------

#[derive(Debug, Clone, Copy, PartialEq)]
pub struct LayerConfig {
    pub tokens: usize,
    pub dim: usize,
    pub q_heads: usize,
    pub kv_heads: usize,
    pub head_dim: usize,
    pub ffn: usize,
    pub eps: f32,
    pub rope_base: f32,
}

/// Weights in GGUF's native layout: a projection with `in` inputs and `out`
/// outputs is stored as `[out][in]` row-major, so `y = x * W^T`.
#[derive(Debug, Clone, PartialEq)]
pub struct LayerWeights {
    pub attn_norm: Vec<f32>,
    pub wq: Vec<f32>,
    pub wk: Vec<f32>,
    pub wv: Vec<f32>,
    pub q_norm: Option<Vec<f32>>,
    pub k_norm: Option<Vec<f32>>,
    pub wo: Vec<f32>,
    pub ffn_norm: Vec<f32>,
    pub wg: Vec<f32>,
    pub wu: Vec<f32>,
    pub wd: Vec<f32>,
}

/// `y[t][o] = sum_i x[t][i] * w[o][i]`  (x is `[t, inp]`, w is `[out, inp]`).
///
/// Large products are split over output rows across threads. Every output
/// element is still a single sequential sum, so the result does not depend on
/// the thread count.
pub fn matmul_nt(x: &[f32], w: &[f32], t: usize, inp: usize, out: usize) -> Vec<f32> {
    assert_eq!(x.len(), t * inp);
    assert_eq!(w.len(), out * inp);
    let mut y = vec![0.0f32; t * out];
    let work = t * inp * out;
    let threads = if work < 1 << 22 {
        1
    } else {
        std::thread::available_parallelism()
            .map_or(1, |n| n.get())
            .min(out)
    };
    let chunk = out.div_ceil(threads).max(1);
    // Each thread owns a disjoint range of output columns, written via a local buffer.
    let parts: Vec<(usize, Vec<f32>)> = std::thread::scope(|s| {
        let handles: Vec<_> = (0..out)
            .step_by(chunk)
            .map(|o0| {
                let o1 = (o0 + chunk).min(out);
                s.spawn(move || {
                    let mut buf = vec![0.0f32; t * (o1 - o0)];
                    for row in 0..t {
                        let xr = &x[row * inp..(row + 1) * inp];
                        for o in o0..o1 {
                            let wr = &w[o * inp..(o + 1) * inp];
                            let mut acc = 0.0f32;
                            for i in 0..inp {
                                acc += xr[i] * wr[i];
                            }
                            buf[row * (o1 - o0) + (o - o0)] = acc;
                        }
                    }
                    (o0, buf)
                })
            })
            .collect();
        handles
            .into_iter()
            .map(|h| h.join().expect("matmul thread"))
            .collect()
    });
    for (o0, buf) in parts {
        let width = buf.len() / t.max(1);
        for row in 0..t {
            y[row * out + o0..row * out + o0 + width]
                .copy_from_slice(&buf[row * width..(row + 1) * width]);
        }
    }
    y
}

pub fn layer_forward(
    cfg: &LayerConfig,
    w: &LayerWeights,
    x: &[f32],
) -> Result<Vec<f32>, BlockError> {
    let (t, d, f, hd) = (cfg.tokens, cfg.dim, cfg.ffn, cfg.head_dim);
    if cfg.q_heads == 0 || cfg.kv_heads == 0 || cfg.q_heads % cfg.kv_heads != 0 {
        return Err(BlockError::Shape(format!(
            "{} q heads do not divide into {} kv heads",
            cfg.q_heads, cfg.kv_heads
        )));
    }
    if hd == 0 || hd % 2 != 0 {
        return Err(BlockError::Shape(format!(
            "head dim {hd} must be even and non-zero"
        )));
    }
    let (qd, kvd) = (cfg.q_heads * hd, cfg.kv_heads * hd);
    expect("x", x.len(), t * d)?;
    expect("attn_norm", w.attn_norm.len(), d)?;
    expect("ffn_norm", w.ffn_norm.len(), d)?;
    expect("wq", w.wq.len(), qd * d)?;
    expect("wk", w.wk.len(), kvd * d)?;
    expect("wv", w.wv.len(), kvd * d)?;
    expect("wo", w.wo.len(), d * qd)?;
    expect("wg", w.wg.len(), f * d)?;
    expect("wu", w.wu.len(), f * d)?;
    expect("wd", w.wd.len(), d * f)?;
    if let Some(n) = &w.q_norm {
        expect("q_norm", n.len(), hd)?;
    }
    if let Some(n) = &w.k_norm {
        expect("k_norm", n.len(), hd)?;
    }

    let h = reference::rmsnorm(t, d, x, &w.attn_norm, cfg.eps);
    let mut q = matmul_nt(&h, &w.wq, t, d, qd);
    let mut k = matmul_nt(&h, &w.wk, t, d, kvd);
    let v = matmul_nt(&h, &w.wv, t, d, kvd);
    // [t, heads*hd] is [t*heads, hd] in memory, so a per-head norm is a row-wise rmsnorm.
    if let Some(n) = &w.q_norm {
        q = reference::rmsnorm(t * cfg.q_heads, hd, &q, n, cfg.eps);
    }
    if let Some(n) = &w.k_norm {
        k = reference::rmsnorm(t * cfg.kv_heads, hd, &k, n, cfg.eps);
    }

    let group = cfg.q_heads / cfg.kv_heads;
    let scale = 1.0 / (hd as f32).sqrt();
    let k_rot: Vec<Vec<f32>> = (0..cfg.kv_heads)
        .map(|kh| reference::rope(t, hd, &cols(&k, t, kvd, kh * hd, hd), 0, cfg.rope_base))
        .collect();
    let v_head: Vec<Vec<f32>> = (0..cfg.kv_heads)
        .map(|kh| cols(&v, t, kvd, kh * hd, hd))
        .collect();
    let mut ctx = vec![0.0f32; t * qd];
    for head in 0..cfg.q_heads {
        let kv = head / group;
        let qh = reference::rope(t, hd, &cols(&q, t, qd, head * hd, hd), 0, cfg.rope_base);
        let (kh, vh) = (&k_rot[kv], &v_head[kv]);
        for i in 0..t {
            let scores: Vec<f32> = (0..=i)
                .map(|j| {
                    let dot: f32 = (0..hd).map(|e| qh[i * hd + e] * kh[j * hd + e]).sum();
                    dot * scale
                })
                .collect();
            let weights = reference::softmax(&scores);
            for e in 0..hd {
                let acc: f32 = weights
                    .iter()
                    .enumerate()
                    .map(|(j, wj)| wj * vh[j * hd + e])
                    .sum();
                ctx[i * qd + head * hd + e] = acc;
            }
        }
    }

    let attn = matmul_nt(&ctx, &w.wo, t, qd, d);
    let x1: Vec<f32> = x.iter().zip(&attn).map(|(a, b)| a + b).collect();
    let h2 = reference::rmsnorm(t, d, &x1, &w.ffn_norm, cfg.eps);
    let gate = reference::silu(&matmul_nt(&h2, &w.wg, t, d, f));
    let up = matmul_nt(&h2, &w.wu, t, d, f);
    let act: Vec<f32> = gate.iter().zip(&up).map(|(a, b)| a * b).collect();
    let down = matmul_nt(&act, &w.wd, t, f, d);
    Ok(x1.iter().zip(&down).map(|(a, b)| a + b).collect())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn threaded_matmul_is_bit_equal_to_the_naive_loop() {
        // 4 * 1024 * 2048 = 8.4M multiply-adds, above the threading threshold.
        let (t, inp, out) = (4usize, 1024usize, 2048usize);
        let x: Vec<f32> = (0..t * inp)
            .map(|i| ((i % 97) as f32 - 48.0) * 0.01)
            .collect();
        let w: Vec<f32> = (0..out * inp)
            .map(|i| ((i % 89) as f32 - 44.0) * 0.007)
            .collect();
        let got = matmul_nt(&x, &w, t, inp, out);
        for row in 0..t {
            for o in 0..out {
                let mut acc = 0.0f32;
                for i in 0..inp {
                    acc += x[row * inp + i] * w[o * inp + i];
                }
                assert_eq!(got[row * out + o], acc, "row {row} col {o}");
            }
        }
    }

    #[test]
    fn ragged_thread_chunks_cover_every_column() {
        // out = 2051 does not divide evenly by any plausible thread count.
        let (t, inp, out) = (3usize, 1500usize, 2051usize);
        let x = vec![1.0f32; t * inp];
        let w: Vec<f32> = (0..out * inp).map(|i| (i / inp) as f32).collect();
        let got = matmul_nt(&x, &w, t, inp, out);
        for row in 0..t {
            for o in 0..out {
                assert_eq!(got[row * out + o], (o * inp) as f32);
            }
        }
    }
}
