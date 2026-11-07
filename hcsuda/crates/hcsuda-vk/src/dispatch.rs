//! Command recording, descriptor management and timing.
//!
//! One `Dispatch` owns a command pool, one command buffer, a descriptor pool and
//! a two-slot timestamp query pool. It is deliberately small and synchronous:
//! H1 only needs "run this kernel on these buffers and tell me how long it took".
//! Asynchronous streams and timeline semaphores arrive with the training work,
//! where they actually buy something.

use std::time::Instant;

use ash::vk;

use crate::buffer::Buffer;
use crate::device::Device;
use crate::error::VkError;
use crate::pipeline::Kernel;

/// Result of one dispatch.
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct Timed {
    /// Wall-clock time from before submit to fence signal, in milliseconds.
    pub wall_ms: f64,
    /// GPU-side time from the timestamp queries, when the queue supports them.
    pub gpu_ms: Option<f64>,
}

pub struct Dispatch {
    device: ash::Device,
    pool: vk::CommandPool,
    cmd: vk::CommandBuffer,
    desc_pool: vk::DescriptorPool,
    query_pool: vk::QueryPool,
    has_timestamps: bool,
    timestamp_period_ns: f32,
    fence: vk::Fence,
}

impl Dispatch {
    pub fn new(dev: &Device) -> Result<Self, VkError> {
        let pool_info = vk::CommandPoolCreateInfo::default()
            .queue_family_index(dev.queue_family)
            .flags(vk::CommandPoolCreateFlags::RESET_COMMAND_BUFFER);
        let pool = unsafe { dev.device.create_command_pool(&pool_info, None)? };
        let alloc = vk::CommandBufferAllocateInfo::default()
            .command_pool(pool)
            .level(vk::CommandBufferLevel::PRIMARY)
            .command_buffer_count(1);
        let cmd = unsafe { dev.device.allocate_command_buffers(&alloc)? }[0];

        let pool_sizes = [vk::DescriptorPoolSize::default()
            .ty(vk::DescriptorType::STORAGE_BUFFER)
            .descriptor_count(64)];
        let desc_info = vk::DescriptorPoolCreateInfo::default()
            .max_sets(16)
            .pool_sizes(&pool_sizes);
        let desc_pool = unsafe { dev.device.create_descriptor_pool(&desc_info, None)? };

        // Timestamps are optional: a queue without `timestampValidBits` still runs
        // kernels, it just reports wall time only.
        let families = unsafe {
            dev.instance
                .get_physical_device_queue_family_properties(dev.physical)
        };
        let has_timestamps = families
            .get(dev.queue_family as usize)
            .map(|q| q.timestamp_valid_bits > 0)
            .unwrap_or(false)
            && dev.features.timestamps;
        let query_pool = unsafe {
            dev.device.create_query_pool(
                &vk::QueryPoolCreateInfo::default()
                    .query_type(vk::QueryType::TIMESTAMP)
                    .query_count(2),
                None,
            )?
        };
        let fence = unsafe {
            dev.device
                .create_fence(&vk::FenceCreateInfo::default(), None)?
        };

        Ok(Self {
            device: dev.device.clone(),
            pool,
            cmd,
            desc_pool,
            query_pool,
            has_timestamps,
            timestamp_period_ns: dev.timestamp_period_ns,
            fence,
        })
    }

    pub fn has_timestamps(&self) -> bool {
        self.has_timestamps
    }

