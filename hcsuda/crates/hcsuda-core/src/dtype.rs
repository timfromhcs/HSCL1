use serde::{Deserialize, Serialize};

/// Every numeric format HCSUDA can store or compute in.
///
/// `Tf32` is a *compute* format (f32 with a 10-bit mantissa) and is stored as f32.
/// `I4` is packed two per byte.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum DType {
    F64,
    F32,
    Tf32,
    Bf16,
    F16,
    Fp8E4M3,
    Fp8E5M2,
    I8,
    I4,
}

impl DType {
    pub const ALL: [DType; 9] = [
        DType::F64,
        DType::F32,
        DType::Tf32,
        DType::Bf16,
        DType::F16,
        DType::Fp8E4M3,
        DType::Fp8E5M2,
        DType::I8,
        DType::I4,
    ];

    pub fn name(self) -> &'static str {
        match self {
            DType::F64 => "f64",
            DType::F32 => "f32",
            DType::Tf32 => "tf32",
            DType::Bf16 => "bf16",
            DType::F16 => "f16",
            DType::Fp8E4M3 => "fp8e4m3",
            DType::Fp8E5M2 => "fp8e5m2",
            DType::I8 => "i8",
            DType::I4 => "i4",
        }
    }

    /// Storage width in bits. `I4` is 4 bits, i.e. two values per byte.
    pub fn bits(self) -> u32 {
        match self {
            DType::F64 => 64,
            DType::F32 | DType::Tf32 => 32,
            DType::Bf16 | DType::F16 => 16,
            DType::Fp8E4M3 | DType::Fp8E5M2 | DType::I8 => 8,
            DType::I4 => 4,
        }
    }

    /// Bytes needed for `len` elements, rounded up. `I4` packs two per byte.
    pub fn bytes_for(self, len: usize) -> usize {
        match self {
            DType::I4 => len.div_ceil(2),
            _ => len * (self.bits() as usize / 8),
        }
    }

    pub fn is_float(self) -> bool {
        !matches!(self, DType::I8 | DType::I4)
    }

    pub fn is_quantized(self) -> bool {
        matches!(
            self,
            DType::I8 | DType::I4 | DType::Fp8E4M3 | DType::Fp8E5M2
        )
    }

    /// Reference tolerance used by the differential gate.
    ///
    /// The values are deliberately generous for narrow formats: they describe
    /// "same result up to the format", not "bit identical". `for_len` scales the
    /// absolute part with the reduction length, because a longer sum accumulates
    /// more rounding.
    pub fn tolerance(self) -> Tolerance {
        match self {
            DType::F64 => Tolerance {
                rel: 1e-12,
                abs: 1e-12,
            },
            DType::F32 | DType::Tf32 => Tolerance {
                rel: 1e-5,
                abs: 1e-6,
            },
            DType::Bf16 => Tolerance {
                rel: 3e-2,
                abs: 1e-3,
            },
            DType::F16 => Tolerance {
                rel: 1e-2,
                abs: 1e-3,
            },
            DType::Fp8E4M3 => Tolerance {
                rel: 6e-2,
                abs: 2e-2,
            },
            DType::Fp8E5M2 => Tolerance {
                rel: 1.5e-1,
                abs: 5e-2,
            },
            DType::I8 | DType::I4 => Tolerance { rel: 0.0, abs: 0.0 },
        }
    }
}

/// Relative + absolute tolerance pair. `abs` grows with `sqrt(len)` for
/// reductions so that a long dot product is not failed for its own rounding.
#[derive(Debug, Clone, Copy, PartialEq, Serialize, Deserialize)]
pub struct Tolerance {
    pub rel: f64,
    pub abs: f64,
}

impl Tolerance {
    pub fn for_len(self, len: usize) -> Tolerance {
        let scale = (len.max(1) as f64).sqrt();
        Tolerance {
            rel: self.rel,
            abs: self.abs * scale,
        }
    }

    /// `true` when `got` is within tolerance of `want`.
    pub fn accepts(self, want: f32, got: f32) -> bool {
        if want.is_nan() || got.is_nan() {
            return want.is_nan() && got.is_nan();
        }
        if want.is_infinite() || got.is_infinite() {
            return want == got;
        }
        let diff = (want as f64 - got as f64).abs();
        diff <= self.abs + self.rel * (want as f64).abs()
    }

    pub fn max_error(self, want: &[f32], got: &[f32]) -> Option<f64> {
        if want.len() != got.len() {
            return None;
        }
        let mut worst: f64 = 0.0;
        for (w, g) in want.iter().zip(got.iter()) {
            if w.is_nan() || g.is_nan() {
                if !(w.is_nan() && g.is_nan()) {
                    return Some(f64::INFINITY);
                }
                continue;
            }
            let diff = (*w as f64 - *g as f64).abs();
            worst = worst.max(diff);
        }
        Some(worst)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn i4_packs_two_per_byte() {
        assert_eq!(DType::I4.bytes_for(1), 1);
        assert_eq!(DType::I4.bytes_for(2), 1);
        assert_eq!(DType::I4.bytes_for(3), 2);
        assert_eq!(DType::F16.bytes_for(3), 6);
    }

    #[test]
    fn tolerance_scales_with_reduction_length() {
        let t = DType::F32.tolerance().for_len(4096);
        assert!(t.abs > DType::F32.tolerance().abs);
        // abs grows to 1e-6 * 64 = 6.4e-5, so a 5e-5 deviation is accepted ...
        assert!(t.accepts(1.0, 1.0 + 5e-5));
        // ... while a 1% deviation is not.
        assert!(!t.accepts(1.0, 1.01));
    }

    #[test]
    fn nan_only_matches_nan() {
        let t = DType::F32.tolerance();
        assert!(t.accepts(f32::NAN, f32::NAN));
        assert!(!t.accepts(1.0, f32::NAN));
    }
}
