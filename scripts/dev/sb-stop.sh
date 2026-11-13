#!/usr/bin/env bash
# Stop the Secure Boot test VM by the PID it reports, keep the evidence, and summarise the failure.
set -u
pid=$(ps -eo pid,comm | awk '$2 ~ /^qemu-system/ {print $1; exit}')
if [ -n "${pid:-}" ]; then
  echo "stopping qemu pid $pid (started by this session's harness)"
  kill "$pid" 2>/dev/null || true
  sleep 3
fi
out=/mnt/e/hcslinux222/artifacts/boot-sb-kvm
mkdir -p "$out"
cp "$HOME/sb-test/qemu.log" "$out/qemu.log" 2>/dev/null || true
cp "$HOME/sb-test/shot-001.png" "$out/shot-001.png" 2>/dev/null || true
{
  echo "HSCL1 Secure Boot probe on this host - BLOCKED"
  echo
  echo "Attempt 1, QEMU on Windows (WHPX), -machine q35,smm=on:"
  grep -m1 'System Management Mode' /mnt/e/hcslinux222/artifacts/boot-sb-0.1.8/qemu.log 2>/dev/null || echo "(log missing)"
  echo
  echo "Attempt 2, QEMU in WSL with KVM (nested virtualization, /dev/kvm present):"
  grep -m1 'KVM: entry failed' "$out/qemu.log" 2>/dev/null || echo "(no KVM entry error recorded)"
  grep -m1 'SMM=1' "$out/qemu.log" 2>/dev/null || true
} | tee "$out/SUMMARY.txt"
echo
echo "evidence: $out/SUMMARY.txt, qemu.log, shot-001.png"
