//! Instance and logical device creation, plus the capability probe.

use ash::{vk, Entry};
use hcsuda_core::caps::{DTypePath, DeviceCaps, Features, Heap, Support};
use hcsuda_core::DType;

use crate::error::VkError;

pub struct Device {
    pub entry: Entry,
    pub instance: ash::Instance,
    pub physical: vk::PhysicalDevice,
    pub device: ash::Device,
    pub queue: vk::Queue,
    pub queue_family: u32,
    pub props: vk::PhysicalDeviceProperties,
    pub memory: vk::PhysicalDeviceMemoryProperties,
    pub features: Features,
    pub timestamp_period_ns: f32,
    pub subgroup_size: u32,
    pub driver_name: String,
    pub driver_info: String,
}

impl Device {
    /// Create a device. `index` selects a physical device; `None` picks the
    /// best available (discrete before integrated, compute queue required).
    pub fn new(index: Option<usize>) -> Result<Self, VkError> {
        let entry = unsafe { Entry::load()? };
        let app_name = c"HCSUDA";
        let app_info = vk::ApplicationInfo::default()
            .application_name(app_name)
            .application_version(vk::make_api_version(0, 0, 1, 0))
            .api_version(vk::API_VERSION_1_3);
        let create_info = vk::InstanceCreateInfo::default().application_info(&app_info);
        let instance = unsafe { entry.create_instance(&create_info, None)? };

        let physicals = unsafe { instance.enumerate_physical_devices()? };
        if physicals.is_empty() {
            return Err(VkError::NoDevice);
        }
        let chosen = match index {
            Some(i) => *physicals.get(i).ok_or(VkError::NoDevice)?,
            None => pick_best(&instance, &physicals),
        };
        let props = unsafe { instance.get_physical_device_properties(chosen) };
        let memory = unsafe { instance.get_physical_device_memory_properties(chosen) };

        let queue_family = unsafe { instance.get_physical_device_queue_family_properties(chosen) }
            .iter()
            .enumerate()
            .find(|(_, q)| q.queue_flags.contains(vk::QueueFlags::COMPUTE))
            .map(|(i, _)| i as u32)
            .ok_or(VkError::NoDevice)?;

        let features = query_features(&instance, chosen);
        let (driver_name, driver_info) = query_driver(&instance, chosen);
        let subgroup_size = query_subgroup_size(&instance, chosen);
        let extensions = available_extensions(&instance, chosen);
        let mut enabled_extensions: Vec<*const std::ffi::c_char> = Vec::new();
        if extensions.iter().any(|e| e == "VK_KHR_cooperative_matrix") {
            enabled_extensions.push(c"VK_KHR_cooperative_matrix".as_ptr());
        }

        let priorities = [1.0f32];
        let queue_info = vk::DeviceQueueCreateInfo::default()
            .queue_family_index(queue_family)
            .queue_priorities(&priorities);

        // Enable every optional feature that was reported as available.
        let mut f16i8 = vk::PhysicalDeviceFloat16Int8FeaturesKHR::default()
            .shader_float16(features.shader_f16)
            .shader_int8(features.shader_i8);
        let mut s16 = vk::PhysicalDevice16BitStorageFeatures::default()
            .storage_buffer16_bit_access(features.storage_16bit);
        let mut s8 = vk::PhysicalDevice8BitStorageFeatures::default()
            .storage_buffer8_bit_access(features.storage_8bit);
        let mut bda = vk::PhysicalDeviceBufferDeviceAddressFeatures::default()
            .buffer_device_address(features.buffer_device_address);
        let mut coop = vk::PhysicalDeviceCooperativeMatrixFeaturesKHR::default()
            .cooperative_matrix(features.cooperative_matrix);

        let mut features2 = vk::PhysicalDeviceFeatures2::default()
            .features(vk::PhysicalDeviceFeatures::default())
            .push_next(&mut f16i8)
            .push_next(&mut s16)
            .push_next(&mut s8)
            .push_next(&mut bda);
        if features.cooperative_matrix {
            features2 = features2.push_next(&mut coop);
        }

        let mut device_info = vk::DeviceCreateInfo::default()
            .queue_create_infos(std::slice::from_ref(&queue_info))
            .push_next(&mut features2);
        if !enabled_extensions.is_empty() {
            device_info = device_info.enabled_extension_names(&enabled_extensions);
        }
        let device = unsafe { instance.create_device(chosen, &device_info, None)? };
        let queue = unsafe { device.get_device_queue(queue_family, 0) };

        Ok(Self {
            entry,
            instance,
            physical: chosen,
            device,
            queue,
            queue_family,
            props,
            memory,
            features,
            timestamp_period_ns: props.limits.timestamp_period,
            subgroup_size,
            driver_name,
            driver_info,
        })
    }

