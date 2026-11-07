//! Integer quantisation: symmetric per-tensor int8 and packed int4.
//!
//! These are the formats the fast dot-product path uses on RDNA2, where
//! `VK_KHR_shader_integer_dot_product` reports accelerated 8-bit and 4x8-bit
//! packed dot products. The reference implementation here is the oracle.

/// A symmetric quantised tensor: `q = clamp(round(x / scale), qmin, qmax)`.
#[derive(Debug, Clone, PartialEq)]
pub struct QTensor {
    pub scale: f32,
    pub values: Vec<i8>,
}

impl QTensor {
    pub fn dequantize(&self) -> Vec<f32> {
        self.values.iter().map(|q| *q as f32 * self.scale).collect()
    }
}

/// Symmetric int8 quantisation over the whole slice (range -127..=127).
pub fn quantize_i8(values: &[f32]) -> QTensor {
    let max_abs = values.iter().fold(0.0f32, |m, v| m.max(v.abs()));
    let scale = if max_abs == 0.0 { 1.0 } else { max_abs / 127.0 };
    let values = values
        .iter()
        .map(|v| (v / scale).round().clamp(-127.0, 127.0) as i8)
        .collect();
    QTensor { scale, values }
}

/// Pack int8 values four per `u32` (element 0 in the low byte), the layout
/// `dotPacked4x8EXT` consumes. The slice length must be a multiple of 4.
pub fn pack_i8x4(values: &[i8]) -> Vec<u32> {
    assert!(
        values.len() % 4 == 0,
        "pack_i8x4 needs a multiple of 4 values"
    );
    values
        .chunks_exact(4)
        .map(|c| u32::from_le_bytes([c[0] as u8, c[1] as u8, c[2] as u8, c[3] as u8]))
        .collect()
}

/// Symmetric int4 quantisation (range -8..=7) packed two per byte.
/// The even element is stored in the low nibble.
pub fn quantize_i4_packed(values: &[f32]) -> (f32, Vec<u8>) {
    let max_abs = values.iter().fold(0.0f32, |m, v| m.max(v.abs()));
    let scale = if max_abs == 0.0 { 1.0 } else { max_abs / 7.0 };
    let mut packed = vec![0u8; values.len().div_ceil(2)];
    for (i, v) in values.iter().enumerate() {
        let q = (v / scale).round().clamp(-8.0, 7.0) as i8;
        let nibble = (q as u8) & 0x0F;
        if i % 2 == 0 {
            packed[i / 2] = (packed[i / 2] & 0xF0) | nibble;
        } else {
            packed[i / 2] = (packed[i / 2] & 0x0F) | (nibble << 4);
        }
    }
    (scale, packed)
}

/// Unpack int4 nibbles back to signed values.
pub fn unpack_i4(packed: &[u8], len: usize) -> Vec<i8> {
    let mut out = Vec::with_capacity(len);
    for i in 0..len {
        let byte = packed[i / 2];
        let nibble = if i % 2 == 0 { byte & 0x0F } else { byte >> 4 };
        // Sign-extend the 4-bit two's-complement value.
        let value = if nibble & 0x08 != 0 {
            (nibble as i8) - 16
        } else {
            nibble as i8
        };
        out.push(value);
    }
    out
}

/// Dequantise packed int4 back to f32.
pub fn dequantize_i4(packed: &[u8], scale: f32, len: usize) -> Vec<f32> {
    unpack_i4(packed, len)
        .into_iter()
        .map(|q| q as f32 * scale)
        .collect()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn i8_round_trip_is_within_one_step() {
        let values = [0.0, 1.0, -1.0, 0.5, -0.25, 3.75];
        let q = quantize_i8(&values);
        let back = q.dequantize();
        for (a, b) in values.iter().zip(back.iter()) {
            assert!((a - b).abs() <= q.scale * 0.5 + 1e-6, "{a} -> {b}");
        }
    }

    #[test]
    fn i8_zero_tensor_does_not_divide_by_zero() {
        let q = quantize_i8(&[0.0; 8]);
        assert_eq!(q.scale, 1.0);
        assert!(q.values.iter().all(|v| *v == 0));
    }

    #[test]
    fn i4_packs_even_in_low_nibble() {
        // max_abs = 7 -> scale 1, so the quantised values are the inputs.
        let (scale, packed) = quantize_i4_packed(&[1.0, -1.0, 7.0, -7.0]);
        assert_eq!(scale, 1.0);
        assert_eq!(packed.len(), 2);
        assert_eq!(unpack_i4(&packed, 4), vec![1, -1, 7, -7]);
        assert_eq!(packed[0], 0xF1);
        assert_eq!(packed[1], 0x97);
    }

    #[test]
    fn i4_odd_length_rounds_up() {
        // max_abs = 7 keeps scale at 1 so the assertion is about packing, not rounding.
        let (_, packed) = quantize_i4_packed(&[1.0, 2.0, 7.0]);
        assert_eq!(packed.len(), 2);
        assert_eq!(unpack_i4(&packed, 3), vec![1, 2, 7]);
    }

    #[test]
    fn i4_quantises_against_the_max_abs_scale() {
        // Symmetric int4 uses max_abs/7, so the positive extreme is 7 and the
        // negative extreme maps to -7 rather than the unused code -8.
        let (scale, packed) = quantize_i4_packed(&[1.0, -8.0]);
        assert!((scale - 8.0 / 7.0).abs() < 1e-6);
        assert_eq!(unpack_i4(&packed, 2), vec![1, -7]);
    }

    #[test]
    fn i4_dequantize_scales() {
        let back = dequantize_i4(&[0xF1], 0.5, 2);
        assert_eq!(back, vec![0.5, -0.5]);
    }

    #[test]
    fn pack_i8x4_layout_and_negative_values() {
        assert_eq!(pack_i8x4(&[1, 2, 3, 4]), vec![0x0403_0201]);
        assert_eq!(pack_i8x4(&[-1, 0, 0, -128]), vec![0x8000_00ff]);
    }
}
