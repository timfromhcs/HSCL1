//! GPU tensor plumbing used by `selftest` and `bench`.
//!
//! Buffers are uploaded once and reused across runs so that a benchmark measures
//! dispatch, not allocation. On this integrated GPU the device-local heap is also
//! host-visible, so there is no staging copy yet; on a discrete GPU the allocator
//! falls back to the host-visible heap and the report says so.

use anyhow::{Context, Result};
use hcsuda_core::DType;
use hcsuda_vk::{Buffer, Device, Dispatch, Kernel, Timed};

/// A device-side f32 vector.
pub struct GpuTensor {
    pub buf: Buffer,
    pub len: usize,
}

pub struct Runner {
    // `dev` is declared last on purpose: Rust drops fields in declaration order,
    // so the VkDevice must be destroyed *after* the objects created from it.
    pub dispatch: Dispatch,
    pub saxpy: Kernel,
    pub triad: Kernel,
    pub gemv: Kernel,
    pub gemm_tiled: Kernel,
    pub softmax: Kernel,
    pub layernorm: Kernel,
    pub rmsnorm: Kernel,
    pub rope: Kernel,
    pub gemm_i8dot: Kernel,
    pub gemm_i8dot_tiled: Kernel,
    pub gemm_f16: Kernel,
    /// `None` when the device cannot build the cooperative-matrix pipeline.
    pub gemm_coopmat: Option<Kernel>,
    pub eltwise: Kernel,
    pub rope_heads: Kernel,
    pub attn_causal: Kernel,
    pub dev: Device,
}

#[repr(C)]
#[derive(Clone, Copy, bytemuck::Pod, bytemuck::Zeroable)]
struct PushAlphaN {
    alpha: f32,
    n: u32,
}

#[repr(C)]
#[derive(Clone, Copy, bytemuck::Pod, bytemuck::Zeroable)]
struct PushRowsCols {
    rows: u32,
    cols: u32,
}

#[repr(C)]
#[derive(Clone, Copy, bytemuck::Pod, bytemuck::Zeroable)]
struct PushMkn {
    m: u32,
    n: u32,
    k: u32,
}

#[repr(C)]
#[derive(Clone, Copy, bytemuck::Pod, bytemuck::Zeroable)]
struct PushRowsColsF {
    cols: u32,
    rows: u32,
    eps: f32,
}

#[repr(C)]
#[derive(Clone, Copy, bytemuck::Pod, bytemuck::Zeroable)]
struct PushRope {
    dim: u32,
    rows: u32,
    pos0: u32,
    base: f32,
}

#[repr(C)]
#[derive(Clone, Copy, bytemuck::Pod, bytemuck::Zeroable)]
struct PushEltwise {
    n: u32,
    mode: u32,
}

#[repr(C)]
#[derive(Clone, Copy, bytemuck::Pod, bytemuck::Zeroable)]
struct PushRopeHeads {
    dim: u32,
    head_dim: u32,
    rows: u32,
    heads: u32,
    pos0: u32,
    base: f32,
}

#[repr(C)]
#[derive(Clone, Copy, bytemuck::Pod, bytemuck::Zeroable)]
struct PushAttn {
    t: u32,
    dim: u32,
    heads: u32,
    head_dim: u32,
    scale: f32,
}

/// Longest sequence `attn_causal` supports (its score row is in shared memory).
pub const ATTN_MAX_TOKENS: usize = 256;

