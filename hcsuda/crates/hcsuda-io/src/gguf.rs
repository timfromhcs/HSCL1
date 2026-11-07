//! GGUF v2/v3 header reader (metadata and tensor table, no tensor data).
//!
//! Format: `GGUF` magic, u32 version, u64 tensor count, u64 key/value count,
//! the key/value pairs, the tensor infos, padding to `general.alignment`
//! (default 32), then the tensor data. All integers are little endian.
//!
//! Every length read from the file is checked against the number of bytes that
//! remain, and counts have fixed ceilings, so a crafted file cannot trigger a
//! large allocation or a loop that outlives the file.

use std::io::{Read, Seek, SeekFrom};
use std::path::Path;

use serde::Serialize;

const MAGIC: [u8; 4] = *b"GGUF";
const DEFAULT_ALIGNMENT: u64 = 32;
const MAX_TENSORS: u64 = 1 << 20;
const MAX_KV: u64 = 1 << 20;
const MAX_DIMS: u32 = 8;
/// Stored (not skipped) string values and keys may not exceed this.
const MAX_STRING: u64 = 16 << 20;
const MAX_ARRAY_DEPTH: u32 = 2;

#[derive(Debug, thiserror::Error, PartialEq, Eq)]
pub enum GgufError {
    #[error("not a GGUF file (bad magic)")]
    BadMagic,
    #[error("unsupported GGUF version {0} (supported: 2, 3)")]
    UnsupportedVersion(u32),
    #[error("file ends inside the header (needed {needed} more bytes at offset {at})")]
    Truncated { at: u64, needed: u64 },
    #[error("{what} count {count} exceeds the limit {limit}")]
    TooMany {
        what: &'static str,
        count: u64,
        limit: u64,
    },
    #[error("string of {len} bytes at offset {at} exceeds the limit or the file")]
    BadString { at: u64, len: u64 },
    #[error("unknown metadata value type {0}")]
    BadValueType(u32),
    #[error("array nesting deeper than {MAX_ARRAY_DEPTH}")]
    ArrayTooDeep,
    #[error("tensor '{name}': {why}")]
    BadTensor { name: String, why: String },
    #[error("general.alignment {0} is not a power of two in 1..=65536")]
    BadAlignment(u64),
    #[error("i/o error: {0}")]
    Io(String),
}

impl From<std::io::Error> for GgufError {
    fn from(e: std::io::Error) -> Self {
        GgufError::Io(e.to_string())
    }
}

/// A metadata value. Arrays are summarised, not materialised: vocabularies run
/// to hundreds of thousands of entries and the loader does not need them here.
#[derive(Debug, Clone, PartialEq, Serialize)]
#[serde(tag = "type", content = "value", rename_all = "snake_case")]
pub enum MetaValue {
    U8(u8),
    I8(i8),
    U16(u16),
    I16(i16),
    U32(u32),
    I32(i32),
    U64(u64),
    I64(i64),
    F32(f32),
    F64(f64),
    Bool(bool),
    Str(String),
    Array { elem_type: u32, len: u64 },
}

impl MetaValue {
    pub fn as_u64(&self) -> Option<u64> {
        match self {
            MetaValue::U8(v) => Some(*v as u64),
            MetaValue::U16(v) => Some(*v as u64),
            MetaValue::U32(v) => Some(*v as u64),
            MetaValue::U64(v) => Some(*v),
            MetaValue::I8(v) if *v >= 0 => Some(*v as u64),
            MetaValue::I16(v) if *v >= 0 => Some(*v as u64),
            MetaValue::I32(v) if *v >= 0 => Some(*v as u64),
            MetaValue::I64(v) if *v >= 0 => Some(*v as u64),
            _ => None,
        }
    }

    pub fn as_str(&self) -> Option<&str> {
        match self {
            MetaValue::Str(s) => Some(s),
            _ => None,
        }
    }
}

