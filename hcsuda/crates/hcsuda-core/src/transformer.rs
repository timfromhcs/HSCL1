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
