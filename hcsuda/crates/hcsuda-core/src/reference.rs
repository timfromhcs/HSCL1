//! CPU reference kernels. This is the oracle: every GPU path is compared
//! against these functions, so they are written for clarity, not speed.

/// `y = alpha * x + y`
pub fn saxpy(alpha: f32, x: &[f32], y: &mut [f32]) {
    assert_eq!(x.len(), y.len());
    for (yi, xi) in y.iter_mut().zip(x.iter()) {
        *yi += alpha * *xi;
    }
}

/// `a = b + alpha * c`
pub fn triad(a: &mut [f32], b: &[f32], c: &[f32], alpha: f32) {
    assert_eq!(a.len(), b.len());
    assert_eq!(a.len(), c.len());
    for i in 0..a.len() {
        a[i] = b[i] + alpha * c[i];
    }
}

/// Row-major matrix-vector product: `y = A * x`, A is `rows x cols`.
pub fn gemv(a: &[f32], x: &[f32], rows: usize, cols: usize) -> Vec<f32> {
    assert_eq!(a.len(), rows * cols, "matrix shape");
    assert_eq!(x.len(), cols, "vector shape");
    let mut y = vec![0.0f32; rows];
    for r in 0..rows {
        let row = &a[r * cols..(r + 1) * cols];
        let mut acc = 0.0f32;
        for (av, xv) in row.iter().zip(x.iter()) {
            acc += av * xv;
        }
        y[r] = acc;
    }
    y
}

/// Row-major matrix-matrix product: `C = A * B`, A `m x k`, B `k x n`.
pub fn gemm(a: &[f32], b: &[f32], m: usize, k: usize, n: usize) -> Vec<f32> {
    assert_eq!(a.len(), m * k, "A shape");
    assert_eq!(b.len(), k * n, "B shape");
    let mut c = vec![0.0f32; m * n];
    for r in 0..m {
        for col in 0..n {
            let mut acc = 0.0f32;
            for i in 0..k {
                acc += a[r * k + i] * b[i * n + col];
            }
            c[r * n + col] = acc;
        }
    }
    c
}

/// Integer matrix product with i32 accumulation: `C = A * B`, A `m x k`, B `k x n`.
pub fn gemm_i8(a: &[i8], b: &[i8], m: usize, k: usize, n: usize) -> Vec<i32> {
    assert_eq!(a.len(), m * k, "A shape");
    assert_eq!(b.len(), k * n, "B shape");
    let mut c = vec![0i32; m * n];
    for r in 0..m {
        for col in 0..n {
            let mut acc = 0i32;
            for i in 0..k {
                acc += a[r * k + i] as i32 * b[i * n + col] as i32;
            }
            c[r * n + col] = acc;
        }
    }
    c
}

/// Numerically stable softmax over one row.
pub fn softmax(x: &[f32]) -> Vec<f32> {
    if x.is_empty() {
        return Vec::new();
    }
    let max = x.iter().copied().fold(f32::NEG_INFINITY, f32::max);
    let mut exps: Vec<f32> = x.iter().map(|v| (v - max).exp()).collect();
    let sum: f32 = exps.iter().sum();
    if sum == 0.0 || !sum.is_finite() {
        let n = exps.len() as f32;
        return vec![1.0 / n; exps.len()];
    }
    for e in exps.iter_mut() {
        *e /= sum;
    }
    exps
}

/// Layer normalisation over the last dimension of `rows x cols`.
pub fn layernorm(
    rows: usize,
    cols: usize,
    x: &[f32],
    gamma: &[f32],
    beta: &[f32],
    eps: f32,
) -> Vec<f32> {
    assert_eq!(x.len(), rows * cols);
    assert_eq!(gamma.len(), cols);
    assert_eq!(beta.len(), cols);
    let mut out = vec![0.0f32; x.len()];
    for r in 0..rows {
        let row = &x[r * cols..(r + 1) * cols];
        let mean = row.iter().sum::<f32>() / cols as f32;
        let var = row.iter().map(|v| (v - mean) * (v - mean)).sum::<f32>() / cols as f32;
        let inv = 1.0 / (var + eps).sqrt();
        for c in 0..cols {
            out[r * cols + c] = (row[c] - mean) * inv * gamma[c] + beta[c];
        }
    }
    out
}