/// ggml tensor element types this reader knows the size of. Anything else is
/// kept as `Unknown(id)` so a file with a vendor-specific type still lists.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize)]
#[serde(rename_all = "snake_case")]
#[allow(non_camel_case_types)] // ggml's own names: Q4_0, Q8_0, ...
pub enum GgmlType {
    F32,
    F16,
    Q4_0,
    Q4_1,
    Q5_0,
    Q5_1,
    Q8_0,
    Q8_1,
    Q2K,
    Q3K,
    Q4K,
    Q5K,
    Q6K,
    Q8K,
    I8,
    I16,
    I32,
    I64,
    F64,
    Bf16,
    Unknown(u32),
}

impl GgmlType {
    pub fn from_id(id: u32) -> Self {
        match id {
            0 => Self::F32,
            1 => Self::F16,
            2 => Self::Q4_0,
            3 => Self::Q4_1,
            6 => Self::Q5_0,
            7 => Self::Q5_1,
            8 => Self::Q8_0,
            9 => Self::Q8_1,
            10 => Self::Q2K,
            11 => Self::Q3K,
            12 => Self::Q4K,
            13 => Self::Q5K,
            14 => Self::Q6K,
            15 => Self::Q8K,
            24 => Self::I8,
            25 => Self::I16,
            26 => Self::I32,
            27 => Self::I64,
            28 => Self::F64,
            30 => Self::Bf16,
            other => Self::Unknown(other),
        }
    }

    /// `(elements per block, bytes per block)`, or `None` for an unknown type.
    pub fn block(self) -> Option<(u64, u64)> {
        Some(match self {
            Self::F32 => (1, 4),
            Self::F16 | Self::Bf16 | Self::I16 => (1, 2),
            Self::F64 | Self::I64 => (1, 8),
            Self::I8 => (1, 1),
            Self::I32 => (1, 4),
            Self::Q4_0 => (32, 18),
            Self::Q4_1 => (32, 20),
            Self::Q5_0 => (32, 22),
            Self::Q5_1 => (32, 24),
            Self::Q8_0 => (32, 34),
            Self::Q8_1 => (32, 36),
            Self::Q2K => (256, 84),
            Self::Q3K => (256, 110),
            Self::Q4K => (256, 144),
            Self::Q5K => (256, 176),
            Self::Q6K => (256, 210),
            Self::Q8K => (256, 292),
            Self::Unknown(_) => return None,
        })
    }
}

#[derive(Debug, Clone, PartialEq, Serialize)]
pub struct TensorInfo {
    pub name: String,
    pub dims: Vec<u64>,
    pub ggml_type: GgmlType,
    /// Offset from the start of the tensor data section.
    pub offset: u64,
    pub n_elements: u64,
    /// `None` when the element type is not known to this reader.
    pub n_bytes: Option<u64>,
}

#[derive(Debug, Clone, PartialEq, Serialize)]
pub struct GgufFile {
    pub version: u32,
    pub alignment: u64,
    pub metadata: Vec<(String, MetaValue)>,
    pub tensors: Vec<TensorInfo>,
    /// Absolute file offset where tensor data starts.
    pub data_offset: u64,
    pub file_len: u64,
}

impl GgufFile {
    pub fn open(path: &Path) -> Result<Self, GgufError> {
        let mut f = std::fs::File::open(path)?;
        let len = f.metadata()?.len();
        let mut buffered = std::io::BufReader::with_capacity(1 << 16, &mut f);
        Self::parse(&mut buffered, len)
    }

    pub fn tensor(&self, name: &str) -> Option<&TensorInfo> {
        self.tensors.iter().find(|t| t.name == name)
    }

