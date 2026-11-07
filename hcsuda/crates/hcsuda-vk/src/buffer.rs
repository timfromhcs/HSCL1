//! Buffers and memory. The integrated GPU exposes a device-local + host-visible
//! heap, so H1 maps directly instead of staging. Staging for discrete GPUs is a
//! later optimisation, not a correctness requirement.

use ash::vk;
use hcsuda_core::caps::Heap;

use crate::device::Device;
use crate::error::VkError;

pub struct Buffer {
    device: ash::Device,
    pub buffer: vk::Buffer,
    pub memory: vk::DeviceMemory,
    pub size: u64,
    pub host_visible: bool,
    pub device_local: bool,
}

impl Buffer {
    pub fn new(
        dev: &Device,
        size: u64,
        usage: vk::BufferUsageFlags,
        prefer_device_local: bool,
    ) -> Result<Self, VkError> {
        let size = size.max(4);
        let info = vk::BufferCreateInfo::default()
            .size(size)
            .usage(usage)
            .sharing_mode(vk::SharingMode::EXCLUSIVE);
        let buffer = unsafe { dev.device.create_buffer(&info, None)? };
        let requirements = unsafe { dev.device.get_buffer_memory_requirements(buffer) };
        let (type_index, host_visible, _device_local) = pick_memory_type(
            &dev.memory,
            requirements.memory_type_bits,
            prefer_device_local,
        )?;
        let flags = dev.memory.memory_types[type_index as usize].property_flags;
        let alloc = vk::MemoryAllocateInfo::default()
            .allocation_size(requirements.size)
            .memory_type_index(type_index);
        let memory = unsafe { dev.device.allocate_memory(&alloc, None)? };
        unsafe { dev.device.bind_buffer_memory(buffer, memory, 0)? };
        Ok(Self {
            device: dev.device.clone(),
            buffer,
            memory,
            size,
            host_visible,
            device_local: flags.contains(vk::MemoryPropertyFlags::DEVICE_LOCAL),
        })
    }

    /// Storage buffer with transfer usage, device-local when possible.
    pub fn storage(dev: &Device, size: u64) -> Result<Self, VkError> {
        Self::new(
            dev,
            size,
            vk::BufferUsageFlags::STORAGE_BUFFER
                | vk::BufferUsageFlags::TRANSFER_SRC
                | vk::BufferUsageFlags::TRANSFER_DST,
            true,
        )
    }

    pub fn upload(&self, dev: &Device, data: &[u8]) -> Result<(), VkError> {
        if !self.host_visible {
            return Err(VkError::Other(
                "buffer is not host visible; staging is not implemented in H1".into(),
            ));
        }
        assert!(data.len() as u64 <= self.size, "upload larger than buffer");
        let ptr = unsafe {
            dev.device.map_memory(
                self.memory,
                0,
                data.len() as u64,
                vk::MemoryMapFlags::empty(),
            )?
        };
        unsafe {
            std::ptr::copy_nonoverlapping(data.as_ptr(), ptr as *mut u8, data.len());
            dev.device.unmap_memory(self.memory);
        }
        Ok(())
    }

    pub fn upload_f32(&self, dev: &Device, values: &[f32]) -> Result<(), VkError> {
        let bytes: Vec<u8> = values.iter().flat_map(|v| v.to_le_bytes()).collect();
        self.upload(dev, &bytes)
    }

    pub fn upload_u32(&self, dev: &Device, values: &[u32]) -> Result<(), VkError> {
        let bytes: Vec<u8> = values.iter().flat_map(|v| v.to_le_bytes()).collect();
        self.upload(dev, &bytes)
    }

    pub fn read_i32(&self, dev: &Device, len: usize) -> Result<Vec<i32>, VkError> {
        let mut bytes = vec![0u8; len * 4];
        self.download(dev, &mut bytes)?;
        Ok(bytes
            .chunks_exact(4)
            .map(|c| i32::from_le_bytes([c[0], c[1], c[2], c[3]]))
            .collect())
    }

    pub fn download(&self, dev: &Device, out: &mut [u8]) -> Result<(), VkError> {
        if !self.host_visible {
            return Err(VkError::Other("buffer is not host visible".into()));
        }
        let len = out.len().min(self.size as usize);
        let ptr = unsafe {
            dev.device
                .map_memory(self.memory, 0, len as u64, vk::MemoryMapFlags::empty())?
        };
        unsafe {
            std::ptr::copy_nonoverlapping(ptr as *const u8, out.as_mut_ptr(), len);
            dev.device.unmap_memory(self.memory);
        }
        Ok(())
    }

    pub fn read_f32(&self, dev: &Device, len: usize) -> Result<Vec<f32>, VkError> {
        let mut bytes = vec![0u8; len * 4];
        self.download(dev, &mut bytes)?;
        Ok(bytes
            .chunks_exact(4)
            .map(|c| f32::from_le_bytes([c[0], c[1], c[2], c[3]]))
            .collect())
    }
}

impl Drop for Buffer {
    fn drop(&mut self) {
        unsafe {
            self.device.destroy_buffer(self.buffer, None);
            self.device.free_memory(self.memory, None);
        }
    }
}

fn pick_memory_type(
    memory: &vk::PhysicalDeviceMemoryProperties,
    type_bits: u32,
    prefer_device_local: bool,
) -> Result<(u32, bool, bool), VkError> {
    let required = vk::MemoryPropertyFlags::HOST_VISIBLE | vk::MemoryPropertyFlags::HOST_COHERENT;
    let mut candidates: Vec<(u32, vk::MemoryPropertyFlags)> = Vec::new();
    for i in 0..memory.memory_type_count {
        if type_bits & (1 << i) == 0 {
            continue;
        }
        let flags = memory.memory_types[i as usize].property_flags;
        if flags.contains(required) {
            candidates.push((i, flags));
        }
    }
    if candidates.is_empty() {
        return Err(VkError::NoMemoryType);
    }
    let pick = if prefer_device_local {
        candidates
            .iter()
            .find(|(_, f)| f.contains(vk::MemoryPropertyFlags::DEVICE_LOCAL))
            .copied()
            .unwrap_or(candidates[0])
    } else {
        candidates[0]
    };
    Ok((
        pick.0,
        pick.1.contains(vk::MemoryPropertyFlags::HOST_VISIBLE),
        pick.1.contains(vk::MemoryPropertyFlags::DEVICE_LOCAL),
    ))
}

/// Human-readable heap summary for reports.
pub fn heap_summary(heaps: &[Heap]) -> String {
    heaps
        .iter()
        .map(|h| {
            format!(
                "heap{}: {:.2} GiB{}{}",
                h.index,
                h.size_bytes as f64 / (1u64 << 30) as f64,
                if h.device_local { " device-local" } else { "" },
                if h.host_visible { " host-visible" } else { "" }
            )
        })
        .collect::<Vec<_>>()
        .join(", ")
}