/// Root-mean-square normalisation over the last dimension.
pub fn rmsnorm(rows: usize, cols: usize, x: &[f32], gamma: &[f32], eps: f32) -> Vec<f32> {
    assert_eq!(x.len(), rows * cols);
    assert_eq!(gamma.len(), cols);
    let mut out = vec![0.0f32; x.len()];
    for r in 0..rows {
        let row = &x[r * cols..(r + 1) * cols];
        let ms = row.iter().map(|v| v * v).sum::<f32>() / cols as f32;
        let inv = 1.0 / (ms + eps).sqrt();
        for c in 0..cols {
            out[r * cols + c] = row[c] * inv * gamma[c];
        }
    }
    out
}

/// GELU with the tanh approximation (the variant used by most transformer stacks).
pub fn gelu(x: &[f32]) -> Vec<f32> {
    let k = (2.0f32 / std::f32::consts::PI).sqrt();
    x.iter()
        .map(|v| 0.5 * v * (1.0 + (k * (v + 0.044_715 * v * v * v)).tanh()))
        .collect()
}

/// SiLU / swish: `x * sigmoid(x)`.
pub fn silu(x: &[f32]) -> Vec<f32> {
    x.iter().map(|v| v / (1.0 + (-v).exp())).collect()
}

pub fn reduce_sum(x: &[f32]) -> f32 {
    x.iter().sum()
}

pub fn reduce_max(x: &[f32]) -> f32 {
    x.iter().copied().fold(f32::NEG_INFINITY, f32::max)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn approx(a: &[f32], b: &[f32], tol: f32) {
        assert_eq!(a.len(), b.len());
        for (x, y) in a.iter().zip(b.iter()) {
            assert!((x - y).abs() <= tol, "{a:?} != {b:?} within {tol}");
        }
    }

    #[test]
    fn gemv_matches_hand_computation() {
        // [[1,2],[3,4]] * [5,6] = [17, 39]
        let y = gemv(&[1.0, 2.0, 3.0, 4.0], &[5.0, 6.0], 2, 2);
        approx(&y, &[17.0, 39.0], 0.0);
    }

    #[test]
    fn gemm_matches_hand_computation() {
        // [[1,2],[3,4]] * [[5,6],[7,8]] = [[19,22],[43,50]]
        let c = gemm(&[1.0, 2.0, 3.0, 4.0], &[5.0, 6.0, 7.0, 8.0], 2, 2, 2);
        approx(&c, &[19.0, 22.0, 43.0, 50.0], 0.0);
    }

    #[test]
    fn gemm_i8_matches_hand_computation() {
        let c = gemm_i8(&[1, 2, 3, 4], &[5, 6, 7, 8], 2, 2, 2);
        assert_eq!(c, vec![19, 22, 43, 50]);
    }

    #[test]
    fn softmax_sums_to_one_and_is_stable() {
        let s = softmax(&[1000.0, 1001.0, 1002.0]);
        let sum: f32 = s.iter().sum();
        assert!((sum - 1.0).abs() < 1e-6, "sum {sum}");
        assert!(s[2] > s[1] && s[1] > s[0]);
        assert!(softmax(&[]).is_empty());
    }

    #[test]
    fn layernorm_has_zero_mean_unit_variance() {
        let x = [1.0f32, 2.0, 3.0, 4.0];
        let y = layernorm(1, 4, &x, &[1.0; 4], &[0.0; 4], 1e-5);
        let mean: f32 = y.iter().sum::<f32>() / 4.0;
        let var: f32 = y.iter().map(|v| (v - mean) * (v - mean)).sum::<f32>() / 4.0;
        assert!(mean.abs() < 1e-5);
        assert!((var - 1.0).abs() < 1e-3);
    }

    #[test]
    fn rmsnorm_preserves_direction() {
        let x = [3.0f32, 4.0];
        let y = rmsnorm(1, 2, &x, &[1.0, 1.0], 0.0);
        // rms = sqrt((9+16)/2) = sqrt(12.5)
        let rms = (12.5f32).sqrt();
        approx(&y, &[3.0 / rms, 4.0 / rms], 1e-6);
    }

    #[test]
    fn gelu_and_silu_known_points() {
        approx(&gelu(&[0.0]), &[0.0], 0.0);
        approx(&silu(&[0.0]), &[0.0], 0.0);
        // silu(1) = 1/(1+e^-1) = 0.7310586
        approx(&silu(&[1.0]), &[0.731_058_6], 1e-6);
        // gelu(1) ~= 0.8411919
        approx(&gelu(&[1.0]), &[0.841_191_9], 1e-5);
    }

    #[test]
    fn reductions() {
        assert_eq!(reduce_sum(&[1.0, 2.0, 3.0]), 6.0);
        assert_eq!(reduce_max(&[1.0, 9.0, 3.0]), 9.0);
    }
}