impl Runner {
    pub fn new(device_index: Option<usize>) -> Result<Self> {
        if !hcsuda_vk::shaders_available() {
            anyhow::bail!(
                "no compute shaders were compiled (glslc missing at build time); \
                 install the Vulkan SDK or set GLSLC, then rebuild"
            );
        }
        let dev = Device::new(device_index).context("creating Vulkan device")?;
        let dispatch = Dispatch::new(&dev).context("creating dispatch")?;
        let saxpy = Kernel::from_shader(&dev, "saxpy", 2, 8).context("saxpy kernel")?;
        let triad = Kernel::from_shader(&dev, "triad", 3, 8).context("triad kernel")?;
        let gemv = Kernel::from_shader(&dev, "gemv", 3, 8).context("gemv kernel")?;
        let gemm_tiled =
            Kernel::from_shader(&dev, "gemm_tiled", 3, 12).context("gemm_tiled kernel")?;
        let softmax = Kernel::from_shader(&dev, "softmax", 2, 8).context("softmax kernel")?;
        let layernorm =
            Kernel::from_shader(&dev, "layernorm", 4, 12).context("layernorm kernel")?;
        let rmsnorm = Kernel::from_shader(&dev, "rmsnorm", 3, 12).context("rmsnorm kernel")?;
        let rope = Kernel::from_shader(&dev, "rope", 2, 16).context("rope kernel")?;
        let gemm_i8dot =
            Kernel::from_shader(&dev, "gemm_i8dot", 3, 12).context("gemm_i8dot kernel")?;
        let gemm_i8dot_tiled = Kernel::from_shader(&dev, "gemm_i8dot_tiled", 3, 12)
            .context("gemm_i8dot_tiled kernel")?;
        let gemm_f16 =
            Kernel::from_shader(&dev, "gemm_f16_tiled", 3, 12).context("gemm_f16 kernel")?;
        let gemm_coopmat = if dev.features.cooperative_matrix {
            Kernel::from_shader(&dev, "gemm_coopmat", 3, 12).ok()
        } else {
            None
        };
        let eltwise = Kernel::from_shader(&dev, "eltwise", 3, 8).context("eltwise kernel")?;
        let rope_heads =
            Kernel::from_shader(&dev, "rope_heads", 2, 24).context("rope_heads kernel")?;
        let attn_causal =
            Kernel::from_shader(&dev, "attn_causal", 4, 20).context("attn_causal kernel")?;
        Ok(Self {
            dispatch,
            saxpy,
            triad,
            gemv,
            gemm_tiled,
            softmax,
            layernorm,
            rmsnorm,
            rope,
            gemm_i8dot,
            gemm_i8dot_tiled,
            gemm_f16,
            gemm_coopmat,
            eltwise,
            rope_heads,
            attn_causal,
            dev,
        })
    }

    pub fn label(&self) -> String {
        format!(
            "{} | Vulkan {} | driver {:#x} | {}",
            self.dev.name(),
            self.dev.api_version(),
            self.dev.props.driver_version,
            if self.dispatch.has_timestamps() {
                "gpu timestamps"
            } else {
                "wall clock only"
            }
        )
    }

    pub fn upload(&self, values: &[f32]) -> Result<GpuTensor> {
        let bytes = (values.len() * 4) as u64;
        let buf = Buffer::storage(&self.dev, bytes).context("allocating storage buffer")?;
        if !buf.host_visible {
            anyhow::bail!(
                "the chosen memory type is not host visible; H1 has no staging path yet \
                 (this is expected on a discrete GPU)"
            );
        }
        buf.upload_f32(&self.dev, values)
            .context("uploading buffer")?;
        Ok(GpuTensor {
            buf,
            len: values.len(),
        })
    }

    /// Upload packed words (four int8 per `u32`); `len` counts words.
    pub fn upload_u32(&self, values: &[u32]) -> Result<GpuTensor> {
        let buf = Buffer::storage(&self.dev, (values.len() * 4) as u64)
            .context("allocating storage buffer")?;
        buf.upload_u32(&self.dev, values)
            .context("uploading buffer")?;
        Ok(GpuTensor {
            buf,
            len: values.len(),
        })
    }

    /// Output buffer of `len` zeroed i32 values.
    pub fn alloc_i32(&self, len: usize) -> Result<GpuTensor> {
        let buf = Buffer::storage(&self.dev, (len * 4) as u64).context("allocating buffer")?;
        buf.upload(&self.dev, &vec![0u8; len * 4])
            .context("zeroing buffer")?;
        Ok(GpuTensor { buf, len })
    }

