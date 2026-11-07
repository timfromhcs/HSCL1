//! Compute pipelines from SPIR-V.

use ash::vk;

use crate::device::Device;
use crate::error::VkError;

pub struct Kernel {
    device: ash::Device,
    pub pipeline: vk::Pipeline,
    pub layout: vk::PipelineLayout,
    pub set_layout: vk::DescriptorSetLayout,
    pub bindings: u32,
    pub push_bytes: u32,
}

impl Kernel {
    /// `bindings` storage buffers at binding 0..n, plus one push-constant block.
    pub fn new(
        dev: &Device,
        spirv: &[u8],
        bindings: u32,
        push_bytes: u32,
    ) -> Result<Self, VkError> {
        assert!(bindings > 0, "a kernel needs at least one binding");
        let binding_flags: Vec<vk::DescriptorSetLayoutBinding> = (0..bindings)
            .map(|i| {
                vk::DescriptorSetLayoutBinding::default()
                    .binding(i)
                    .descriptor_type(vk::DescriptorType::STORAGE_BUFFER)
                    .descriptor_count(1)
                    .stage_flags(vk::ShaderStageFlags::COMPUTE)
            })
            .collect();
        let set_info = vk::DescriptorSetLayoutCreateInfo::default().bindings(&binding_flags);
        let set_layout = unsafe { dev.device.create_descriptor_set_layout(&set_info, None)? };

        let ranges = [vk::PushConstantRange::default()
            .stage_flags(vk::ShaderStageFlags::COMPUTE)
            .offset(0)
            .size(push_bytes)];
        let layout_info = vk::PipelineLayoutCreateInfo::default()
            .set_layouts(std::slice::from_ref(&set_layout))
            .push_constant_ranges(&ranges);
        let layout = unsafe { dev.device.create_pipeline_layout(&layout_info, None)? };

        // SPIR-V is a byte slice whose alignment is not guaranteed, so it is
        // re-packed into words instead of cast.
        if spirv.len() % 4 != 0 {
            return Err(VkError::Other(format!(
                "SPIR-V length {} is not a multiple of 4",
                spirv.len()
            )));
        }
        let words: Vec<u32> = spirv
            .chunks_exact(4)
            .map(|c| u32::from_le_bytes([c[0], c[1], c[2], c[3]]))
            .collect();
        let module_info = vk::ShaderModuleCreateInfo::default().code(&words);
        let module = unsafe { dev.device.create_shader_module(&module_info, None)? };
        let stage = vk::PipelineShaderStageCreateInfo::default()
            .stage(vk::ShaderStageFlags::COMPUTE)
            .module(module)
            .name(c"main");
        let pipeline_info = vk::ComputePipelineCreateInfo::default()
            .stage(stage)
            .layout(layout);
        let pipelines = unsafe {
            dev.device.create_compute_pipelines(
                vk::PipelineCache::null(),
                std::slice::from_ref(&pipeline_info),
                None,
            )
        }
        .map_err(|(_, e)| e)?;
        unsafe { dev.device.destroy_shader_module(module, None) };

        Ok(Self {
            device: dev.device.clone(),
            pipeline: pipelines[0],
            layout,
            set_layout,
            bindings,
            push_bytes,
        })
    }

    /// Build a kernel from a shader compiled into the binary.
    pub fn from_shader(
        dev: &Device,
        name: &str,
        bindings: u32,
        push_bytes: u32,
    ) -> Result<Self, VkError> {
        let spirv = crate::shader(name).ok_or_else(|| VkError::ShaderNotFound(name.to_string()))?;
        Self::new(dev, spirv, bindings, push_bytes)
    }
}

impl Drop for Kernel {
    fn drop(&mut self) {
        unsafe {
            self.device.destroy_pipeline(self.pipeline, None);
            self.device.destroy_pipeline_layout(self.layout, None);
            self.device
                .destroy_descriptor_set_layout(self.set_layout, None);
        }
    }
}
