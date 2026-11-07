//! A minimal typed tensor. Storage is bytes plus a dtype; conversions to and
//! from `f32` go through the reference codecs so tests compare like with like.

use crate::dtype::DType;
use crate::fp8;
use crate::quant::{dequantize_i4, unpack_i4};

#[derive(Debug, Clone, PartialEq)]
pub struct Tensor {
    pub dtype: DType,
    pub shape: Vec<usize>,
    pub data: Vec<u8>,
}

impl Tensor {
    pub fn new(dtype: DType, shape: Vec<usize>, data: Vec<u8>) -> Self {
        Self { dtype, shape, data }
    }

    pub fn len(&self) -> usize {
        self.shape.iter().product()
    }

    pub fn is_empty(&self) -> bool {
        self.len() == 0
    }

    /// f32 tensor (the common case for reference work).
    pub fn from_f32(shape: Vec<usize>, values: &[f32]) -> Self {
        let expected: usize = shape.iter().product();
        assert_eq!(expected, values.len(), "shape does not match data length");
        let mut data = Vec::with_capacity(values.len() * 4);
        for v in values {
            data.extend_from_slice(&v.to_le_bytes());
        }
        Self {
            dtype: DType::F32,
            shape,
            data,
        }
    }

    pub fn from_f16_bits(shape: Vec<usize>, values: &[f32]) -> Self {
        let mut data = Vec::with_capacity(values.len() * 2);
        for v in values {
            data.extend_from_slice(&f32_to_f16_bits(*v).to_le_bytes());
        }
        Self {
            dtype: DType::F16,
            shape,
            data,
        }
    }

    pub fn from_i8(shape: Vec<usize>, values: &[i8]) -> Self {
        Self {
            dtype: DType::I8,
            shape,
            data: values.iter().map(|v| *v as u8).collect(),
        }
    }

    /// Decode to f32 using the reference codecs.
    pub fn to_f32(&self) -> Vec<f32> {
        match self.dtype {
            DType::F32 | DType::Tf32 => self
                .data
                .chunks_exact(4)
                .map(|c| f32::from_le_bytes([c[0], c[1], c[2], c[3]]))
                .collect(),
            DType::F64 => self
                .data
                .chunks_exact(8)
                .map(|c| {
                    f64::from_le_bytes([c[0], c[1], c[2], c[3], c[4], c[5], c[6], c[7]]) as f32
                })
                .collect(),
            DType::F16 => self
                .data
                .chunks_exact(2)
                .map(|c| f16_bits_to_f32(u16::from_le_bytes([c[0], c[1]])))
                .collect(),
            DType::Bf16 => self
                .data
                .chunks_exact(2)
                .map(|c| f32::from_bits((u16::from_le_bytes([c[0], c[1]]) as u32) << 16))
                .collect(),
            DType::Fp8E4M3 => fp8::decode_e4m3(&self.data),
            DType::Fp8E5M2 => fp8::decode_e5m2(&self.data),
            DType::I8 => self.data.iter().map(|b| *b as i8 as f32).collect(),
            DType::I4 => unpack_i4(&self.data, self.len())
                .into_iter()
                .map(|v| v as f32)
                .collect(),
        }
    }

    /// Decode an int4 tensor with an explicit scale (int4 storage carries none).
    pub fn to_f32_scaled(&self, scale: f32) -> Vec<f32> {
        match self.dtype {
            DType::I4 => dequantize_i4(&self.data, scale, self.len()),
            DType::I8 => self.data.iter().map(|b| *b as i8 as f32 * scale).collect(),
            _ => self.to_f32(),
        }
    }
}