    /// Record and submit one dispatch of `kernel` over `buffers`, then wait.
    ///
    /// `push` must match the shader's push-constant block byte for byte; a
    /// mismatch is a programming error, so it is rejected rather than padded.
    pub fn run(
        &mut self,
        dev: &Device,
        kernel: &Kernel,
        buffers: &[&Buffer],
        push: &[u8],
        groups: (u32, u32, u32),
    ) -> Result<Timed, VkError> {
        if buffers.len() as u32 != kernel.bindings {
            return Err(VkError::Other(format!(
                "kernel expects {} bindings, got {}",
                kernel.bindings,
                buffers.len()
            )));
        }
        if push.len() as u32 != kernel.push_bytes {
            return Err(VkError::Other(format!(
                "kernel expects {} push-constant bytes, got {}",
                kernel.push_bytes,
                push.len()
            )));
        }

        unsafe {
            self.device
                .reset_descriptor_pool(self.desc_pool, vk::DescriptorPoolResetFlags::empty())?;
            let layouts = [kernel.set_layout];
            let set_info = vk::DescriptorSetAllocateInfo::default()
                .descriptor_pool(self.desc_pool)
                .set_layouts(&layouts);
            let sets = self.device.allocate_descriptor_sets(&set_info)?;
            let set = sets[0];

            let infos: Vec<[vk::DescriptorBufferInfo; 1]> = buffers
                .iter()
                .map(|b| {
                    [vk::DescriptorBufferInfo::default()
                        .buffer(b.buffer)
                        .offset(0)
                        .range(b.size)]
                })
                .collect();
            let writes: Vec<vk::WriteDescriptorSet> = infos
                .iter()
                .enumerate()
                .map(|(i, info)| {
                    vk::WriteDescriptorSet::default()
                        .dst_set(set)
                        .dst_binding(i as u32)
                        .descriptor_type(vk::DescriptorType::STORAGE_BUFFER)
                        .buffer_info(info)
                })
                .collect();
            self.device.update_descriptor_sets(&writes, &[]);

            self.device.reset_fences(&[self.fence])?;
            self.device
                .reset_command_buffer(self.cmd, vk::CommandBufferResetFlags::empty())?;
            let begin = vk::CommandBufferBeginInfo::default()
                .flags(vk::CommandBufferUsageFlags::ONE_TIME_SUBMIT);
            self.device.begin_command_buffer(self.cmd, &begin)?;

            if self.has_timestamps {
                self.device
                    .cmd_reset_query_pool(self.cmd, self.query_pool, 0, 2);
                self.device.cmd_write_timestamp(
                    self.cmd,
                    vk::PipelineStageFlags::TOP_OF_PIPE,
                    self.query_pool,
                    0,
                );
            }

            self.device.cmd_bind_pipeline(
                self.cmd,
                vk::PipelineBindPoint::COMPUTE,
                kernel.pipeline,
            );
            self.device.cmd_bind_descriptor_sets(
                self.cmd,
                vk::PipelineBindPoint::COMPUTE,
                kernel.layout,
                0,
                &[set],
                &[],
            );
            if !push.is_empty() {
                self.device.cmd_push_constants(
                    self.cmd,
                    kernel.layout,
                    vk::ShaderStageFlags::COMPUTE,
                    0,
                    push,
                );
            }
            self.device
                .cmd_dispatch(self.cmd, groups.0, groups.1, groups.2);

            if self.has_timestamps {
                self.device.cmd_write_timestamp(
                    self.cmd,
                    vk::PipelineStageFlags::BOTTOM_OF_PIPE,
                    self.query_pool,
                    1,
                );
            }
            self.device.end_command_buffer(self.cmd)?;

            let cmds = [self.cmd];
            let submit = vk::SubmitInfo::default().command_buffers(&cmds);
            let started = Instant::now();
            self.device.queue_submit(dev.queue, &[submit], self.fence)?;
            self.device.wait_for_fences(&[self.fence], true, u64::MAX)?;
            let wall_ms = started.elapsed().as_secs_f64() * 1000.0;

            let gpu_ms = if self.has_timestamps {
                let mut data = [0u64; 2];
                self.device.get_query_pool_results(
                    self.query_pool,
                    0,
                    &mut data,
                    vk::QueryResultFlags::TYPE_64,
                )?;
                let ticks = data[1].saturating_sub(data[0]);
                Some(ticks as f64 * self.timestamp_period_ns as f64 / 1e6)
            } else {
                None
            };

            Ok(Timed { wall_ms, gpu_ms })
        }
    }
}

impl Drop for Dispatch {
    fn drop(&mut self) {
        unsafe {
            self.device.destroy_fence(self.fence, None);
            self.device.destroy_query_pool(self.query_pool, None);
            self.device.destroy_descriptor_pool(self.desc_pool, None);
            self.device.destroy_command_pool(self.pool, None);
        }
    }
}
