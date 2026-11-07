//! The reference transformer block against a NumPy forward pass
//! (`hcsuda/tools/gen_block_fixture.py`), written independently of the Rust code.

use hcsuda_core::transformer::{block_forward, BlockConfig, BlockWeights};

fn load(name: &str) -> Vec<f32> {
    let path = std::path::Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("tests/fixtures/block")
        .join(format!("{name}.f32"));
    let bytes = std::fs::read(&path).unwrap_or_else(|e| panic!("{}: {e}", path.display()));
    bytes
        .chunks_exact(4)
        .map(|c| f32::from_le_bytes([c[0], c[1], c[2], c[3]]))
        .collect()
}

fn cfg() -> BlockConfig {
    BlockConfig {
        tokens: 6,
        dim: 32,
        heads: 4,
        ffn: 64,
        eps: 1e-5,
        rope_base: 10000.0,
    }
}

fn weights() -> BlockWeights {
    BlockWeights {
        g1: load("g1"),
        g2: load("g2"),
        wq: load("wq"),
        wk: load("wk"),
        wv: load("wv"),
        wo: load("wo"),
        wg: load("wg"),
        wu: load("wu"),
        wd: load("wd"),
    }
}

#[test]
fn block_forward_matches_numpy() {
    let got = block_forward(&cfg(), &weights(), &load("x")).unwrap();
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
    eprintln!("block: {} values, worst abs error {worst:e}", got.len());
}

#[test]
fn causal_mask_future_tokens_do_not_change_earlier_outputs() {
    let c = cfg();
    let w = weights();
    let x = load("x");
    let base = block_forward(&c, &w, &x).unwrap();
    // Change only the last token's input; rows 0..tokens-1 must be unchanged.
    let mut x2 = x.clone();
    for v in &mut x2[(c.tokens - 1) * c.dim..] {
        *v += 1.5;
    }
    let changed = block_forward(&c, &w, &x2).unwrap();
    let keep = (c.tokens - 1) * c.dim;
    assert_eq!(base[..keep], changed[..keep]);
    assert_ne!(base[keep..], changed[keep..]);
}

#[test]
fn bad_shapes_are_errors_not_panics() {
    let mut c = cfg();
    let w = weights();
    let x = load("x");
    assert!(block_forward(&c, &w, &x[1..]).is_err());
    c.heads = 5; // 32 is not divisible by 5
    assert!(block_forward(&c, &w, &x).is_err());
    let mut c = cfg();
    c.dim = 30; // weights no longer match
    assert!(block_forward(&c, &w, &x).is_err());
}