/// IEEE-754 binary16 encoding, round-to-nearest-even.
pub fn f32_to_f16_bits(value: f32) -> u16 {
    let bits = value.to_bits();
    let sign = ((bits >> 16) & 0x8000) as u16;
    let mut exp = ((bits >> 23) & 0xFF) as i32;
    let mant = bits & 0x007F_FFFF;

    if exp == 0xFF {
        // Inf or NaN.
        let payload = if mant == 0 { 0 } else { 0x200 };
        return sign | 0x7C00 | payload;
    }
    let unbiased = exp - 127;
    if unbiased > 15 {
        return sign | 0x7C00; // overflow -> inf
    }
    if unbiased < -24 {
        return sign; // underflow -> zero
    }
    if unbiased < -14 {
        // Subnormal half: shift the implicit 1 into place.
        let shift = (-14 - unbiased) as u32;
        let rounded = round_shift(mant | 0x0080_0000, 13 + shift);
        return sign | rounded as u16;
    }
    exp = unbiased + 15;
    let half_mant = round_shift(mant, 13);
    if half_mant == 0x400 {
        // Mantissa overflow carries into the exponent.
        let e = exp + 1;
        if e >= 0x1F {
            return sign | 0x7C00;
        }
        return sign | ((e as u16) << 10);
    }
    sign | ((exp as u16) << 10) | half_mant as u16
}

/// Round `value >> shift` to nearest, ties to even.
fn round_shift(value: u32, shift: u32) -> u32 {
    if shift == 0 {
        return value;
    }
    let lsb = (value >> shift) & 1;
    let mask = (1u32 << shift) - 1;
    let rem = value & mask;
    let half = 1u32 << (shift - 1);
    (value >> shift) + u32::from(rem > half || (rem == half && lsb == 1))
}

/// IEEE-754 binary16 decoding (exact).
pub fn f16_bits_to_f32(bits: u16) -> f32 {
    let sign = if bits & 0x8000 != 0 { -1.0f32 } else { 1.0 };
    let exp = ((bits >> 10) & 0x1F) as i32;
    let mant = (bits & 0x03FF) as f32;
    let magnitude = if exp == 0 {
        (mant / 1024.0) * 2f32.powi(-14)
    } else if exp == 0x1F {
        if mant == 0.0 {
            return sign * f32::INFINITY;
        }
        return f32::NAN;
    } else {
        (1.0 + mant / 1024.0) * 2f32.powi(exp - 15)
    };
    sign * magnitude
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn f16_round_trip_on_exact_values() {
        for v in [0.0f32, 1.0, -1.0, 0.5, 2.0, 65504.0, 2f32.powi(-14)] {
            let back = f16_bits_to_f32(f32_to_f16_bits(v));
            assert_eq!(back, v, "value {v}");
        }
    }

    #[test]
    fn f16_overflows_to_infinity() {
        assert!(f16_bits_to_f32(f32_to_f16_bits(1e9)).is_infinite());
        assert!(f16_bits_to_f32(f32_to_f16_bits(-1e9)).is_infinite());
    }

    #[test]
    fn f16_nan_stays_nan() {
        assert!(f16_bits_to_f32(f32_to_f16_bits(f32::NAN)).is_nan());
    }

    #[test]
    fn f16_ties_to_even() {
        // 2049 is the midpoint between 2048 and 2050 in f16 (spacing 2 at 2^11).
        assert_eq!(f32_to_f16_bits(2049.0), f32_to_f16_bits(2048.0));
        // 2051 rounds up to 2052 (even mantissa).
        assert_eq!(f16_bits_to_f32(f32_to_f16_bits(2051.0)), 2052.0);
    }

    #[test]
    fn tensor_round_trips_f32_and_f16() {
        let t = Tensor::from_f32(vec![2, 2], &[1.0, 2.0, 3.0, 4.0]);
        assert_eq!(t.to_f32(), vec![1.0, 2.0, 3.0, 4.0]);
        let h = Tensor::from_f16_bits(vec![3], &[1.0, -2.0, 0.25]);
        assert_eq!(h.to_f32(), vec![1.0, -2.0, 0.25]);
    }

    #[test]
    fn i8_tensor_decodes_signed() {
        let t = Tensor::from_i8(vec![3], &[-128, 0, 127]);
        assert_eq!(t.to_f32(), vec![-128.0, 0.0, 127.0]);
    }
}
