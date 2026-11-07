//! The conservative planner.
//!
//! Given an operation, a dtype, a shape and a capability record, the planner
//! returns the fastest path that is **known to be correct on this device**.
//! Unknown paths are never chosen. Promotion is a separate, evidence-producing
//! step (`hcsuda bench` + differential test), not a heuristic here.

use serde::{Deserialize, Serialize};

use crate::caps::DeviceCaps;
use crate::dtype::DType;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Op {
    Saxpy,
    Triad,
    Gemv,
    Gemm,
    Softmax,
    LayerNorm,
    RmsNorm,
    Gelu,
    Silu,
    Reduce,
}

impl Op {
    pub const ALL: [Op; 10] = [
        Op::Saxpy,
        Op::Triad,
        Op::Gemv,
        Op::Gemm,
        Op::Softmax,
        Op::LayerNorm,
        Op::RmsNorm,
        Op::Gelu,
        Op::Silu,
        Op::Reduce,
    ];

    pub fn name(self) -> &'static str {
        match self {
            Op::Saxpy => "saxpy",
            Op::Triad => "triad",
            Op::Gemv => "gemv",
            Op::Gemm => "gemm",
            Op::Softmax => "softmax",
            Op::LayerNorm => "layernorm",
            Op::RmsNorm => "rmsnorm",
            Op::Gelu => "gelu",
            Op::Silu => "silu",
            Op::Reduce => "reduce",
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum PathKind {
    /// Single-threaded CPU oracle. Always correct, never fast.
    Reference,
    /// Multi-threaded CPU.
    CpuParallel,
    /// Vulkan, one element per invocation (no shared memory).
    VulkanScalar,
    /// Vulkan with shared-memory tiling.
    VulkanTiled,
    /// Vulkan cooperative matrix (f16 inputs, f32 accumulate).
    VulkanCoopMat,
    /// Vulkan integer dot product (int8/int4 quantised GEMM).
    VulkanIntDot,
}

impl PathKind {
    pub fn name(self) -> &'static str {
        match self {
            PathKind::Reference => "reference",
            PathKind::CpuParallel => "cpu_parallel",
            PathKind::VulkanScalar => "vulkan_scalar",
            PathKind::VulkanTiled => "vulkan_tiled",
            PathKind::VulkanCoopMat => "vulkan_coopmat",
            PathKind::VulkanIntDot => "vulkan_intdot",
        }
    }

    /// Key used in `DeviceCaps::verified_paths` and in benchmark evidence.
    pub fn key(self, op: Op, dtype: DType) -> String {
        format!("{}:{}:{}", self.name(), op.name(), dtype.name())
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub struct Tile {
    /// Output elements per workgroup along x.
    pub x: u32,
    /// Output elements per workgroup along y.
    pub y: u32,
    /// Elements per inner step.
    pub k: u32,
    /// Bytes of shared memory the tile needs (0 for scalar paths).
    pub shared_bytes: u32,
}

impl Tile {
    pub const NONE: Tile = Tile {
        x: 1,
        y: 1,
        k: 1,
        shared_bytes: 0,
    };
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Plan {
    pub op: Op,
    pub dtype: DType,
    pub kind: PathKind,
    pub tile: Tile,
    /// Human-readable justification, always one sentence.
    pub reason: String,
}

/// Shape of the problem. Unused fields are `None`; the planner only reads what
/// the op needs, which keeps one type for all operations.
#[derive(Debug, Clone, Copy, Default, PartialEq, Eq)]
pub struct Shape {
    pub m: usize,
    pub n: usize,
    pub k: usize,
}

impl Shape {
    pub fn new(m: usize, n: usize, k: usize) -> Self {
        Self { m, n, k }
    }
}

/// Pick a tile that fits in shared memory with room for two operands.
/// RDNA2 exposes 32 KiB, so a 16x16 f32 tile pair is 2 KiB and a 32x32 pair is
/// 8 KiB; the planner stays at or below a quarter of the reported limit.
pub fn tile_for(dtype: DType, max_shared: u32) -> Tile {
    let element_bytes = (dtype.bits() / 8).max(1);
    let budget = max_shared / 4;
    // x*y*element_bytes*2 <= budget, with square tiles.
    let side = ((budget / (2 * element_bytes)).max(1) as f64).sqrt() as u32;
    let side = side.clamp(1, 32);
    Tile {
        x: side,
        y: side,
        k: side,
        shared_bytes: side * side * element_bytes * 2,
    }
}

/// The decision itself.
pub fn plan(op: Op, dtype: DType, shape: Shape, caps: &DeviceCaps) -> Plan {
    let dtype_path = caps.dtype(dtype);

    // 1. A format the device cannot compute in never reaches the GPU.
    if !dtype_path.compute.can_compute() {
        return Plan {
            op,
            dtype,
            kind: PathKind::Reference,
            tile: Tile::NONE,
            reason: format!(
                "{} has no compute path on this device ({:?}); reference kernel used",
                dtype.name(),
                dtype_path.compute
            ),
        };
    }

    // 2. Integer formats prefer the accelerated dot-product path, but only if
    //    that path has been verified on this device.
    let int_path = match dtype {
        DType::I8 => Some(PathKind::VulkanIntDot),
        DType::I4 if caps.features.int4_dot => Some(PathKind::VulkanIntDot),
        _ => None,
    };
    if let Some(kind) = int_path {
        if matches!(op, Op::Gemm | Op::Gemv) && caps.path_is_verified(&kind.key(op, dtype)) {
            return Plan {
                op,
                dtype,
                kind,
                tile: tile_for(DType::I8, caps.max_shared_memory),
                reason: format!("{} dot-product path verified on this device", dtype.name()),
            };
        }
        return Plan {
            op,
            dtype,
            kind: PathKind::Reference,
            tile: Tile::NONE,
            reason: format!(
                "{} compute is accelerated but no verified {} kernel exists yet",
                dtype.name(),
                op.name()
            ),
        };
    }

    // 3. Matrix work: cooperative matrix first, then shared-memory tiling.
    if matches!(op, Op::Gemm | Op::Gemv) {
        let coop = PathKind::VulkanCoopMat.key(op, dtype);
        if caps.features.cooperative_matrix
            && matches!(dtype, DType::F16 | DType::Bf16)
            && caps.path_is_verified(&coop)
        {
            return Plan {
                op,
                dtype,
                kind: PathKind::VulkanCoopMat,
                tile: Tile {
                    x: 16,
                    y: 16,
                    k: 16,
                    shared_bytes: 16 * 16 * 4,
                },
                reason: "cooperative-matrix path verified for 16x16x16 f16 tiles".into(),
            };
        }
        let tiled = PathKind::VulkanTiled.key(op, dtype);
        if caps.path_is_verified(&tiled) {
            return Plan {
                op,
                dtype,
                kind: PathKind::VulkanTiled,
                tile: tile_for(dtype, caps.max_shared_memory),
                reason: "shared-memory tiled path verified on this device".into(),
            };
        }
    }

    // 4. Elementwise work: the scalar path is cheap to verify and hard to get
    //    wrong, so it is the default GPU path for these ops.
    if matches!(op, Op::Saxpy | Op::Triad | Op::Gelu | Op::Silu) {
        let scalar = PathKind::VulkanScalar.key(op, dtype);
        if caps.path_is_verified(&scalar) {
            return Plan {
                op,
                dtype,
                kind: PathKind::VulkanScalar,
                tile: Tile::NONE,
                reason: "scalar elementwise path verified on this device".into(),
            };
        }
    }

    // 5. Reductions and normalisation need a verified kernel or stay on the CPU.
    if matches!(op, Op::Softmax | Op::LayerNorm | Op::RmsNorm | Op::Reduce) {
        let tiled = PathKind::VulkanTiled.key(op, dtype);
        if caps.path_is_verified(&tiled) {
            return Plan {
                op,
                dtype,
                kind: PathKind::VulkanTiled,
                tile: tile_for(dtype, caps.max_shared_memory),
                reason: "row-wise tiled reduction verified on this device".into(),
            };
        }
    }

    // 6. Fallback: the oracle. This is the honest default for a fresh device.
    let _ = shape;
    Plan {
        op,
        dtype,
        kind: PathKind::Reference,
        tile: Tile::NONE,
        reason: format!(
            "no verified {} path for {} on this device yet; reference kernel used",
            op.name(),
            dtype.name()
        ),
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::caps::{DTypePath, Features, Heap, Support};
    use std::collections::{BTreeMap, BTreeSet};

    fn caps(features: Features, verified: &[&str]) -> DeviceCaps {
        let mut dtypes = BTreeMap::new();
        for d in DType::ALL {
            dtypes.insert(
                d.name().to_string(),
                DTypePath {
                    storage: Support::Native,
                    compute: Support::Native,
                },
            );
        }
        DeviceCaps {
            schema: crate::SCHEMA_VERSION,
            name: "test".into(),
            vendor_id: 0,
            device_id: 0,
            device_type: "integrated".into(),
            api_version: "1.3".into(),
            driver_name: "test".into(),
            driver_info: "test".into(),
            subgroup_size: 64,
            max_workgroup_invocations: 1024,
            max_shared_memory: 32768,
            max_storage_range: u32::MAX as u64,
            timestamp_period_ns: 10.0,
            heaps: vec![Heap {
                index: 0,
                size_bytes: 1 << 30,
                budget_bytes: None,
                device_local: true,
                host_visible: false,
            }],
            features,
            dtypes,
            verified_paths: verified
                .iter()
                .map(|s| s.to_string())
                .collect::<BTreeSet<_>>(),
        }
    }

    #[test]
    fn fresh_device_falls_back_to_reference() {
        let c = caps(Features::default(), &[]);
        let p = plan(Op::Gemm, DType::F32, Shape::new(64, 64, 64), &c);
        assert_eq!(p.kind, PathKind::Reference);
        assert!(p.reason.contains("no verified"));
    }

    #[test]
    fn unverified_int_path_is_not_used_even_when_hardware_supports_it() {
        let f = Features {
            int8_dot: true,
            ..Default::default()
        };
        let c = caps(f, &[]);
        let p = plan(Op::Gemm, DType::I8, Shape::new(64, 64, 64), &c);
        assert_eq!(p.kind, PathKind::Reference);
        assert!(p.reason.contains("no verified"));
    }

    #[test]
    fn verified_int_path_is_used() {
        let f = Features {
            int8_dot: true,
            ..Default::default()
        };
        let c = caps(f, &["vulkan_intdot:gemm:i8"]);
        let p = plan(Op::Gemm, DType::I8, Shape::new(64, 64, 64), &c);
        assert_eq!(p.kind, PathKind::VulkanIntDot);
    }

    #[test]
    fn coopmat_requires_f16_and_verification() {
        let f = Features {
            cooperative_matrix: true,
            ..Default::default()
        };
        let c = caps(f, &["vulkan_coopmat:gemm:f16"]);
        assert_eq!(
            plan(Op::Gemm, DType::F16, Shape::new(64, 64, 64), &c).kind,
            PathKind::VulkanCoopMat
        );
        assert_eq!(
            plan(Op::Gemm, DType::F32, Shape::new(64, 64, 64), &c).kind,
            PathKind::Reference
        );
    }

    #[test]
    fn tile_fits_shared_memory_budget() {
        let t = tile_for(DType::F32, 32768);
        assert!(t.shared_bytes <= 32768);
        assert!(t.x >= 1 && t.x <= 32);
        let t16 = tile_for(DType::F16, 32768);
        assert!(t16.x >= t.x, "f16 should allow an equal or larger tile");
    }

    #[test]
    fn unsupported_compute_dtype_never_leaves_the_cpu() {
        let mut c = caps(Features::default(), &["vulkan_scalar:saxpy:f32"]);
        c.dtypes.insert(
            "bf16".into(),
            DTypePath {
                storage: Support::StorageOnly,
                compute: Support::Unsupported,
            },
        );
        let p = plan(Op::Saxpy, DType::Bf16, Shape::default(), &c);
        assert_eq!(p.kind, PathKind::Reference);
    }
}