    pub fn name(&self) -> String {
        self.props
            .device_name_as_c_str()
            .map(|c| c.to_string_lossy().into_owned())
            .unwrap_or_else(|_| "unknown".to_string())
    }

    /// Device API version as `major.minor.patch`.
    pub fn api_version(&self) -> String {
        format!(
            "{}.{}.{}",
            vk::api_version_major(self.props.api_version),
            vk::api_version_minor(self.props.api_version),
            vk::api_version_patch(self.props.api_version)
        )
    }

    pub fn driver_label(&self) -> String {
        format!("{} ({:#x})", self.name(), self.props.driver_version)
    }
}

impl Drop for Device {
    fn drop(&mut self) {
        unsafe {
            self.device.destroy_device(None);
            self.instance.destroy_instance(None);
        }
    }
}

fn pick_best(instance: &ash::Instance, physicals: &[vk::PhysicalDevice]) -> vk::PhysicalDevice {
    let mut best = physicals[0];
    let mut best_score = -1i32;
    for pd in physicals {
        let props = unsafe { instance.get_physical_device_properties(*pd) };
        let has_compute = unsafe { instance.get_physical_device_queue_family_properties(*pd) }
            .iter()
            .any(|q| q.queue_flags.contains(vk::QueueFlags::COMPUTE));
        if !has_compute {
            continue;
        }
        let score = match props.device_type {
            vk::PhysicalDeviceType::DISCRETE_GPU => 3,
            vk::PhysicalDeviceType::INTEGRATED_GPU => 2,
            vk::PhysicalDeviceType::VIRTUAL_GPU => 1,
            _ => 0,
        };
        if score > best_score {
            best = *pd;
            best_score = score;
        }
    }
    best
}

fn available_extensions(instance: &ash::Instance, pd: vk::PhysicalDevice) -> Vec<String> {
    unsafe { instance.enumerate_device_extension_properties(pd) }
        .unwrap_or_default()
        .iter()
        .filter_map(|e| {
            e.extension_name_as_c_str()
                .ok()
                .map(|c| c.to_string_lossy().into_owned())
        })
        .collect()
}

fn query_driver(instance: &ash::Instance, pd: vk::PhysicalDevice) -> (String, String) {
    let mut driver = vk::PhysicalDeviceDriverProperties::default();
    let mut props2 = vk::PhysicalDeviceProperties2::default().push_next(&mut driver);
    unsafe { instance.get_physical_device_properties2(pd, &mut props2) };
    let name = driver
        .driver_name_as_c_str()
        .map(|c| c.to_string_lossy().into_owned())
        .unwrap_or_else(|_| "unknown".to_string());
    let info = driver
        .driver_info_as_c_str()
        .map(|c| c.to_string_lossy().into_owned())
        .unwrap_or_default();
    (name, info)
}

fn query_subgroup_size(instance: &ash::Instance, pd: vk::PhysicalDevice) -> u32 {
    let mut subgroup = vk::PhysicalDeviceSubgroupProperties::default();
    let mut props2 = vk::PhysicalDeviceProperties2::default().push_next(&mut subgroup);
    unsafe { instance.get_physical_device_properties2(pd, &mut props2) };
    subgroup.subgroup_size
}

fn query_features(instance: &ash::Instance, pd: vk::PhysicalDevice) -> Features {
    let mut f16i8 = vk::PhysicalDeviceFloat16Int8FeaturesKHR::default();
    let mut s16 = vk::PhysicalDevice16BitStorageFeatures::default();
    let mut s8 = vk::PhysicalDevice8BitStorageFeatures::default();
    let mut bda = vk::PhysicalDeviceBufferDeviceAddressFeatures::default();
    let mut coop = vk::PhysicalDeviceCooperativeMatrixFeaturesKHR::default();
    let mut dot = vk::PhysicalDeviceShaderIntegerDotProductProperties::default();
    let mut subgroup = vk::PhysicalDeviceSubgroupProperties::default();

    let mut props2 = vk::PhysicalDeviceProperties2::default()
        .push_next(&mut dot)
        .push_next(&mut subgroup);
    unsafe { instance.get_physical_device_properties2(pd, &mut props2) };

    let mut features2 = vk::PhysicalDeviceFeatures2::default()
        .push_next(&mut f16i8)
        .push_next(&mut s16)
        .push_next(&mut s8)
        .push_next(&mut bda)
        .push_next(&mut coop);
    unsafe { instance.get_physical_device_features2(pd, &mut features2) };

    let core = features2.features;
    let props = unsafe { instance.get_physical_device_properties(pd) };
    Features {
        shader_f16: f16i8.shader_float16 == vk::TRUE,
        storage_16bit: s16.storage_buffer16_bit_access == vk::TRUE,
        shader_i8: f16i8.shader_int8 == vk::TRUE,
        storage_8bit: s8.storage_buffer8_bit_access == vk::TRUE,
        shader_f64: core.shader_float64 == vk::TRUE,
        shader_i64: core.shader_int64 == vk::TRUE,
        buffer_device_address: bda.buffer_device_address == vk::TRUE,
        int8_dot: dot.integer_dot_product8_bit_signed_accelerated == vk::TRUE
            && dot.integer_dot_product8_bit_unsigned_accelerated == vk::TRUE,
        int4_dot: dot.integer_dot_product4x8_bit_packed_signed_accelerated == vk::TRUE
            && dot.integer_dot_product4x8_bit_packed_unsigned_accelerated == vk::TRUE,
        cooperative_matrix: coop.cooperative_matrix == vk::TRUE,
        float8_ext: false,
        timestamps: props.limits.timestamp_compute_and_graphics == vk::TRUE,
    }
}

