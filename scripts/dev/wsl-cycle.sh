#!/usr/bin/env bash
# HSCL1 full pipeline (owner rule 2026-11-08: everything in WSL/Linux, repo of record on E:).
#
#   dev pull   -> E: -> ~/src/HSCL1-build
#   dev build  -> pull + cargo release build + cargo test
#   dev push   -> ~/src/HSCL1-build -> E: (after green tests)
#   dev iso    -> pull + cargo test, then remaster-iso.sh (fast or release) into ~/hscl1-build/out
#   dev vm     -> boot the newest ISO in QEMU/KVM, wait for desktop, screenshot
#   dev probe  -> boot newest ISO + read-only in-guest probes via the Workshop API (e2e_probe.py)
#   dev mcp    -> exercise the workshop MCP server protocol directly (initialize/tools/list/tools/call)
#   dev all    -> pull + build + iso --fast + vm + probe + mcp + push
#   dev status -> inventory: repos, ISOs, memory, disk, KVM
#
# Exit code is nonzero as soon as a step fails; every step logs to stdout with a step tag.
set -Eeuo pipefail
export PATH="$HOME/.cargo/bin:$PATH"

REPO_E=/mnt/e/hcslinux222
REPO_L="$HOME/src/HSCL1-build"
BUILD="$HOME/hscl1-build"
OUT="$BUILD/out"
EXCLUDES=(--exclude 'target/' --exclude '.git/' --exclude 'node_modules/' \
          --exclude 'artifacts/' --exclude '*.iso' --exclude '*.squashfs' \
          --exclude 'dist/' --exclude '__pycache__/')
STEP="dev"

log() { printf '[%s] %s\n' "$STEP" "$*"; }

sync_in() {
  mkdir -p "$REPO_L"
  rsync -a --delete "${EXCLUDES[@]}" "$REPO_E/" "$REPO_L/"
  sync
  log "synced E: -> Linux"
}

sync_out() {
  sync
  rsync -a "${EXCLUDES[@]}" "$REPO_L/" "$REPO_E/"
  sync
  log "synced Linux -> E:"
}

newest_iso() {
  ls -1t "$OUT"/HSCL1*.iso 2>/dev/null | head -n 1 || true
}

cmd="${1:-status}"; shift || true
case "$cmd" in

  pull)
    sync_in ;;

  build)
    STEP=build; sync_in
    cd "$REPO_L"
    cargo build --release -p hscl
    cargo test --release -p hscl
    log "build+test green"
    sync_out ;;

  push)
    STEP=push; sync_out ;;

  iso)
    STEP=iso; sync_in
    cd "$REPO_L"
    cargo test --release -p hscl
    mode=release; [ "${1:-}" = "--fast" ] && { mode=fast; shift || true; }
    fast_flag=()
    [ "$mode" = fast ] && fast_flag=(--fast)
    if [ -n "${1:-}" ]; then
      out_path="$1"; shift || true
      log "remaster ISO ($mode) -> $out_path"
      scripts/remaster-iso.sh "${fast_flag[@]}" --out "$out_path" --force
    else
      log "remaster ISO ($mode)"
      scripts/remaster-iso.sh "${fast_flag[@]}" \
        --out "$OUT/HSCL1-dev-$(date -u +%m%d%H%M).iso" --force
    fi
    newest_iso
    log "ISO built"
    sync_out
    ;;

  vm)
    STEP=vm
    iso="${1:-$(newest_iso)}"
    [ -n "$iso" ] && [ -f "$iso" ] || { log "no ISO found in $OUT" >&2; exit 2; }
    vmdir="$BUILD/vmcheck"; rm -rf "$vmdir"; mkdir -p "$vmdir"
    cd "$REPO_L"
    log "boot $iso (KVM, UEFI)"
    python3 scripts/qemu_boot_test.py "$iso" "$vmdir" || { log "boot test FAILED"; exit 1; }
    log "desktop reached, evidence in $vmdir"
    ;;

  probe)
    STEP=probe
    iso="${1:-$(newest_iso)}"
    [ -n "$iso" ] && [ -f "$iso" ] || { log "no ISO found in $OUT" >&2; exit 2; }
    pdir="$BUILD/probe"; rm -rf "$pdir"; mkdir -p "$pdir"
    cat > "$pdir/probes.json" <<'EOF'
{"version": "/usr/bin/hscl --version",
 "daemon": "systemctl is-active hscl-workshopd || service hscl-workshopd status",
 "desktop": "echo $XDG_CURRENT_DESKTOP; plasmashell --version",
 "security": "/usr/lib/hscl/security/security-baseline.sh check 2>&1 | tail -5"}
EOF
    cd "$REPO_L"
    log "boot + probe $iso via Workshop API"
    python3 scripts/workshop/e2e_probe.py "$iso" "$pdir" "$pdir/probes.json"
    cat "$pdir/probe.json"
    log "probes done, evidence in $pdir"
    ;;

  mcp)
    STEP=mcp
    cd "$REPO_L"
    python3 scripts/dev/mcp_selftest.py
    log "MCP protocol self-test green"
    ;;

  all)
    STEP=all
    "$0" build
    "$0" iso --fast
    "$0" vm
    "$0" probe
    "$0" mcp
    STEP=all; log "pipeline complete"; sync_out
    ;;

  status)
    STEP=status
    log "repo-L : $REPO_L ($(du -sh "$REPO_L" 2>/dev/null | cut -f1))"
    log "repo-E : $REPO_E"
    log "ISOs   :"
    ls -1t "$OUT"/HSCL1*.iso 2>/dev/null | head -3 | while read -r i; do
      log "         $(basename "$i")  $(date -u -r "$i" +%m-%d\ %H:%M)  $(du -h "$i" | cut -f1)"
    done
    mem_avail=$(awk '/MemAvailable/ {print int($2/1024)}' /proc/meminfo)
    log "mem    : ${mem_avail} MB available (remaster needs >= 3000)"
    log "disk   : $(df -h "$BUILD" | awk 'NR==2{print $4 " free"}')  (remaster needs >= 30 GB)"
    if [ -w /dev/kvm ]; then log "kvm    : yes"; else log "kvm    : no (TCG fallback)"; fi
    ;;

  *)
    grep -A1 '^#   dev' "$0" >&2
    exit 2 ;;
esac
