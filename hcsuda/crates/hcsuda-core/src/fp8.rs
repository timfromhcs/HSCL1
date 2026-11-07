//! FP8 (E4M3 and E5M2) encode/decode.
//!
//! RDNA2 has no FP8 arithmetic units and no `VK_EXT_shader_float8`, so on this
//! hardware FP8 is a **storage and quantisation** format: values are decoded to
//! f16/f32 for compute. These functions are the exact reference the GPU
//! conversion path is checked against.
//!
//! Encoding is round-to-nearest-even against the real value table (128 finite
//! codes per sign), with saturation to the largest finite value. That is the
//! behaviour of hardware FP8 converters and avoids the classic "inf on overflow"
//! surprise in a quantised model.

use std::sync::OnceLock;

/// Decode one E4M3 byte (bias 7, no infinities, `0x7F`/`0xFF` are NaN).
pub fn e4m3_to_f32(byte: u8) -> f32 {
    let sign = if byte & 0x80 != 0 { -1.0 } else { 1.0 };
    let exp = ((byte >> 3) & 0x0F) as i32;
    let mant = (byte & 0x07) as f32;
    if exp == 0x0F && (byte & 0x07) == 0x07 {
        return f32::NAN;
    }
    let magnitude = if exp == 0 {
        (mant / 8.0) * 2f32.powi(-6)
    } else {
        (1.0 + mant / 8.0) * 2f32.powi(exp - 7)
    };
    sign * magnitude
}

/// Decode one E5M2 byte (bias 15, IEEE-style inf/NaN).
pub fn e5m2_to_f32(byte: u8) -> f32 {
    let sign = if byte & 0x80 != 0 { -1.0 } else { 1.0 };
    let exp = ((byte >> 2) & 0x1F) as i32;
    let mant = (byte & 0x03) as f32;
    if exp == 0x1F {
        return if (byte & 0x03) == 0 {
            sign * f32::INFINITY
        } else {
            f32::NAN
        };
    }
    let magnitude = if exp == 0 {
        (mant / 4.0) * 2f32.powi(-14)
    } else {
        (1.0 + mant / 4.0) * 2f32.powi(exp - 15)
    };
    sign * magnitude
}

/// Largest finite E4M3 value (448.0).
pub const E4M3_MAX: f32 = 448.0;
/// Largest finite E5M2 value (57344.0).
pub const E5M2_MAX: f32 = 57344.0;

fn table(e5: bool) -> &'static [(f32, u8)] {
    static E4: OnceLock<Vec<(f32, u8)>> = OnceLock::new();
    static E5: OnceLock<Vec<(f32, u8)>> = OnceLock::new();
    if e5 {
        E5.get_or_init(|| build_table(true))
    } else {
        E4.get_or_init(|| build_table(false))
    }
}

fn build_table(e5: bool) -> Vec<(f32, u8)> {
    let mut rows: Vec<(f32, u8)> = (0u16..128)
        .map(|code| {
            let byte = code as u8;
            let value = if e5 {
                e5m2_to_f32(byte)
            } else {
                e4m3_to_f32(byte)
            };
            (value, byte)
        })
        .filter(|(v, _)| v.is_finite() && *v >= 0.0)
        .collect();
    rows.sort_by(|a, b| a.0.partial_cmp(&b.0).unwrap_or(std::cmp::Ordering::Equal));
    rows.dedup_by(|a, b| a.0 == b.0);
    rows
}

fn encode_with(value: f32, e5: bool) -> u8 {
    let sign: u8 = if value.is_sign_negative() { 0x80 } else { 0x00 };
    if value.is_nan() {
        return 0x7F;
    }
    let a = value.abs();
    if a == 0.0 {
        return sign;
    }
    let max = if e5 { E5M2_MAX } else { E4M3_MAX };
    if a >= max {
        let (v, code) = *table(e5).last().expect("fp8 table is never empty");
        debug_assert_eq!(v, max);
        return sign | code;
    }
    let rows = table(e5);
    // Binary search for the insertion point, then pick the nearer neighbour.
    let idx = rows.partition_point(|(v, _)| *v < a);
    let (lo, hi) = if idx == 0 {
        (rows[0], rows[0])
    } else if idx >= rows.len() {
        (rows[rows.len() - 1], rows[rows.len() - 1])
    } else {
        (rows[idx - 1], rows[idx])
    };
    let d_lo = a - lo.0;
    let d_hi = hi.0 - a;
    let chosen = if d_hi < d_lo {
        hi
    } else if d_lo < d_hi {
        lo
    } else {
        // Tie: round to even mantissa (lowest significant bit 0).
        if lo.1 & 1 == 0 {
            lo
        } else {
            hi
        }
    };
    sign | chosen.1
}