    pub fn download_i32(&self, t: &GpuTensor) -> Result<Vec<i32>> {
        t.buf
            .read_i32(&self.dev, t.len)
            .context("reading back buffer")
    }

    /// int8 x int8 -> int32 product. `a` is m x k packed along k, `bt` is B transposed
    /// (n x k) packed along k; `k` must be a multiple of 4.
    pub fn gemm_i8dot(
        &mut self,
        a: &GpuTensor,
        bt: &GpuTensor,
        c: &GpuTensor,
        m: usize,
        k: usize,
        n: usize,
    ) -> Result<Timed> {
        anyhow::ensure!(k % 4 == 0, "gemm_i8dot needs k % 4 == 0");
        let pc = PushMkn {
            m: m as u32,
            n: n as u32,
            k: k as u32,
        };
        let push = bytemuck::bytes_of(&pc);
        let groups = ((n as u32).div_ceil(16), (m as u32).div_ceil(16), 1);
        self.dispatch
            .run(
                &self.dev,
                &self.gemm_i8dot,
                &[&a.buf, &bt.buf, &c.buf],
                push,
                groups,
            )
            .map_err(Into::into)
    }

    /// Shared-memory tiled variant of [`Runner::gemm_i8dot`]; any `k % 4 == 0`.
    pub fn gemm_i8dot_tiled(
        &mut self,
        a: &GpuTensor,
        bt: &GpuTensor,
        c: &GpuTensor,
        m: usize,
        k: usize,
        n: usize,
    ) -> Result<Timed> {
        anyhow::ensure!(k % 4 == 0, "gemm_i8dot_tiled needs k % 4 == 0");
        let pc = PushMkn {
            m: m as u32,
            n: n as u32,
            k: k as u32,
        };
        let push = bytemuck::bytes_of(&pc);
        let groups = ((n as u32).div_ceil(16), (m as u32).div_ceil(16), 1);
        self.dispatch
            .run(
                &self.dev,
                &self.gemm_i8dot_tiled,
                &[&a.buf, &bt.buf, &c.buf],
                push,
                groups,
            )
            .map_err(Into::into)
    }

    /// f16 storage, f32 math: `a` (m x k) and `b` (k x n) are packed halves
    /// ([`hcsuda_core::tensor::pack_f16x2`]); the output is f32 (m x n).
    pub fn gemm_f16(
        &mut self,
        a: &GpuTensor,
        b: &GpuTensor,
        c: &GpuTensor,
        m: usize,
        k: usize,
        n: usize,
    ) -> Result<Timed> {
        let pc = PushMkn {
            m: m as u32,
            n: n as u32,
            k: k as u32,
        };
        let push = bytemuck::bytes_of(&pc);
        let groups = ((n as u32).div_ceil(16), (m as u32).div_ceil(16), 1);
        self.dispatch
            .run(
                &self.dev,
                &self.gemm_f16,
                &[&a.buf, &b.buf, &c.buf],
                push,
                groups,
            )
            .map_err(Into::into)
    }

    /// Cooperative-matrix GEMM, f16 inputs (packed halves), f32 output.
    /// m, n and k must all be multiples of 16.
    pub fn gemm_coopmat(
        &mut self,
        a: &GpuTensor,
        b: &GpuTensor,
        c: &GpuTensor,
        m: usize,
        k: usize,
        n: usize,
    ) -> Result<Timed> {
        anyhow::ensure!(
            m % 16 == 0 && n % 16 == 0 && k % 16 == 0,
            "gemm_coopmat needs m, n, k to be multiples of 16"
        );
        let kernel = self
            .gemm_coopmat
            .as_ref()
            .context("this device has no cooperative-matrix pipeline")?;
        let pc = PushMkn {
            m: m as u32,
            n: n as u32,
            k: k as u32,
        };
        let push = bytemuck::bytes_of(&pc);
        let groups = ((n / 16) as u32, (m / 16) as u32, 1);
        self.dispatch
            .run(&self.dev, kernel, &[&a.buf, &b.buf, &c.buf], push, groups)
            .map_err(Into::into)
    }