    /// Read the raw bytes of one tensor. The size comes from the already
    /// validated table, and `max_bytes` bounds the allocation.
    pub fn read_tensor_bytes(
        &self,
        path: &Path,
        t: &TensorInfo,
        max_bytes: u64,
    ) -> Result<Vec<u8>, GgufError> {
        let n = t
            .n_bytes
            .ok_or_else(|| bad_tensor(&t.name, "element type has no known size".into()))?;
        if n > max_bytes {
            return Err(bad_tensor(
                &t.name,
                format!("{n} bytes exceeds the read limit {max_bytes}"),
            ));
        }
        let start = self
            .data_offset
            .checked_add(t.offset)
            .filter(|s| s.checked_add(n).is_some_and(|e| e <= self.file_len))
            .ok_or_else(|| bad_tensor(&t.name, "data lies outside the file".into()))?;
        let mut f = std::fs::File::open(path)?;
        if f.metadata()?.len() != self.file_len {
            return Err(GgufError::Io(
                "file changed size since the header was read".into(),
            ));
        }
        f.seek(SeekFrom::Start(start))?;
        let mut buf = vec![0u8; n as usize];
        f.read_exact(&mut buf)?;
        Ok(buf)
    }

    pub fn meta(&self, key: &str) -> Option<&MetaValue> {
        self.metadata.iter().find(|(k, _)| k == key).map(|(_, v)| v)
    }

    /// Total bytes of all tensors whose size is known.
    pub fn known_tensor_bytes(&self) -> u64 {
        self.tensors.iter().filter_map(|t| t.n_bytes).sum()
    }

    pub fn parse<R: Read + Seek>(r: &mut R, file_len: u64) -> Result<Self, GgufError> {
        let mut rd = Reader {
            r,
            pos: 0,
            len: file_len,
        };
        let magic = rd.bytes(4)?;
        if magic != MAGIC {
            return Err(GgufError::BadMagic);
        }
        let version = rd.u32()?;
        if !(2..=3).contains(&version) {
            return Err(GgufError::UnsupportedVersion(version));
        }
        let n_tensors = rd.u64()?;
        let n_kv = rd.u64()?;
        if n_tensors > MAX_TENSORS {
            return Err(GgufError::TooMany {
                what: "tensor",
                count: n_tensors,
                limit: MAX_TENSORS,
            });
        }
        if n_kv > MAX_KV {
            return Err(GgufError::TooMany {
                what: "metadata",
                count: n_kv,
                limit: MAX_KV,
            });
        }

        let mut metadata = Vec::new();
        for _ in 0..n_kv {
            let key = rd.string()?;
            let ty = rd.u32()?;
            let value = rd.value(ty, 0)?;
            metadata.push((key, value));
        }

        let alignment = metadata
            .iter()
            .find(|(k, _)| k == "general.alignment")
            .and_then(|(_, v)| v.as_u64())
            .unwrap_or(DEFAULT_ALIGNMENT);
        if alignment == 0 || alignment > 65536 || !alignment.is_power_of_two() {
            return Err(GgufError::BadAlignment(alignment));
        }

        let mut tensors = Vec::new();
        for _ in 0..n_tensors {
            let name = rd.string()?;
            let n_dims = rd.u32()?;
            if n_dims == 0 || n_dims > MAX_DIMS {
                return Err(bad_tensor(&name, format!("{n_dims} dimensions")));
            }
            let mut dims = Vec::with_capacity(n_dims as usize);
            let mut n_elements: u64 = 1;
            for _ in 0..n_dims {
                let d = rd.u64()?;
                n_elements = n_elements
                    .checked_mul(d)
                    .ok_or_else(|| bad_tensor(&name, "element count overflows u64".into()))?;
                dims.push(d);
            }
            let ggml_type = GgmlType::from_id(rd.u32()?);
            let offset = rd.u64()?;
            let n_bytes = match ggml_type.block() {
                Some((block, bytes)) => {
                    if n_elements % block != 0 {
                        return Err(bad_tensor(
                            &name,
                            format!(
                                "{n_elements} elements is not a multiple of block size {block}"
                            ),
                        ));
                    }
                    Some(
                        (n_elements / block)
                            .checked_mul(bytes)
                            .ok_or_else(|| bad_tensor(&name, "byte size overflows u64".into()))?,
                    )
                }
                None => None,
            };
            if offset % alignment != 0 {
                return Err(bad_tensor(
                    &name,
                    format!("offset {offset} is not a multiple of the alignment {alignment}"),
                ));
            }
            tensors.push(TensorInfo {
                name,
                dims,
                ggml_type,
                offset,
                n_elements,
                n_bytes,
            });
        }

        let header_end = rd.pos;
        let data_offset = header_end.div_ceil(alignment) * alignment;
        let data_len = file_len.saturating_sub(data_offset);
        for t in &tensors {
            if let Some(n) = t.n_bytes {
                let end = t.offset.checked_add(n);
                if end.map_or(true, |e| e > data_len) {
                    return Err(bad_tensor(
                        &t.name,
                        format!(
                            "data [{}, +{}) lies outside the {} data bytes of the file",
                            t.offset, n, data_len
                        ),
                    ));
                }
            }
        }

        Ok(GgufFile {
            version,
            alignment,
            metadata,
            tensors,
            data_offset,
            file_len,
        })
    }
}

