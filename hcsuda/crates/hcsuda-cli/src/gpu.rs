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
