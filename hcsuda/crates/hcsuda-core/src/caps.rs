//! Device capability model.
//!
//! A capability record is what the planner is allowed to reason about. Anything
//! not positively reported here is treated as unsupported: that is the
//! "conservative" half of the conservative planner.

use std::collections::{BTreeMap, BTreeSet};

use serde::{Deserialize, Serialize};

use crate::dtype::DType;

/// How well a device can handle a format.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Support {
    /// Dedicated hardware instructions (or a first-class driver path).
    Native,
    /// Works through conversion or a software path.
    Emulated,
    /// Can be stored and moved, but not computed in.
    StorageOnly,
    /// Not usable at all.
    Unsupported,
}

impl Support {
    pub fn can_compute(self) -> bool {
        matches!(self, Support::Native | Support::Emulated)
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub struct DTypePath {
    pub storage: Support,
    pub compute: Support,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct Heap {
    pub index: u32,
    pub size_bytes: u64,
    pub budget_bytes: Option<u64>,
    pub device_local: bool,
    pub host_visible: bool,
}

/// Feature flags that matter for kernel selection.
#[derive(Debug, Clone, Default, PartialEq, Eq, Serialize, Deserialize)]
pub struct Features {
    pub shader_f16: bool,
    pub storage_16bit: bool,
    pub shader_i8: bool,
    pub storage_8bit: bool,
    pub shader_f64: bool,
    pub shader_i64: bool,
    pub buffer_device_address: bool,
    /// `VK_KHR_shader_integer_dot_product`: 8-bit dot product accelerated.
    pub int8_dot: bool,
    /// 4x8-bit packed dot product accelerated (int4 storage, int8 math).
    pub int4_dot: bool,
    /// `VK_KHR_cooperative_matrix` present.
    pub cooperative_matrix: bool,
    /// `VK_EXT_shader_float8` present (RDNA4+; absent on the 680M).
    pub float8_ext: bool,
    pub timestamps: bool,
}

/// A full capability record for one device, as reported by the backend.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct DeviceCaps {
    pub schema: u32,
    pub name: String,
    pub vendor_id: u32,
    pub device_id: u32,
    pub device_type: String,
    pub api_version: String,
    pub driver_name: String,
    pub driver_info: String,
    pub subgroup_size: u32,
    pub max_workgroup_invocations: u32,
    pub max_shared_memory: u32,
    pub max_storage_range: u64,
    pub timestamp_period_ns: f32,
    pub heaps: Vec<Heap>,
    pub features: Features,
    /// Per-format storage/compute path.
    pub dtypes: BTreeMap<String, DTypePath>,
    /// Paths that passed the differential gate on this device, e.g.
    /// `vk:gemm:f32:tiled`. The planner refuses everything else.
    #[serde(default)]
    pub verified_paths: BTreeSet<String>,
}

impl DeviceCaps {
    pub fn dtype(&self, dtype: DType) -> DTypePath {
        self.dtypes.get(dtype.name()).copied().unwrap_or(DTypePath {
            storage: Support::Unsupported,
            compute: Support::Unsupported,
        })
    }

    pub fn total_device_local_bytes(&self) -> u64 {
        self.heaps
            .iter()
            .filter(|h| h.device_local)
            .map(|h| h.size_bytes)
            .sum()
    }

    /// Usable device memory: the smaller of size and budget, minus headroom.
    pub fn usable_device_bytes(&self, headroom: u64) -> u64 {
        self.heaps
            .iter()
            .filter(|h| h.device_local)
            .map(|h| h.budget_bytes.unwrap_or(h.size_bytes))
            .sum::<u64>()
            .saturating_sub(headroom)
    }

    pub fn path_is_verified(&self, key: &str) -> bool {
        self.verified_paths.contains(key)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn caps() -> DeviceCaps {
        let mut dtypes = BTreeMap::new();
        dtypes.insert(
            "f32".to_string(),
            DTypePath {
                storage: Support::Native,
                compute: Support::Native,
            },
        );
        dtypes.insert(
            "fp8e4m3".to_string(),
            DTypePath {
                storage: Support::StorageOnly,
                compute: Support::Emulated,
            },
        );
        DeviceCaps {
            schema: crate::SCHEMA_VERSION,
            name: "test".into(),
            vendor_id: 0,
            device_id: 0,
            device_type: "cpu".into(),
            api_version: "1.3".into(),
            driver_name: "none".into(),
            driver_info: "none".into(),
            subgroup_size: 64,
            max_workgroup_invocations: 1024,
            max_shared_memory: 32768,
            max_storage_range: u32::MAX as u64,
            timestamp_period_ns: 10.0,
            heaps: vec![Heap {
                index: 0,
                size_bytes: 8 << 30,
                budget_bytes: Some(6 << 30),
                device_local: true,
                host_visible: false,
            }],
            features: Features::default(),
            dtypes,
            verified_paths: BTreeSet::new(),
        }
    }

    #[test]
    fn unknown_dtype_is_unsupported() {
        let c = caps();
        assert_eq!(c.dtype(DType::Bf16).compute, Support::Unsupported);
        assert_eq!(c.dtype(DType::F32).compute, Support::Native);
    }

    #[test]
    fn usable_memory_uses_budget_and_headroom() {
        let c = caps();
        assert_eq!(c.usable_device_bytes(1 << 30), (6u64 << 30) - (1 << 30));
        assert_eq!(c.total_device_local_bytes(), 8 << 30);
    }

    #[test]
    fn storage_only_cannot_compute() {
        assert!(!Support::StorageOnly.can_compute());
        assert!(Support::Emulated.can_compute());
    }
}