    fn zeros(&self, n: usize) -> Result<GpuTensor> {
        self.upload(&vec![0.0f32; n])
    }

    /// `mode` 0: c = a + b; 1: c = silu(a) * b.
    pub fn eltwise(
        &mut self,
        a: &GpuTensor,
        b: &GpuTensor,
        c: &GpuTensor,
        mode: u32,
    ) -> Result<Timed> {
        let pc = PushEltwise {
            n: a.len as u32,
            mode,
        };
        let push = bytemuck::bytes_of(&pc);
        let groups = (a.len as u32).div_ceil(256);
        self.dispatch
            .run(
                &self.dev,
                &self.eltwise,
                &[&a.buf, &b.buf, &c.buf],
                push,
                (groups, 1, 1),
            )
            .map_err(Into::into)
    }

    /// Split-half RoPE on every head of a `[rows, heads * head_dim]` matrix.
    #[allow(clippy::too_many_arguments)]
    pub fn rope_heads(
        &mut self,
        x: &GpuTensor,
        y: &GpuTensor,
        rows: usize,
        heads: usize,
        head_dim: usize,
        pos0: u32,
        base: f32,
    ) -> Result<Timed> {
        let pc = PushRopeHeads {
            dim: (heads * head_dim) as u32,
            head_dim: head_dim as u32,
            rows: rows as u32,
            heads: heads as u32,
            pos0,
            base,
        };
        let push = bytemuck::bytes_of(&pc);
        let groups = ((rows * heads * head_dim / 2) as u32).div_ceil(256);
        self.dispatch
            .run(
                &self.dev,
                &self.rope_heads,
                &[&x.buf, &y.buf],
                push,
                (groups, 1, 1),
            )
            .map_err(Into::into)
    }

    /// Causal multi-head attention; `t` must not exceed [`ATTN_MAX_TOKENS`].
    #[allow(clippy::too_many_arguments)]
    pub fn attn_causal(
        &mut self,
        q: &GpuTensor,
        k: &GpuTensor,
        v: &GpuTensor,
        ctx: &GpuTensor,
        t: usize,
        heads: usize,
        head_dim: usize,
    ) -> Result<Timed> {
        anyhow::ensure!(
            t <= ATTN_MAX_TOKENS,
            "attn_causal supports at most {ATTN_MAX_TOKENS} tokens, got {t}"
        );
        let pc = PushAttn {
            t: t as u32,
            dim: (heads * head_dim) as u32,
            heads: heads as u32,
            head_dim: head_dim as u32,
            scale: 1.0 / (head_dim as f32).sqrt(),
        };
        let push = bytemuck::bytes_of(&pc);
        self.dispatch
            .run(
                &self.dev,
                &self.attn_causal,
                &[&q.buf, &k.buf, &v.buf, &ctx.buf],
                push,
                (t as u32, heads as u32, 1),
            )
            .map_err(Into::into)
    }

