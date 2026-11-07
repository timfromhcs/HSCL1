use ash::vk;

#[derive(Debug, thiserror::Error)]
pub enum VkError {
    #[error("Vulkan loader not available: {0}")]
    Loader(String),
    #[error("Vulkan call failed: {0}")]
    Vk(#[from] vk::Result),
    #[error("no Vulkan device with a compute queue was found")]
    NoDevice,
    #[error("no shaders were compiled (glslc missing at build time)")]
    NoShaders,
    #[error("shader '{0}' was not compiled into this binary")]
    ShaderNotFound(String),
    #[error("no memory type satisfies the request")]
    NoMemoryType,
    #[error("{0}")]
    Other(String),
}

impl From<ash::LoadingError> for VkError {
    fn from(value: ash::LoadingError) -> Self {
        VkError::Loader(value.to_string())
    }
}
