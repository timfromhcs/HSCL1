#!/usr/bin/env bash
# Report the state of the Secure Boot test VM and its output directory.
set -u
echo "== qemu processes"
ps -eo pid,etime,pcpu,rss,comm | grep -E 'qemu-system' | grep -v grep || echo none
echo
echo "== ~/sb-test"
ls -la "$HOME/sb-test" 2>/dev/null | sed -n '2,16p'
echo
echo "== qemu.log (first 8 lines)"
head -8 "$HOME/sb-test/qemu.log" 2>/dev/null || echo empty
