//! The Qwen3-style decoder layer (GQA, QK-norm, GGUF [out, in] weights) against a
//! NumPy forward pass written independently (`hcsuda/tools/gen_layer_fixture.py`).

use hcsuda_core::transformer::{layer_forward, LayerConfig, LayerWeights};

fn load(name: &str) -> Vec<f32> {
    let path = std::path::Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("tests/fixtures/layer")
        .join(format!("{name}.f32"));
    let bytes = std::fs::read(&path).unwrap_or_else(|e| panic!("{}: {e}", path.display()));
    bytes
        .chunks_exact(4)
        .map(|c| f32::from_le_bytes([c[0], c[1], c[2], c[3]]))
        .collect()
}

fn cfg() -> LayerConfig {
    LayerConfig {
        tokens: 5,
        dim: 32,
        q_heads: 4,
        kv_heads: 2,
        head_dim: 16,
        ffn: 48,
        eps: 1e-6,
        rope_base: 5_000_000.0,
    }
}

fn weights() -> LayerWeights {
    LayerWeights {
        attn_norm: load("attn_norm"),
        wq: load("wq"),
        wk: load("wk"),
        wv: load("wv"),
        q_norm: Some(load("q_norm")),
        k_norm: Some(load("k_norm")),
        wo: load("wo"),
        ffn_norm: load("ffn_norm"),
        wg: load("wg"),
        wu: load("wu"),
        wd: load("wd"),
    }
}

#[test]
fn layer_forward_matches_numpy() {
    let got = layer_forward(&cfg(), &weights(), &load("x")).unwrap();
    let want = load("out");
    assert_eq!(got.len(), want.len());
    let mut worst = 0.0f32;
    for (i, (g, w)) in got.iter().zip(&want).enumerate() {
        let err = (g - w).abs();
        assert!(
            err <= 1e-4 * w.abs().max(1.0),
            "out[{i}]: got {g}, want {w}, err {err}"
        );
        worst = worst.max(err);
    }
    eprintln!("layer: {} values, worst abs error {worst:e}", got.len());
}

#[test]
fn causal_future_tokens_do_not_change_earlier_rows() {
    let c = cfg();
    let w = weights();
    let x = load("x");
    let base = layer_forward(&c, &w, &x).unwrap();
    let mut x2 = x.clone();
    for v in &mut x2[(c.tokens - 1) * c.dim..] {
        *v += 2.0;
    }
    let changed = layer_forward(&c, &w, &x2).unwrap();
    let keep = (c.tokens - 1) * c.dim;
    assert_eq!(base[..keep], changed[..keep]);
    assert_ne!(base[keep..], changed[keep..]);
}

#[test]
fn qk_norm_is_applied_when_present() {
    let c = cfg();
    let x = load("x");
    let with = layer_forward(&c, &weights(), &x).unwrap();
    let mut no_norm = weights();
    no_norm.q_norm = None;
    no_norm.k_norm = None;
    let without = layer_forward(&c, &no_norm, &x).unwrap();
    assert_ne!(with, without);
}

#[test]
fn bad_shapes_are_errors_not_panics() {
    let w = weights();
    let x = load("x");
    let mut c = cfg();
    c.kv_heads = 3; // 4 q heads do not divide into 3 groups
    assert!(layer_forward(&c, &w, &x).is_err());
    let mut c = cfg();
    c.head_dim = 15; // odd: RoPE needs pairs
    assert!(layer_forward(&c, &w, &x).is_err());
    assert!(layer_forward(&cfg(), &w, &x[1..]).is_err());
    let mut bad = weights();
    bad.wk.pop();
    assert!(layer_forward(&cfg(), &bad, &x).is_err());
    let mut bad = weights();
    bad.q_norm = Some(vec![1.0; 3]);
    assert!(layer_forward(&cfg(), &bad, &x).is_err());
}
