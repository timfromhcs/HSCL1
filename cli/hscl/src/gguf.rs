//! GGUF metadata reader and memory-fit estimate (`hscl ai fit`).
//!
//! The format is public (ggml's GGUF specification). Only the header, key/value metadata and tensor table are read - never the weights - and every
//! count and length is bounded, because model files are untrusted input. The idea of estimating RAM/VRAM from GGUF metadata, context size and offload
//! follows gguf-parser-go (MIT, gpustack); this is an independent Rust implementation of the *reading and arithmetic*, not a copy.
//!
//! The estimate covers standard attention models. Architectures with other cache layouts (MLA, SSM/hybrid) are detected and flagged, not guessed.

use anyhow::{bail, Context, Result};
use serde::Serialize;
use std::collections::BTreeMap;
use std::io::Read;
use std::path::Path;

const MAX_KV: u64 = 100_000;
const MAX_TENSORS: u64 = 1_000_000;
const MAX_STR: u64 = 1 << 20;
const MAX_DIMS: u32 = 8;
const MAX_ARRAY: u64 = 1 << 28;
/// Fixed runtime overhead added to every estimate. A HEURISTIC, labelled as such in the report; the plan's gate compares it with real loads.
pub const OVERHEAD_MIB: u64 = 256;

#[derive(Debug, Clone, PartialEq)]
pub enum Value {
    U(u64),
    I(i64),
    F(f64),
    B(bool),
    S(String),
    /// Arrays (vocabularies, merges) are skipped; only the length is kept.
    Arr(u64),
}

#[derive(Debug, Clone)]
pub struct Tensor {
    pub name: String,
    pub dims: Vec<u64>,
    pub ggml_type: u32,
    pub offset: u64,
}

#[derive(Debug)]
pub struct Gguf {
    pub version: u32,
    pub kv: BTreeMap<String, Value>,
    pub tensors: Vec<Tensor>,
    pub data_offset: u64,
    pub file_size: u64,
}

struct Counting<R> {
    inner: R,
    pos: u64,
}

impl<R: Read> Read for Counting<R> {
    fn read(&mut self, buf: &mut [u8]) -> std::io::Result<usize> {
        let n = self.inner.read(buf)?;
        self.pos += n as u64;
        Ok(n)
    }
}

/// (elements per block, bytes per block) for ggml tensor types, from ggml's public type traits.
pub fn type_traits(t: u32) -> Option<(u64, u64)> {
    Some(match t {
        0 => (1, 4),      // F32
        1 => (1, 2),      // F16
        2 => (32, 18),    // Q4_0
        3 => (32, 20),    // Q4_1
        6 => (32, 22),    // Q5_0
        7 => (32, 24),    // Q5_1
        8 => (32, 34),    // Q8_0
        9 => (32, 36),    // Q8_1
        10 => (256, 84),  // Q2_K
        11 => (256, 110), // Q3_K
        12 => (256, 144), // Q4_K
        13 => (256, 176), // Q5_K
        14 => (256, 210), // Q6_K
        15 => (256, 292), // Q8_K
        16 => (256, 66),  // IQ2_XXS
        17 => (256, 74),  // IQ2_XS
        18 => (256, 98),  // IQ3_XXS
        19 => (256, 50),  // IQ1_S
        20 => (32, 18),   // IQ4_NL
        21 => (256, 110), // IQ3_S
        22 => (256, 82),  // IQ2_S
        23 => (256, 136), // IQ4_XS
        24 => (1, 1),     // I8
        25 => (1, 2),     // I16
        26 => (1, 4),     // I32
        27 => (1, 8),     // I64
        28 => (1, 8),     // F64
        29 => (256, 56),  // IQ1_M
        30 => (1, 2),     // BF16
        _ => return None,
    })
}

fn rd<R: Read, const N: usize>(r: &mut R) -> Result<[u8; N]> {
    let mut b = [0u8; N];
    r.read_exact(&mut b).context("unexpected end of file")?;
    Ok(b)
}
fn rd_u32<R: Read>(r: &mut R) -> Result<u32> {
    Ok(u32::from_le_bytes(rd::<_, 4>(r)?))
}
fn rd_u64<R: Read>(r: &mut R) -> Result<u64> {
    Ok(u64::from_le_bytes(rd::<_, 8>(r)?))
}