    /// The transformer block of `hcsuda_core::transformer`, composed from GPU
    /// kernels. Same shape rules as the CPU reference (checked there first).
    pub fn block_forward_gpu(
        &mut self,
        cfg: &hcsuda_core::transformer::BlockConfig,
        w: &hcsuda_core::transformer::BlockWeights,
        x: &[f32],
    ) -> Result<Vec<f32>> {
        let (t, d, f) = (cfg.tokens, cfg.dim, cfg.ffn);
        anyhow::ensure!(
            cfg.heads > 0 && d % cfg.heads == 0 && (d / cfg.heads) % 2 == 0,
            "dim must split into an even head dimension"
        );
        anyhow::ensure!(
            x.len() == t * d,
            "x has {} values, expected {}",
            x.len(),
            t * d
        );
        let hd = d / cfg.heads;

        let gx = self.upload(x)?;
        let (g1, g2) = (self.upload(&w.g1)?, self.upload(&w.g2)?);
        let (wq, wk, wv, wo) = (
            self.upload(&w.wq)?,
            self.upload(&w.wk)?,
            self.upload(&w.wv)?,
            self.upload(&w.wo)?,
        );
        let (wg, wu, wd) = (
            self.upload(&w.wg)?,
            self.upload(&w.wu)?,
            self.upload(&w.wd)?,
        );

        let h = self.zeros(t * d)?;
        self.rmsnorm(&gx, &g1, &h, t, d, cfg.eps)?;
        let (q, k, v) = (self.zeros(t * d)?, self.zeros(t * d)?, self.zeros(t * d)?);
        self.gemm_tiled(&h, &wq, &q, t, d, d)?;
        self.gemm_tiled(&h, &wk, &k, t, d, d)?;
        self.gemm_tiled(&h, &wv, &v, t, d, d)?;
        let (qr, kr) = (self.zeros(t * d)?, self.zeros(t * d)?);
        self.rope_heads(&q, &qr, t, cfg.heads, hd, 0, cfg.rope_base)?;
        self.rope_heads(&k, &kr, t, cfg.heads, hd, 0, cfg.rope_base)?;
        let ctx = self.zeros(t * d)?;
        self.attn_causal(&qr, &kr, &v, &ctx, t, cfg.heads, hd)?;
        let attn = self.zeros(t * d)?;
        self.gemm_tiled(&ctx, &wo, &attn, t, d, d)?;
        let x1 = self.zeros(t * d)?;
        self.eltwise(&gx, &attn, &x1, 0)?;

        let h2 = self.zeros(t * d)?;
        self.rmsnorm(&x1, &g2, &h2, t, d, cfg.eps)?;
        let (gate, up) = (self.zeros(t * f)?, self.zeros(t * f)?);
        self.gemm_tiled(&h2, &wg, &gate, t, d, f)?;
        self.gemm_tiled(&h2, &wu, &up, t, d, f)?;
        let act = self.zeros(t * f)?;
        self.eltwise(&gate, &up, &act, 1)?;
        let down = self.zeros(t * d)?;
        self.gemm_tiled(&act, &wd, &down, t, f, d)?;
        let out = self.zeros(t * d)?;
        self.eltwise(&x1, &down, &out, 0)?;
        self.download(&out)
    }

    pub fn download(&self, t: &GpuTensor) -> Result<Vec<f32>> {
        t.buf
            .read_f32(&self.dev, t.len)
            .context("reading back buffer")
    }

    pub fn saxpy(&mut self, alpha: f32, x: &GpuTensor, y: &GpuTensor) -> Result<Timed> {
        let n = x.len as u32;
        let pc = PushAlphaN { alpha, n };
        let push = bytemuck::bytes_of(&pc);
        let groups = (n.div_ceil(256), 1, 1);
        self.dispatch
            .run(&self.dev, &self.saxpy, &[&x.buf, &y.buf], push, groups)
            .map_err(Into::into)
    }

    pub fn triad(
        &mut self,
        alpha: f32,
        a: &GpuTensor,
        b: &GpuTensor,
        c: &GpuTensor,
    ) -> Result<Timed> {
        let n = a.len as u32;
        let pc = PushAlphaN { alpha, n };
        let push = bytemuck::bytes_of(&pc);
        let groups = (n.div_ceil(256), 1, 1);
        self.dispatch
            .run(
                &self.dev,
                &self.triad,
                &[&a.buf, &b.buf, &c.buf],
                push,
                groups,
            )
            .map_err(Into::into)
    }

    pub fn gemv(
        &mut self,
        a: &GpuTensor,
        x: &GpuTensor,
        y: &GpuTensor,
        rows: usize,
        cols: usize,
    ) -> Result<Timed> {
        let pc = PushRowsCols {
            rows: rows as u32,
            cols: cols as u32,
        };
        let push = bytemuck::bytes_of(&pc);
        let groups = ((rows as u32).div_ceil(64), 1, 1);
        self.dispatch
            .run(
                &self.dev,
                &self.gemv,
                &[&a.buf, &x.buf, &y.buf],
                push,
                groups,
            )
            .map_err(Into::into)
    }