/// Probe one device and return a serialisable capability record.
pub fn probe(index: Option<usize>) -> Result<DeviceCaps, VkError> {
    let device = Device::new(index)?;
    let props = device.props;
    let extensions = available_extensions(&device.instance, device.physical);

    let mut heaps = Vec::new();
    for i in 0..device.memory.memory_heap_count {
        let heap = device.memory.memory_heaps[i as usize];
        // A heap is host-visible when at least one of its memory types is.
        let host_visible = (0..device.memory.memory_type_count).any(|t| {
            let ty = device.memory.memory_types[t as usize];
            ty.heap_index == i
                && ty
                    .property_flags
                    .contains(vk::MemoryPropertyFlags::HOST_VISIBLE)
        });
        heaps.push(Heap {
            index: i,
            size_bytes: heap.size,
            budget_bytes: None,
            device_local: heap.flags.contains(vk::MemoryHeapFlags::DEVICE_LOCAL),
            host_visible,
        });
    }

    let mut dtypes = std::collections::BTreeMap::new();
    for dtype in DType::ALL {
        dtypes.insert(
            dtype.name().to_string(),
            dtype_path(dtype, &device.features),
        );
    }

    let driver_name = device.driver_name.clone();
    let driver_info = device.driver_info.clone();

    Ok(DeviceCaps {
        schema: hcsuda_core::SCHEMA_VERSION,
        name: device.name(),
        vendor_id: props.vendor_id,
        device_id: props.device_id,
        device_type: format!("{:?}", props.device_type),
        api_version: format!(
            "{}.{}.{}",
            vk::api_version_major(props.api_version),
            vk::api_version_minor(props.api_version),
            vk::api_version_patch(props.api_version)
        ),
        driver_name,
        driver_info,
        subgroup_size: device.subgroup_size,
        max_workgroup_invocations: props.limits.max_compute_work_group_invocations,
        max_shared_memory: props.limits.max_compute_shared_memory_size,
        max_storage_range: props.limits.max_storage_buffer_range as u64,
        timestamp_period_ns: props.limits.timestamp_period,
        heaps,
        features: Features {
            float8_ext: extensions.iter().any(|e| e == "VK_EXT_shader_float8"),
            ..device.features.clone()
        },
        dtypes,
        verified_paths: Default::default(),
    })
}

/// Which path a format has on this device. The rules are conservative: a format
/// is only `Native` when dedicated instructions or a first-class storage type
/// exist, otherwise it is `Emulated` or `StorageOnly`.
fn dtype_path(dtype: DType, f: &Features) -> DTypePath {
    let native_f16 = if f.shader_f16 && f.storage_16bit {
        Support::Native
    } else {
        Support::Emulated
    };
    match dtype {
        DType::F64 => DTypePath {
            storage: Support::Native,
            compute: if f.shader_f64 {
                Support::Native
            } else {
                Support::Emulated
            },
        },
        DType::F32 | DType::Tf32 => DTypePath {
            storage: Support::Native,
            compute: Support::Native,
        },
        DType::F16 => DTypePath {
            storage: native_f16,
            compute: native_f16,
        },
        DType::Bf16 => DTypePath {
            // No VK_KHR_shader_bfloat16 on this stack: store as 16-bit, compute
            // by widening to f32.
            storage: if f.storage_16bit {
                Support::Native
            } else {
                Support::Emulated
            },
            compute: Support::Emulated,
        },
        DType::Fp8E4M3 | DType::Fp8E5M2 => DTypePath {
            // Bytes in a storage buffer; no FP8 arithmetic units on RDNA2.
            storage: Support::Native,
            compute: if f.float8_ext {
                Support::Native
            } else {
                Support::Emulated
            },
        },
        DType::I8 => DTypePath {
            storage: if f.storage_8bit {
                Support::Native
            } else {
                Support::Emulated
            },
            compute: if f.int8_dot {
                Support::Native
            } else {
                Support::Emulated
            },
        },
        DType::I4 => DTypePath {
            storage: Support::Native, // packed nibbles in a byte buffer
            compute: if f.int4_dot {
                Support::Native
            } else {
                Support::Emulated
            },
        },
    }
}