fn skip<R: Read>(r: &mut R, n: u64) -> Result<()> {
    let copied = std::io::copy(&mut r.take(n), &mut std::io::sink())?;
    if copied != n {
        bail!("unexpected end of file");
    }
    Ok(())
}

fn read_string<R: Read>(r: &mut R) -> Result<String> {
    let len = rd_u64(r)?;
    if len > MAX_STR {
        bail!("string of {len} bytes exceeds the limit");
    }
    let mut v = vec![0u8; len as usize];
    r.read_exact(&mut v).context("unexpected end of file")?;
    Ok(String::from_utf8_lossy(&v).into_owned())
}

fn elem_size(ty: u32) -> Option<u64> {
    match ty {
        0 | 1 | 7 => Some(1),
        2 | 3 => Some(2),
        4..=6 => Some(4),
        10..=12 => Some(8),
        _ => None,
    }
}

fn read_value<R: Read>(r: &mut R, ty: u32, depth: u32) -> Result<Value> {
    Ok(match ty {
        0 => Value::U(rd::<_, 1>(r)?[0] as u64),
        1 => Value::I(rd::<_, 1>(r)?[0] as i8 as i64),
        2 => Value::U(u16::from_le_bytes(rd::<_, 2>(r)?) as u64),
        3 => Value::I(i16::from_le_bytes(rd::<_, 2>(r)?) as i64),
        4 => Value::U(rd_u32(r)? as u64),
        5 => Value::I(rd_u32(r)? as i32 as i64),
        6 => Value::F(f32::from_le_bytes(rd::<_, 4>(r)?) as f64),
        7 => Value::B(rd::<_, 1>(r)?[0] != 0),
        8 => Value::S(read_string(r)?),
        9 => {
            if depth > 0 {
                bail!("nested arrays are not supported");
            }
            let et = rd_u32(r)?;
            let n = rd_u64(r)?;
            if n > MAX_ARRAY {
                bail!("array of {n} elements exceeds the limit");
            }
            if et == 8 {
                for _ in 0..n {
                    let l = rd_u64(r)?;
                    if l > MAX_STR {
                        bail!("string in array exceeds the limit");
                    }
                    skip(r, l)?;
                }
            } else {
                let sz = elem_size(et)
                    .with_context(|| format!("unsupported array element type {et}"))?;
                skip(r, n.checked_mul(sz).context("array size overflow")?)?;
            }
            Value::Arr(n)
        }
        10 => Value::U(rd_u64(r)?),
        11 => Value::I(rd_u64(r)? as i64),
        12 => Value::F(f64::from_le_bytes(rd::<_, 8>(r)?)),
        other => bail!("unknown value type {other}"),
    })
}

/// Parse header, metadata and tensor table. `file_size` is the size of the whole file (for the data-region cross-check).
pub fn parse<R: Read>(r: R, file_size: u64) -> Result<Gguf> {
    let mut r = Counting { inner: r, pos: 0 };
    if &rd::<_, 4>(&mut r)? != b"GGUF" {
        bail!("not a GGUF file (bad magic)");
    }
    let version = rd_u32(&mut r)?;
    if !(2..=3).contains(&version) {
        bail!("unsupported GGUF version {version}");
    }
    let tensor_count = rd_u64(&mut r)?;
    let kv_count = rd_u64(&mut r)?;
    if tensor_count > MAX_TENSORS || kv_count > MAX_KV {
        bail!("implausible counts (tensors {tensor_count}, metadata {kv_count})");
    }
    let mut kv = BTreeMap::new();
    for _ in 0..kv_count {
        let key = read_string(&mut r)?;
        let ty = rd_u32(&mut r)?;
        let v = read_value(&mut r, ty, 0)?;
        kv.insert(key, v);
    }
    let mut tensors = Vec::with_capacity(tensor_count.min(4096) as usize);
    for _ in 0..tensor_count {
        let name = read_string(&mut r)?;
        let nd = rd_u32(&mut r)?;
        if nd > MAX_DIMS {
            bail!("tensor with {nd} dimensions");
        }
        let mut dims = Vec::new();
        for _ in 0..nd {
            dims.push(rd_u64(&mut r)?);
        }
        let ggml_type = rd_u32(&mut r)?;
        let offset = rd_u64(&mut r)?;
        tensors.push(Tensor {
            name,
            dims,
            ggml_type,
            offset,
        });
    }
    let align = match kv.get("general.alignment") {
        Some(Value::U(a)) if *a > 0 && a.is_power_of_two() && *a <= 1 << 20 => *a,
        Some(_) => bail!("invalid general.alignment"),
        None => 32,
    };
    let data_offset = r.pos.div_ceil(align) * align;
    Ok(Gguf {
        version,
        kv,
        tensors,
        data_offset,
        file_size,
    })
}