    /// Tiled GEMM: `C = A * B`, A `m x k`, B `k x n`, all row-major f32.
    pub fn gemm_tiled(
        &mut self,
        a: &GpuTensor,
        b: &GpuTensor,
        c: &GpuTensor,
        m: usize,
        k: usize,
        n: usize,
    ) -> Result<Timed> {
        let pc = PushMkn {
            m: m as u32,
            n: n as u32,
            k: k as u32,
        };
        let push = bytemuck::bytes_of(&pc);
        let groups = ((n as u32).div_ceil(16), (m as u32).div_ceil(16), 1);
        self.dispatch
            .run(
                &self.dev,
                &self.gemm_tiled,
                &[&a.buf, &b.buf, &c.buf],
                push,
                groups,
            )
            .map_err(Into::into)
    }
    /// Softmax over one row; one workgroup per row.
    pub fn softmax(
        &mut self,
        x: &GpuTensor,
        y: &GpuTensor,
        rows: usize,
        cols: usize,
    ) -> Result<Timed> {
        // The softmax shader's push block is { uint cols; uint rows; } (8 bytes).
        let pc = [cols as u32, rows as u32];
        let push = bytemuck::bytes_of(&pc);
        self.dispatch
            .run(
                &self.dev,
                &self.softmax,
                &[&x.buf, &y.buf],
                push,
                (rows as u32, 1, 1),
            )
            .map_err(Into::into)
    }

    /// Layer normalisation over the last dimension; one workgroup per row.
    #[allow(clippy::too_many_arguments)]
    pub fn layernorm(
        &mut self,
        x: &GpuTensor,
        gamma: &GpuTensor,
        beta: &GpuTensor,
        y: &GpuTensor,
        rows: usize,
        cols: usize,
        eps: f32,
    ) -> Result<Timed> {
        let pc = PushRowsColsF {
            cols: cols as u32,
            rows: rows as u32,
            eps,
        };
        let push = bytemuck::bytes_of(&pc);
        self.dispatch
            .run(
                &self.dev,
                &self.layernorm,
                &[&x.buf, &gamma.buf, &beta.buf, &y.buf],
                push,
                (rows as u32, 1, 1),
            )
            .map_err(Into::into)
    }

    /// RMS normalisation over the last dimension; one workgroup per row.
    pub fn rmsnorm(
        &mut self,
        x: &GpuTensor,
        gamma: &GpuTensor,
        y: &GpuTensor,
        rows: usize,
        cols: usize,
        eps: f32,
    ) -> Result<Timed> {
        let pc = PushRowsColsF {
            cols: cols as u32,
            rows: rows as u32,
            eps,
        };
        let push = bytemuck::bytes_of(&pc);
        self.dispatch
            .run(
                &self.dev,
                &self.rmsnorm,
                &[&x.buf, &gamma.buf, &y.buf],
                push,
                (rows as u32, 1, 1),
            )
            .map_err(Into::into)
    }

    /// Rotary position embedding (split-half); one invocation per (row, pair).
    pub fn rope(
        &mut self,
        x: &GpuTensor,
        y: &GpuTensor,
        rows: usize,
        dim: usize,
        pos0: u32,
        base: f32,
    ) -> Result<Timed> {
        let pc = PushRope {
            dim: dim as u32,
            rows: rows as u32,
            pos0,
            base,
        };
        let push = bytemuck::bytes_of(&pc);
        let groups = ((rows * dim / 2) as u32).div_ceil(256);
        self.dispatch
            .run(
                &self.dev,
                &self.rope,
                &[&x.buf, &y.buf],
                push,
                (groups, 1, 1),
            )
            .map_err(Into::into)
    }
}

/// Tolerance for an f32 differential test of a reduction of `len` elements.
pub fn f32_tolerance(len: usize) -> hcsuda_core::Tolerance {
    DType::F32.tolerance().for_len(len)
}
