//! HCSUDA Vulkan backend.
//!
//! Scope of this crate: device selection, capability probing, memory, dispatch
//! and timing. It contains no model logic and no heuristics about what is fast;
//! that is the planner's job in `hcsuda-core`.

pub mod buffer;
pub mod device;
pub mod dispatch;
pub mod error;
pub mod pipeline;

pub use buffer::Buffer;
pub use device::{probe, Device};
pub use dispatch::{Dispatch, Timed};
pub use error::VkError;
pub use pipeline::Kernel;

/// Re-exported so a consumer needs one dependency, not two.
pub use hcsuda_core::caps::DeviceCaps;

/// Shaders compiled by `build.rs`.
pub mod shaders {
    include!(concat!(env!("OUT_DIR"), "/shaders.rs"));
}

/// Look up a compiled shader by stem (e.g. `"saxpy"`).
pub fn shader(name: &str) -> Option<&'static [u8]> {
    shaders::SHADERS
        .iter()
        .find(|(n, _)| *n == name)
        .map(|(_, bytes)| *bytes)
}

/// True when the build had `glslc` and every shader compiled.
pub fn shaders_available() -> bool {
    shaders::SHADERS_AVAILABLE
}