pub fn parse_file(p: &Path) -> Result<Gguf> {
    let f = std::fs::File::open(p).with_context(|| format!("cannot open {}", p.display()))?;
    let size = f.metadata()?.len();
    parse(std::io::BufReader::new(f), size)
}

impl Tensor {
    pub fn elements(&self) -> Option<u64> {
        self.dims.iter().try_fold(1u64, |a, d| a.checked_mul(*d))
    }
    /// Bytes from ggml's type table; None for unknown types or element counts that do not fill whole blocks.
    pub fn bytes(&self) -> Option<u64> {
        let (blk, by) = type_traits(self.ggml_type)?;
        let n = self.elements()?;
        (n % blk == 0).then(|| (n / blk).checked_mul(by)).flatten()
    }
}

#[derive(Debug, Clone, Serialize)]
pub struct Summary {
    pub gguf_version: u32,
    pub architecture: String,
    pub name: Option<String>,
    pub layers: u64,
    pub embedding: u64,
    pub heads: u64,
    pub kv_heads: u64,
    pub head_dim_k: u64,
    pub head_dim_v: u64,
    pub context_train: Option<u64>,
    pub vocab: Option<u64>,
    pub experts: u64,
    pub experts_used: u64,
    pub tensors: usize,
    /// On-disk size of the data region (file size minus data offset). Exact for a complete file.
    pub weights_bytes: u64,
    /// Sum from ggml's type table, for a cross-check; None when a tensor type is unknown.
    pub weights_bytes_table: Option<u64>,
    /// Bytes of the tensors that belong to numbered layers (`blk.N.`), per layer, to plan partial offload.
    pub layer_bytes: Vec<u64>,
    pub non_layer_bytes: u64,
    pub warnings: Vec<String>,
}

fn get_u(kv: &BTreeMap<String, Value>, key: &str) -> Option<u64> {
    match kv.get(key) {
        Some(Value::U(v)) => Some(*v),
        Some(Value::I(v)) if *v >= 0 => Some(*v as u64),
        _ => None,
    }
}

