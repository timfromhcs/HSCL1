# Troubleshooting

| Problem | What to try |
|---|---|
| Black screen in a VM | Use standard VGA and disable 3D acceleration. |
| Very slow boot | Enable hardware acceleration (KVM or WHPX); software emulation needs several minutes. |
| The installer says "no partitions" | The virtual machine has no disk attached. Attach a disposable virtual disk. |
| The installer stops with `hscl-verify-esp: … did not populate the EFI system partition` | The installer finished writing the system but no EFI boot loader landed on the EFI partition, so the machine would not start. Nothing was lost: start the installation again, and if it repeats, report the exact message from `/var/log/calamares.log`. |
| The installer window disappears right after starting | Known intermittent fault (about one start in six to twelve). On current images the launcher restarts it by itself; on older ones simply start it again. |
| After login the desktop shows a "Welcome Center" with KDE pages | Old images only. Current images open the Welcome Center on the HSCL1 page, and the first login does not open it at all. |
| `hscl doctor` reports AppArmor disabled | Normal inside WSL or kernels without AppArmor; on a real HSCL1 install it should be enabled. |