/// Encode f32 to E4M3 with round-to-nearest-even and saturation.
pub fn f32_to_e4m3(value: f32) -> u8 {
    encode_with(value, false)
}

/// Encode f32 to E5M2 with round-to-nearest-even and saturation.
pub fn f32_to_e5m2(value: f32) -> u8 {
    encode_with(value, true)
}

/// Quantise a slice to E4M3 bytes.
pub fn encode_e4m3(values: &[f32]) -> Vec<u8> {
    values.iter().map(|v| f32_to_e4m3(*v)).collect()
}

/// Dequantise E4M3 bytes to f32.
pub fn decode_e4m3(bytes: &[u8]) -> Vec<f32> {
    bytes.iter().map(|b| e4m3_to_f32(*b)).collect()
}

/// Quantise a slice to E5M2 bytes.
pub fn encode_e5m2(values: &[f32]) -> Vec<u8> {
    values.iter().map(|v| f32_to_e5m2(*v)).collect()
}

/// Dequantise E5M2 bytes to f32.
pub fn decode_e5m2(bytes: &[u8]) -> Vec<f32> {
    bytes.iter().map(|b| e5m2_to_f32(*b)).collect()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn e4m3_known_values() {
        assert_eq!(e4m3_to_f32(0x00), 0.0);
        assert_eq!(e4m3_to_f32(0x38), 1.0); // exp 7, mant 0
        assert_eq!(e4m3_to_f32(0x3C), 1.5);
        assert_eq!(e4m3_to_f32(0x7E), 448.0);
        assert!(e4m3_to_f32(0x7F).is_nan());
        assert_eq!(e4m3_to_f32(0x80), -0.0);
        assert_eq!(e4m3_to_f32(0x01), 2f32.powi(-9)); // smallest subnormal
    }

    #[test]
    fn e5m2_known_values() {
        assert_eq!(e5m2_to_f32(0x3C), 1.0);
        assert_eq!(e5m2_to_f32(0x7C), f32::INFINITY);
        assert!(e5m2_to_f32(0x7D).is_nan());
        assert_eq!(e5m2_to_f32(0x7B), 57344.0);
        assert_eq!(e5m2_to_f32(0x01), 2f32.powi(-16));
    }

    #[test]
    fn round_trip_is_exact_on_representable_values() {
        for code in 0u16..256 {
            let byte = code as u8;
            let v = e4m3_to_f32(byte);
            if v.is_nan() {
                assert!(f32_to_e4m3(v) & 0x7F == 0x7F);
            } else {
                assert_eq!(f32_to_e4m3(v), byte, "e4m3 code {byte:#04x}");
            }
        }
    }

    #[test]
    fn saturation_not_infinity() {
        assert_eq!(f32_to_e4m3(1e9), 0x7E);
        assert_eq!(f32_to_e4m3(-1e9), 0xFE);
        assert_eq!(f32_to_e5m2(1e9), 0x7B);
    }

    #[test]
    fn ties_round_to_even() {
        // 1.0 (0x38) and 1.125 (0x39) are neighbours; 1.0625 is the midpoint.
        assert_eq!(f32_to_e4m3(1.0625), 0x38);
        // 1.125 and 1.25 -> midpoint 1.1875 must pick the even code 0x3A.
        assert_eq!(f32_to_e4m3(1.1875), 0x3A);
    }

    #[test]
    fn encode_decode_preserves_sign_and_range() {
        let values = [0.0, -0.0, 1.0, -2.5, 0.125, -448.0, 448.0];
        let bytes = encode_e4m3(&values);
        let back = decode_e4m3(&bytes);
        for (a, b) in values.iter().zip(back.iter()) {
            assert!((a - b).abs() <= 0.0, "{a} -> {b}");
        }
    }
}