pub fn summarize(g: &Gguf) -> Result<Summary> {
    let arch = match g.kv.get("general.architecture") {
        Some(Value::S(s))
            if !s.is_empty()
                && s.len() < 64
                && s.bytes()
                    .all(|b| b.is_ascii_alphanumeric() || b"._-".contains(&b)) =>
        {
            s.clone()
        }
        _ => bail!("missing or invalid general.architecture"),
    };
    let key = |k: &str| format!("{arch}.{k}");
    let layers = get_u(&g.kv, &key("block_count")).context("missing block_count")?;
    let embedding = get_u(&g.kv, &key("embedding_length")).context("missing embedding_length")?;
    let heads =
        get_u(&g.kv, &key("attention.head_count")).context("missing attention.head_count")?;
    if layers == 0 || layers > 4096 || embedding == 0 || heads == 0 || heads > 4096 {
        bail!("implausible model dimensions");
    }
    let kv_heads = get_u(&g.kv, &key("attention.head_count_kv")).unwrap_or(heads);
    let head_dim_k = get_u(&g.kv, &key("attention.key_length")).unwrap_or(embedding / heads);
    let head_dim_v = get_u(&g.kv, &key("attention.value_length")).unwrap_or(embedding / heads);
    let mut warnings = Vec::new();
    if g.kv
        .keys()
        .any(|k| k.contains(".ssm.") || k.contains("kv_lora_rank") || k.contains("rwkv"))
    {
        warnings.push("this architecture uses a cache layout other than standard attention (SSM/MLA/RWKV): the KV-cache estimate is NOT valid".to_string());
    }
    let mut layer_bytes = vec![0u64; layers as usize];
    let mut non_layer = 0u64;
    let mut table_total = Some(0u64);
    for t in &g.tensors {
        let b = t.bytes();
        table_total = match (table_total, b) {
            (Some(a), Some(b)) => a.checked_add(b),
            _ => None,
        };
        // Layer attribution uses the table; unknown types simply do not contribute (the total comes from the file layout).
        if let Some(b) = b {
            if let Some(rest) = t.name.strip_prefix("blk.") {
                if let Some(Ok(i)) = rest.split('.').next().map(|n| n.parse::<usize>()) {
                    if i < layer_bytes.len() {
                        layer_bytes[i] += b;
                        continue;
                    }
                }
            }
            non_layer += b;
        }
    }
    let weights_bytes = g.file_size.saturating_sub(g.data_offset);
    for t in &g.tensors {
        if let Some(b) = t.bytes() {
            if t.offset
                .checked_add(b)
                .map_or(true, |end| end > weights_bytes)
            {
                warnings.push(format!(
                    "tensor `{}` lies beyond the data region (file truncated or corrupt)",
                    t.name
                ));
                break;
            }
        }
    }
    if let Some(tt) = table_total {
        let diff = weights_bytes.abs_diff(tt);
        if weights_bytes > 0 && diff * 100 > weights_bytes {
            warnings.push(format!("tensor table sums to {tt} bytes but the data region is {weights_bytes} bytes (file truncated, or unknown padding)"));
        }
    } else {
        warnings.push("a tensor has an unknown ggml type: per-layer sizes are incomplete, the data-region size is used for the total".to_string());
    }
    Ok(Summary {
        gguf_version: g.version,
        architecture: arch.clone(),
        name: match g.kv.get("general.name") {
            Some(Value::S(s)) => Some(s.clone()),
            _ => None,
        },
        layers,
        embedding,
        heads,
        kv_heads,
        head_dim_k,
        head_dim_v,
        context_train: get_u(&g.kv, &key("context_length")),
        vocab: match g.kv.get("tokenizer.ggml.tokens") {
            Some(Value::Arr(n)) => Some(*n),
            _ => None,
        },
        experts: get_u(&g.kv, &key("expert_count")).unwrap_or(0),
        experts_used: get_u(&g.kv, &key("expert_used_count")).unwrap_or(0),
        tensors: g.tensors.len(),
        weights_bytes,
        weights_bytes_table: table_total,
        layer_bytes,
        non_layer_bytes: non_layer,
        warnings,
    })
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum KvType {
    F16,
    Q8_0,
    Q4_0,
}

impl KvType {
    pub fn parse(s: &str) -> Result<Self> {
        match s {
            "f16" => Ok(KvType::F16),
            "q8_0" => Ok(KvType::Q8_0),
            "q4_0" => Ok(KvType::Q4_0),
            o => bail!("kv cache type must be f16, q8_0 or q4_0, not `{o}`"),
        }
    }
    /// bytes per cached element (block size 32: q8_0 = 34 bytes, q4_0 = 18 bytes)
    fn bytes_per_elem(self) -> f64 {
        match self {
            KvType::F16 => 2.0,
            KvType::Q8_0 => 34.0 / 32.0,
            KvType::Q4_0 => 18.0 / 32.0,
        }
    }
}

pub fn kv_bytes_per_token(s: &Summary, kv: KvType) -> f64 {
    s.layers as f64 * s.kv_heads as f64 * (s.head_dim_k + s.head_dim_v) as f64 * kv.bytes_per_elem()
}

#[derive(Debug, Clone, Serialize)]
pub struct Fit {
    pub context: u64,
    pub kv_type: KvType,
    pub weights_mib: f64,
    pub kv_cache_mib: f64,
    pub overhead_mib: u64,
    pub overhead_is_heuristic: bool,
    pub total_mib: f64,
    pub fits_ram: Option<bool>,
    pub fits_vram: Option<bool>,
    /// Largest context (capped at the training context) that fits the RAM budget with 10 % headroom; None when no RAM budget was given or the weights alone do not fit.
    pub max_context_in_ram: Option<u64>,
    /// With a VRAM budget: how many layers fit on the GPU (weights + their KV share) with 10 % headroom; all layers fit when this equals the layer count.
    pub gpu_layers: Option<u64>,
    pub notes: Vec<String>,
}

const MIB: f64 = 1024.0 * 1024.0;

pub fn fit(
    s: &Summary,
    context: u64,
    kv: KvType,
    ram_mib: Option<u64>,
    vram_mib: Option<u64>,
) -> Fit {
    let per_tok = kv_bytes_per_token(s, kv);
    let weights = s.weights_bytes as f64 / MIB;
    let kv_mib = per_tok * context as f64 / MIB;
    let total = weights + kv_mib + OVERHEAD_MIB as f64;
    let mut notes = s.warnings.clone();
    if let Some(ct) = s.context_train {
        if context > ct {
            notes.push(format!(
                "context {context} exceeds the model's training context {ct}"
            ));
        }
    }
    if s.experts > 0 {
        notes.push(format!("mixture-of-experts model ({} experts, {} used): expert weights can stay in RAM with --n-cpu-moe if the pinned llama.cpp offers it", s.experts, s.experts_used));
    }
    let fits_ram = ram_mib.map(|r| total <= r as f64 * 0.9);
    let max_ctx = ram_mib.and_then(|r| {
        let free = r as f64 * 0.9 - weights - OVERHEAD_MIB as f64;
        if free <= 0.0 || per_tok <= 0.0 {
            return None;
        }
        let c = (free * MIB / per_tok).floor() as u64;
        Some(s.context_train.map_or(c, |ct| c.min(ct)))
    });
    let (fits_vram, gpu_layers) = match vram_mib {
        None => (None, None),
        Some(v) => {
            let budget = v as f64 * 0.9 - OVERHEAD_MIB as f64;
            let kv_layer = per_tok / s.layers as f64 * context as f64 / MIB;
            let mut used = 0.0;
            let mut n = 0u64;
            for lb in &s.layer_bytes {
                let c = *lb as f64 / MIB + kv_layer;
                if used + c > budget {
                    break;
                }
                used += c;
                n += 1;
            }
            let all = n == s.layers;
            (
                Some(all && used + s.non_layer_bytes as f64 / MIB <= budget),
                Some(n),
            )
        }
    };
    Fit {
        context,
        kv_type: kv,
        weights_mib: weights,
        kv_cache_mib: kv_mib,
        overhead_mib: OVERHEAD_MIB,
        overhead_is_heuristic: true,
        total_mib: total,
        fits_ram,
        fits_vram,
        max_context_in_ram: max_ctx,
        gpu_layers,
        notes,
    }
}

pub fn render(s: &Summary, f: &Fit) -> String {
    let mut o = format!(
        "{} ({}): {} layers, embedding {}, {} heads / {} KV heads, head dim {}/{}{}\n",
        s.name.as_deref().unwrap_or("unnamed model"),
        s.architecture,
        s.layers,
        s.embedding,
        s.heads,
        s.kv_heads,
        s.head_dim_k,
        s.head_dim_v,
        s.context_train
            .map(|c| format!(", trained for {c} tokens"))
            .unwrap_or_default()
    );
    o.push_str(&format!(
        "Estimate for {} tokens of context, KV cache {:?}: weights {:.0} MiB + KV cache {:.0} MiB + overhead {} MiB (heuristic) = {:.0} MiB\n",
        f.context, f.kv_type, f.weights_mib, f.kv_cache_mib, f.overhead_mib, f.total_mib
    ));
    if let Some(b) = f.fits_ram {
        o.push_str(&format!(
            "RAM: {} (10 % headroom kept){}\n",
            if b { "fits" } else { "does NOT fit" },
            f.max_context_in_ram
                .map(|c| format!("; largest context that fits: {c} tokens"))
                .unwrap_or_default()
        ));
    }
    if let (Some(n), Some(b)) = (f.gpu_layers, f.fits_vram) {
        o.push_str(&format!(
            "GPU: {n} of {} layers fit{}\n",
            s.layers,
            if b { " (everything fits)" } else { "" }
        ));
    }
    for n in &f.notes {
        o.push_str(&format!("note: {n}\n"));
    }
    o.push_str(
        "This is an estimate from file metadata; real use differs (see docs/LOCAL_AI.md).\n",
    );
    o
}

#[cfg(test)]
mod tests {
    use super::*;

    enum Kv {
        U32(u32),
        S(&'static str),
        StrArr(usize),
        U32Arr(usize),
    }

    fn put_str(b: &mut Vec<u8>, s: &str) {
        b.extend((s.len() as u64).to_le_bytes());
        b.extend(s.as_bytes());
    }

    /// Writes a complete synthetic GGUF: header, metadata, tensor table, alignment padding and zeroed tensor data.
    fn build(kvs: &[(&str, Kv)], tensors: &[(&str, Vec<u64>, u32)], version: u32) -> Vec<u8> {
        let mut b = b"GGUF".to_vec();
        b.extend(version.to_le_bytes());
        b.extend((tensors.len() as u64).to_le_bytes());
        b.extend((kvs.len() as u64).to_le_bytes());
        for (k, v) in kvs {
            put_str(&mut b, k);
            match v {
                Kv::U32(x) => {
                    b.extend(4u32.to_le_bytes());
                    b.extend(x.to_le_bytes());
                }
                Kv::S(s) => {
                    b.extend(8u32.to_le_bytes());
                    put_str(&mut b, s);
                }
                Kv::StrArr(n) => {
                    b.extend(9u32.to_le_bytes());
                    b.extend(8u32.to_le_bytes());
                    b.extend((*n as u64).to_le_bytes());
                    for i in 0..*n {
                        put_str(&mut b, &format!("tok{i}"));
                    }
                }
                Kv::U32Arr(n) => {
                    b.extend(9u32.to_le_bytes());
                    b.extend(4u32.to_le_bytes());
                    b.extend((*n as u64).to_le_bytes());
                    b.extend(vec![0u8; n * 4]);
                }
            }
        }
        let mut off = 0u64;
        let mut sizes = Vec::new();
        for (name, dims, ty) in tensors {
            put_str(&mut b, name);
            b.extend((dims.len() as u32).to_le_bytes());
            for d in dims {
                b.extend(d.to_le_bytes());
            }
            b.extend(ty.to_le_bytes());
            b.extend(off.to_le_bytes());
            let t = Tensor {
                name: name.to_string(),
                dims: dims.clone(),
                ggml_type: *ty,
                offset: off,
            };
            let sz = t.bytes().expect("fixture uses known types");
            sizes.push(sz);
            off += sz.div_ceil(32) * 32;
        }
        while b.len() % 32 != 0 {
            b.push(0);
        }
        b.extend(vec![0u8; off as usize]);
        b
    }

    fn llama_like(layers: u64) -> Vec<u8> {
        let kvs = vec![
            ("general.architecture", Kv::S("llama")),
            ("general.name", Kv::S("fixture")),
            ("llama.block_count", Kv::U32(layers as u32)),
            ("llama.embedding_length", Kv::U32(4096)),
            ("llama.attention.head_count", Kv::U32(32)),
            ("llama.attention.head_count_kv", Kv::U32(8)),
            ("llama.context_length", Kv::U32(131072)),
            ("tokenizer.ggml.tokens", Kv::StrArr(10)),
            ("tokenizer.ggml.token_type", Kv::U32Arr(10)),
        ];
        let mut tensors: Vec<(String, Vec<u64>, u32)> =
            vec![("token_embd.weight".into(), vec![4096, 64], 8)];
        for i in 0..layers {
            tensors.push((format!("blk.{i}.attn_q.weight"), vec![4096, 64], 12));
        }
        let leaked: Vec<(&str, Vec<u64>, u32)> = tensors
            .iter()
            .map(|(n, d, t)| (n.as_str(), d.clone(), *t))
            .collect();
        build(&kvs, &leaked, 3)
    }

    #[test]
    fn parses_a_synthetic_file_and_the_table_matches_the_data_region() {
        let bytes = llama_like(4);
        let g = parse(&bytes[..], bytes.len() as u64).unwrap();
        assert_eq!((g.version, g.tensors.len()), (3, 5));
        let s = summarize(&g).unwrap();
        assert_eq!(
            (
                s.architecture.as_str(),
                s.layers,
                s.embedding,
                s.heads,
                s.kv_heads
            ),
            ("llama", 4, 4096, 32, 8)
        );
        assert_eq!(
            (s.head_dim_k, s.head_dim_v, s.context_train, s.vocab),
            (128, 128, Some(131072), Some(10))
        );
        assert!(s.warnings.is_empty(), "{:?}", s.warnings);
        // Q8_0 embedding: 4096*64/32 blocks * 34 bytes; Q4_K layers: 4096*64/256 * 144 bytes each (all padded to 32 in the file)
        assert_eq!(s.non_layer_bytes, 4096 * 64 / 32 * 34);
        assert_eq!(s.layer_bytes, vec![4096 * 64 / 256 * 144; 4]);
        let pad = |x: u64| x.div_ceil(32) * 32;
        assert_eq!(
            s.weights_bytes,
            pad(s.non_layer_bytes) + 4 * pad(s.layer_bytes[0])
        );
    }

    #[test]
    fn kv_cache_arithmetic_is_exact() {
        // 32 layers * 8 KV heads * (128+128) * 2 bytes = 131072 bytes per token; 8192 tokens = 1024 MiB exactly
        let bytes = llama_like(32);
        let s = summarize(&parse(&bytes[..], bytes.len() as u64).unwrap()).unwrap();
        assert_eq!(kv_bytes_per_token(&s, KvType::F16), 131072.0);
        let f = fit(&s, 8192, KvType::F16, None, None);
        assert_eq!(f.kv_cache_mib, 1024.0);
        assert_eq!(
            fit(&s, 8192, KvType::Q8_0, None, None).kv_cache_mib,
            1024.0 * 34.0 / 32.0 / 2.0
        );
        assert!(fit(&s, 8192, KvType::Q4_0, None, None).kv_cache_mib < f.kv_cache_mib / 3.0);
        assert!(f.overhead_is_heuristic && f.fits_ram.is_none() && f.gpu_layers.is_none());
    }

    #[test]
    fn ram_fit_and_largest_context() {
        let bytes = llama_like(32);
        let s = summarize(&parse(&bytes[..], bytes.len() as u64).unwrap()).unwrap();
        let w = s.weights_bytes as f64 / MIB;
        let f = fit(&s, 8192, KvType::F16, Some(100_000), None);
        assert_eq!(f.fits_ram, Some(true));
        assert_eq!(
            f.max_context_in_ram,
            Some(131072),
            "capped at the training context"
        );
        let small = (w + 256.0 + 512.0) / 0.9; // room for 4096 tokens at 128 KiB/token, plus headroom
        let f = fit(&s, 8192, KvType::F16, Some(small.ceil() as u64), None);
        assert_eq!(f.fits_ram, Some(false));
        let c = f.max_context_in_ram.unwrap();
        assert!((4000..=4200).contains(&c), "{c}");
        assert_eq!(
            fit(&s, 1, KvType::F16, Some(1), None).max_context_in_ram,
            None,
            "weights alone do not fit"
        );
    }

    #[test]
    fn gpu_layers_follow_the_vram_budget() {
        let bytes = llama_like(8);
        let s = summarize(&parse(&bytes[..], bytes.len() as u64).unwrap()).unwrap();
        let all = fit(&s, 1024, KvType::F16, None, Some(100_000));
        assert_eq!((all.gpu_layers, all.fits_vram), (Some(8), Some(true)));
        let none = fit(&s, 1024, KvType::F16, None, Some(10));
        assert_eq!((none.gpu_layers, none.fits_vram), (Some(0), Some(false)));
        let per_layer = s.layer_bytes[0] as f64 / MIB
            + fit(&s, 1024, KvType::F16, None, None).kv_cache_mib / 8.0;
        let some = fit(
            &s,
            1024,
            KvType::F16,
            None,
            Some(((256.0 + per_layer * 3.5) / 0.9).ceil() as u64),
        );
        assert_eq!(some.gpu_layers, Some(3));
    }

    #[test]
    fn unusual_architectures_and_unknown_types_are_flagged_not_guessed() {
        let kvs = vec![
            ("general.architecture", Kv::S("deepseek2")),
            ("deepseek2.block_count", Kv::U32(2)),
            ("deepseek2.embedding_length", Kv::U32(512)),
            ("deepseek2.attention.head_count", Kv::U32(8)),
            ("deepseek2.attention.kv_lora_rank", Kv::U32(64)),
            ("deepseek2.expert_count", Kv::U32(16)),
            ("deepseek2.expert_used_count", Kv::U32(2)),
        ];
        let bytes = build(&kvs, &[("blk.0.w", vec![256], 12)], 3);
        let s = summarize(&parse(&bytes[..], bytes.len() as u64).unwrap()).unwrap();
        assert!(s.warnings.iter().any(|w| w.contains("NOT valid")));
        let f = fit(&s, 4096, KvType::F16, None, None);
        assert!(f.notes.iter().any(|n| n.contains("mixture-of-experts")));
        // unknown ggml type 99: parsing works, per-layer sizes are incomplete, total comes from the data region
        let mut raw = build(&kvs, &[], 3);
        raw.extend(vec![0u8; 64]);
        let mut g = parse(&raw[..], raw.len() as u64).unwrap();
        g.tensors.push(Tensor {
            name: "blk.0.x".into(),
            dims: vec![32],
            ggml_type: 99,
            offset: 0,
        });
        assert!(summarize(&g)
            .unwrap()
            .warnings
            .iter()
            .any(|w| w.contains("unknown ggml type")));
    }

    #[test]
    fn rejects_bad_headers_and_hostile_counts_without_allocating() {
        assert!(parse(&b"GGUX"[..], 4).is_err());
        assert!(
            parse(&b"GGUF\x01\0\0\0"[..], 8).is_err(),
            "version 1 is unsupported"
        );
        let mut huge = b"GGUF".to_vec();
        huge.extend(3u32.to_le_bytes());
        huge.extend(u64::MAX.to_le_bytes());
        huge.extend(0u64.to_le_bytes());
        assert!(parse(&huge[..], 24).is_err());
        let mut longstr = b"GGUF".to_vec();
        longstr.extend(3u32.to_le_bytes());
        longstr.extend(0u64.to_le_bytes());
        longstr.extend(1u64.to_le_bytes());
        longstr.extend(u64::MAX.to_le_bytes()); // key length
        assert!(parse(&longstr[..], 40).is_err());
        let full = llama_like(2);
        for cut in [5, 12, 30, 80, 200] {
            assert!(
                parse(&full[..cut.min(full.len() - 1)], full.len() as u64).is_err() || cut > 200
            );
        }
        assert!(KvType::parse("q5_0").is_err());
        let no_arch = build(&[("llama.block_count", Kv::U32(1))], &[], 3);
        assert!(summarize(&parse(&no_arch[..], no_arch.len() as u64).unwrap()).is_err());
    }

    #[test]
    fn invalid_alignment_and_truncated_data_are_reported() {
        let bad = build(
            &[
                ("general.architecture", Kv::S("llama")),
                ("general.alignment", Kv::U32(48)),
            ],
            &[],
            3,
        );
        assert!(
            parse(&bad[..], bad.len() as u64).is_err(),
            "alignment must be a power of two"
        );
        let full = llama_like(4);
        let cut = &full[..full.len() - 100]; // data region shorter than the tensor table claims
        let s = summarize(&parse(cut, cut.len() as u64).unwrap()).unwrap();
        assert!(
            s.warnings
                .iter()
                .any(|w| w.contains("beyond the data region")),
            "{:?}",
            s.warnings
        );
        assert_eq!(s.gguf_version, 3);
    }

    #[test]
    fn seeded_fuzz_never_panics() {
        let base = llama_like(3);
        let mut seed: u64 = 0x1234_5678_9abc_def0;
        let mut next = move || {
            seed ^= seed << 13;
            seed ^= seed >> 7;
            seed ^= seed << 17;
            seed
        };
        for _ in 0..4000 {
            let mut b = base.clone();
            let flips = 1 + next() % 6;
            for _ in 0..flips {
                let i = (next() % b.len() as u64) as usize;
                b[i] = next() as u8;
            }
            if next() % 4 == 0 {
                b.truncate((next() % b.len() as u64) as usize);
            }
            if let Ok(g) = parse(&b[..], b.len() as u64) {
                let _ = summarize(&g);
            }
        }
        for _ in 0..2000 {
            let n = (next() % 200) as usize;
            let mut b = b"GGUF\x03\0\0\0".to_vec();
            b.extend((0..n).map(|_| next() as u8));
            let _ = parse(&b[..], b.len() as u64);
        }
    }
}