fn bad_tensor(name: &str, why: String) -> GgufError {
    GgufError::BadTensor {
        name: name.to_string(),
        why,
    }
}

struct Reader<'a, R: Read + Seek> {
    r: &'a mut R,
    pos: u64,
    len: u64,
}

impl<R: Read + Seek> Reader<'_, R> {
    fn remaining(&self) -> u64 {
        self.len.saturating_sub(self.pos)
    }

    fn need(&self, n: u64) -> Result<(), GgufError> {
        if n > self.remaining() {
            Err(GgufError::Truncated {
                at: self.pos,
                needed: n - self.remaining(),
            })
        } else {
            Ok(())
        }
    }

    fn bytes(&mut self, n: u64) -> Result<Vec<u8>, GgufError> {
        self.need(n)?;
        let mut buf = vec![0u8; n as usize];
        self.r.read_exact(&mut buf)?;
        self.pos += n;
        Ok(buf)
    }

    fn skip(&mut self, n: u64) -> Result<(), GgufError> {
        self.need(n)?;
        self.r.seek(SeekFrom::Current(n as i64))?;
        self.pos += n;
        Ok(())
    }

    fn array<const N: usize>(&mut self) -> Result<[u8; N], GgufError> {
        self.need(N as u64)?;
        let mut b = [0u8; N];
        self.r.read_exact(&mut b)?;
        self.pos += N as u64;
        Ok(b)
    }

    fn u32(&mut self) -> Result<u32, GgufError> {
        Ok(u32::from_le_bytes(self.array()?))
    }

    fn u64(&mut self) -> Result<u64, GgufError> {
        Ok(u64::from_le_bytes(self.array()?))
    }

    fn string(&mut self) -> Result<String, GgufError> {
        let at = self.pos;
        let len = self.u64()?;
        if len > MAX_STRING || len > self.remaining() {
            return Err(GgufError::BadString { at, len });
        }
        let raw = self.bytes(len)?;
        Ok(String::from_utf8_lossy(&raw).into_owned())
    }

    /// Advance past one string without keeping it.
    fn skip_string(&mut self) -> Result<(), GgufError> {
        let at = self.pos;
        let len = self.u64()?;
        if len > self.remaining() {
            return Err(GgufError::BadString { at, len });
        }
        self.skip(len)
    }

    fn value(&mut self, ty: u32, depth: u32) -> Result<MetaValue, GgufError> {
        Ok(match ty {
            0 => MetaValue::U8(u8::from_le_bytes(self.array()?)),
            1 => MetaValue::I8(i8::from_le_bytes(self.array()?)),
            2 => MetaValue::U16(u16::from_le_bytes(self.array()?)),
            3 => MetaValue::I16(i16::from_le_bytes(self.array()?)),
            4 => MetaValue::U32(self.u32()?),
            5 => MetaValue::I32(i32::from_le_bytes(self.array()?)),
            6 => MetaValue::F32(f32::from_le_bytes(self.array()?)),
            7 => MetaValue::Bool(u8::from_le_bytes(self.array()?) != 0),
            8 => MetaValue::Str(self.string()?),
            9 => {
                if depth >= MAX_ARRAY_DEPTH {
                    return Err(GgufError::ArrayTooDeep);
                }
                let elem = self.u32()?;
                let n = self.u64()?;
                self.skip_array(elem, n, depth)?;
                MetaValue::Array {
                    elem_type: elem,
                    len: n,
                }
            }
            10 => MetaValue::U64(self.u64()?),
            11 => MetaValue::I64(i64::from_le_bytes(self.array()?)),
            12 => MetaValue::F64(f64::from_le_bytes(self.array()?)),
            other => return Err(GgufError::BadValueType(other)),
        })
    }

    fn skip_array(&mut self, elem: u32, n: u64, depth: u32) -> Result<(), GgufError> {
        let fixed = match elem {
            0 | 1 | 7 => Some(1u64),
            2 | 3 => Some(2),
            4..=6 => Some(4),
            10..=12 => Some(8),
            _ => None,
        };
        if let Some(size) = fixed {
            let total = n.checked_mul(size).ok_or(GgufError::TooMany {
                what: "array element",
                count: n,
                limit: u64::MAX / size,
            })?;
            return self.skip(total);
        }
        match elem {
            8 => {
                // Every string needs at least its 8-byte length prefix.
                if n.checked_mul(8).map_or(true, |b| b > self.remaining()) {
                    return Err(GgufError::Truncated {
                        at: self.pos,
                        needed: n.saturating_mul(8).saturating_sub(self.remaining()),
                    });
                }
                for _ in 0..n {
                    self.skip_string()?;
                }
                Ok(())
            }
            9 => {
                if depth + 1 >= MAX_ARRAY_DEPTH {
                    return Err(GgufError::ArrayTooDeep);
                }
                // Each nested array needs at least a 12-byte header.
                if n.checked_mul(12).map_or(true, |b| b > self.remaining()) {
                    return Err(GgufError::Truncated {
                        at: self.pos,
                        needed: 1,
                    });
                }
                for _ in 0..n {
                    let inner = self.u32()?;
                    let m = self.u64()?;
                    self.skip_array(inner, m, depth + 1)?;
                }
                Ok(())
            }
            other => Err(GgufError::BadValueType(other)),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::io::Cursor;

    /// Builds GGUF bytes for tests.
    struct B(Vec<u8>);

    impl B {
        fn new(version: u32, n_tensors: u64, n_kv: u64) -> Self {
            let mut v = MAGIC.to_vec();
            v.extend(version.to_le_bytes());
            v.extend(n_tensors.to_le_bytes());
            v.extend(n_kv.to_le_bytes());
            B(v)
        }
        fn s(mut self, s: &str) -> Self {
            self.0.extend((s.len() as u64).to_le_bytes());
            self.0.extend(s.as_bytes());
            self
        }
        fn u32(mut self, v: u32) -> Self {
            self.0.extend(v.to_le_bytes());
            self
        }
        fn u64(mut self, v: u64) -> Self {
            self.0.extend(v.to_le_bytes());
            self
        }
        fn raw(mut self, b: &[u8]) -> Self {
            self.0.extend(b);
            self
        }
        /// Pad to `align` and append `data_len` zero bytes.
        fn data(mut self, align: usize, data_len: usize) -> Self {
            while self.0.len() % align != 0 {
                self.0.push(0);
            }
            self.0.extend(vec![0u8; data_len]);
            self
        }
        fn parse(&self) -> Result<GgufFile, GgufError> {
            GgufFile::parse(&mut Cursor::new(&self.0), self.0.len() as u64)
        }
    }

    fn one_tensor_file() -> B {
        B::new(3, 1, 2)
            .s("general.architecture")
            .u32(8)
            .s("llama")
            .s("general.name")
            .u32(8)
            .s("tiny")
            .s("w")
            .u32(2)
            .u64(64)
            .u64(2)
            .u32(0) // f32
            .u64(0)
            .data(32, 64 * 2 * 4)
    }

    #[test]
    fn parses_metadata_and_tensor_table() {
        let f = one_tensor_file().parse().unwrap();
        assert_eq!(f.version, 3);
        assert_eq!(
            f.meta("general.architecture").unwrap().as_str(),
            Some("llama")
        );
        assert_eq!(f.tensors.len(), 1);
        let t = &f.tensors[0];
        assert_eq!((t.name.as_str(), t.dims.clone()), ("w", vec![64, 2]));
        assert_eq!(t.ggml_type, GgmlType::F32);
        assert_eq!(t.n_bytes, Some(512));
        assert_eq!(f.data_offset % 32, 0);
        assert_eq!(f.known_tensor_bytes(), 512);
    }

    #[test]
    fn quantised_size_uses_blocks() {
        // 4096 elements of Q4_K = 16 blocks of 144 bytes.
        let f = B::new(3, 1, 0)
            .s("q")
            .u32(1)
            .u64(4096)
            .u32(12)
            .u64(0)
            .data(32, 16 * 144)
            .parse()
            .unwrap();
        assert_eq!(f.tensors[0].n_bytes, Some(2304));
    }

    #[test]
    fn unknown_tensor_type_lists_without_a_size() {
        let f = B::new(3, 1, 0)
            .s("x")
            .u32(1)
            .u64(8)
            .u32(9999)
            .u64(0)
            .data(32, 0)
            .parse()
            .unwrap();
        assert_eq!(f.tensors[0].ggml_type, GgmlType::Unknown(9999));
        assert_eq!(f.tensors[0].n_bytes, None);
    }

    #[test]
    fn arrays_are_skipped_not_materialised() {
        let f = B::new(3, 0, 2)
            .s("a")
            .u32(9)
            .u32(4)
            .u64(3)
            .u32(1)
            .u32(2)
            .u32(3)
            .s("tokens")
            .u32(9)
            .u32(8)
            .u64(2)
            .s("ab")
            .s("c")
            .parse()
            .unwrap();
        assert_eq!(
            f.metadata[0].1,
            MetaValue::Array {
                elem_type: 4,
                len: 3
            }
        );
        assert_eq!(
            f.metadata[1].1,
            MetaValue::Array {
                elem_type: 8,
                len: 2
            }
        );
    }

    #[test]
    fn rejects_bad_magic_and_versions() {
        let mut b = one_tensor_file();
        b.0[0] = b'X';
        assert_eq!(b.parse().unwrap_err(), GgufError::BadMagic);
        assert_eq!(
            B::new(1, 0, 0).parse().unwrap_err(),
            GgufError::UnsupportedVersion(1)
        );
        assert_eq!(
            B::new(4, 0, 0).parse().unwrap_err(),
            GgufError::UnsupportedVersion(4)
        );
    }

    #[test]
    fn rejects_huge_counts_before_allocating() {
        assert!(matches!(
            B::new(3, u64::MAX, 0).parse().unwrap_err(),
            GgufError::TooMany { what: "tensor", .. }
        ));
        assert!(matches!(
            B::new(3, 0, u64::MAX).parse().unwrap_err(),
            GgufError::TooMany {
                what: "metadata",
                ..
            }
        ));
    }

    #[test]
    fn rejects_string_longer_than_the_file() {
        let b = B::new(3, 0, 1).u64(u64::MAX - 1).raw(b"abc");
        assert!(matches!(
            b.parse().unwrap_err(),
            GgufError::BadString { .. }
        ));
    }

    #[test]
    fn rejects_array_count_larger_than_the_file() {
        let b = B::new(3, 0, 1).s("a").u32(9).u32(4).u64(u64::MAX);
        assert!(b.parse().is_err());
        let strings = B::new(3, 0, 1).s("a").u32(9).u32(8).u64(1 << 40);
        assert!(strings.parse().is_err());
    }

    #[test]
    fn rejects_deeply_nested_arrays() {
        // array of array of array
        let b = B::new(3, 0, 1)
            .s("a")
            .u32(9)
            .u32(9)
            .u64(1)
            .u32(9)
            .u64(1)
            .u32(4)
            .u64(0);
        assert_eq!(b.parse().unwrap_err(), GgufError::ArrayTooDeep);
    }

    #[test]
    fn rejects_unknown_value_type() {
        let b = B::new(3, 0, 1).s("a").u32(77);
        assert_eq!(b.parse().unwrap_err(), GgufError::BadValueType(77));
    }

    #[test]
    fn rejects_truncated_header() {
        let full = one_tensor_file().0;
        for cut in [3usize, 10, 30, 60, 100] {
            let part = &full[..cut.min(full.len())];
            assert!(GgufFile::parse(&mut Cursor::new(part), part.len() as u64).is_err());
        }
    }

    #[test]
    fn rejects_tensor_data_outside_the_file() {
        let b = B::new(3, 1, 0)
            .s("w")
            .u32(1)
            .u64(1024)
            .u32(0)
            .u64(0)
            .data(32, 100); // needs 4096 bytes
        assert!(matches!(
            b.parse().unwrap_err(),
            GgufError::BadTensor { .. }
        ));
    }

    #[test]
    fn rejects_overflowing_dimensions_and_bad_block_multiples() {
        let overflow = B::new(3, 1, 0)
            .s("w")
            .u32(2)
            .u64(u64::MAX)
            .u64(2)
            .u32(0)
            .u64(0);
        assert!(matches!(
            overflow.parse().unwrap_err(),
            GgufError::BadTensor { .. }
        ));
        let ragged = B::new(3, 1, 0)
            .s("w")
            .u32(1)
            .u64(33)
            .u32(2)
            .u64(0)
            .data(32, 1000);
        assert!(matches!(
            ragged.parse().unwrap_err(),
            GgufError::BadTensor { .. }
        ));
        let dims = B::new(3, 1, 0).s("w").u32(99).u64(1);
        assert!(matches!(
            dims.parse().unwrap_err(),
            GgufError::BadTensor { .. }
        ));
    }

    #[test]
    fn rejects_unaligned_offset_and_bad_alignment() {
        let off = B::new(3, 1, 0)
            .s("w")
            .u32(1)
            .u64(8)
            .u32(0)
            .u64(5)
            .data(32, 64);
        assert!(matches!(
            off.parse().unwrap_err(),
            GgufError::BadTensor { .. }
        ));
        let al = B::new(3, 0, 1).s("general.alignment").u32(4).u32(3);
        assert_eq!(al.parse().unwrap_err(), GgufError::BadAlignment(3));
    }

    fn temp_file(tag: &str, bytes: &[u8]) -> std::path::PathBuf {
        let p = std::env::temp_dir().join(format!("hcsuda-io-{}-{tag}.gguf", std::process::id()));
        std::fs::write(&p, bytes).unwrap();
        p
    }

    #[test]
    fn read_tensor_bytes_returns_the_right_slice_and_honours_the_limit() {
        // Two f32 tensors of 8 elements each; fill tensor data with its own index.
        let mut b = B::new(3, 2, 0)
            .s("a")
            .u32(1)
            .u64(8)
            .u32(0)
            .u64(0)
            .s("b")
            .u32(1)
            .u64(8)
            .u32(0)
            .u64(32);
        while b.0.len() % 32 != 0 {
            b.0.push(0);
        }
        let data_start = b.0.len();
        b.0.extend((0u8..64).collect::<Vec<u8>>());
        let path = temp_file("slice", &b.0);
        let f = GgufFile::open(&path).unwrap();
        assert_eq!(f.data_offset as usize, data_start);
        let tb = f.tensor("b").unwrap().clone();
        let got = f.read_tensor_bytes(&path, &tb, 1024).unwrap();
        assert_eq!(got, (32u8..64).collect::<Vec<u8>>());
        assert!(f.read_tensor_bytes(&path, &tb, 16).is_err());
        // The file grows after the header was read: refuse instead of trusting stale offsets.
        std::fs::write(&path, [b.0.clone(), vec![0u8; 8]].concat()).unwrap();
        assert!(f.read_tensor_bytes(&path, &tb, 1024).is_err());
        std::fs::remove_file(&path).ok();
    }
}
