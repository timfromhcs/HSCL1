# Troubleshooting

| Problem | What to try |
|---|---|
| Black screen in a VM | Use standard VGA and disable 3D acceleration. |
| Very slow boot | Enable hardware acceleration (KVM or WHPX); software emulation needs several minutes. |
| The installer says "no partitions" | The virtual machine has no disk attached. Attach a disposable virtual disk. |
| `hscl doctor` reports AppArmor disabled | Normal inside WSL or kernels without AppArmor; on a real HSCL1 install it should be enabled. |
