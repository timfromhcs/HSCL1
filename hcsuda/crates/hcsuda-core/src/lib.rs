//! HCSUDA core.
//!
//! Everything here is device-independent and deterministic: data types, the
//! capability model, the conservative planner and the CPU reference kernels that
//! every GPU path is verified against. No Vulkan, no threads, no hidden state.

pub mod caps;
pub mod dtype;
pub mod fp8;
pub mod planner;
pub mod quant;
pub mod reference;
pub mod report;
pub mod tensor;

pub use caps::{DTypePath, DeviceCaps, Features, Heap, Support};
pub use dtype::{DType, Tolerance};
pub use planner::{PathKind, Plan, Tile};
pub use report::BenchRow;
pub use tensor::Tensor;

/// Version of the HCSUDA capability/report schema. Bumped whenever a field is
/// removed or changes meaning, so old JSON evidence stays interpretable.
pub const SCHEMA_VERSION: u32 = 1;
