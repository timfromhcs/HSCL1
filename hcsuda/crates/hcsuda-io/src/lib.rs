//! Model file I/O for HCSUDA.
//!
//! Model files are untrusted input. Nothing here executes, deserialises code,
//! or allocates from a length it has not checked against the file size.

pub mod dequant;
pub mod gguf;

pub use gguf::{GgmlType, GgufError, GgufFile, MetaValue, TensorInfo};
