# Privacy Mode: what it is, what it is not

Status of this document: written against `HSCL1-rc6` (`4a0d48a3…`) on 2026-11-11, from a booted live guest.
Everything below is either measured in that guest or explicitly marked as untested.

**HSCL1's Privacy Mode is not Tails.** It borrows properties that are cheap to provide honestly - a live session
whose writes stay in RAM, no swap on disk, no core dumps, no automatic mounting of internal disks, and a
fail-closed Tor launcher - and it says so instead of claiming anonymity. If your safety depends on strong
anonymity, use the official Tails release, which is a separate project with its own threat model.

## What the live medium actually does (measured)

`hscl privacy status` in the rc6 live guest (`artifacts/boot-cc-miner/cm3-cli-status.png`):

```text
session:               ephemeral (volatile RAM overlay)
ephemeral overlay:     active (volatile RAM overlayfs)
root filesystem:       overlay
zram memory swap:      active (compressed zram in RAM)
persistent disk swap:  none
core dumps:            disabled (fs.suid_dumpable = 0)
internal disk mounts:  none (host disks unmounted)
tor service:           inactive
tor browser:           not installed
```

- The root filesystem is an overlay whose upper layer lives in RAM; a shutdown discards it.
- Swap is zram only - compressed pages in RAM, never a disk partition or swap file.
- Core dumps are off, so a crash of a privacy-sensitive process does not write memory to disk.
- Internal disks are not mounted by the live medium; nothing is copied out of them.
- The session does **not** ship Tor Browser and the Tor daemon is inactive until something starts it.

## What HSCL1 provides for Tor

- `hscl privacy tor status` reports whether a local SOCKS proxy answers and whether a Tor Browser launcher is
  available.
- `hscl privacy tor launch` is **fail-closed**: if Tor Browser is not installed or the proxy does not answer, it
  refuses to start anything instead of falling back to a direct connection.
- `hscl privacy session explain` prints the architecture of the ephemeral session.

Installing Tor Browser is a user action from the upstream distribution channel; HSCL1 does not bundle it.

## What is *not* provided, and is not claimed

| Not provided | Consequence |
|---|---|
| A verified network kill switch | Nothing in this tree captures packets to prove that no non-Tor traffic leaves. Do not treat the Privacy Mode as leak-proof. |
| Encryption of the live session's RAM owner | A live overlay protects against later disk forensics, not against a compromised firmware or a running attacker. |
| Persistent storage opt-in | There is no encrypted persistence volume yet; the session is discarded at shutdown. |
| Hiding of hardware identifiers | CPU, disks and firmware are still visible to the running system. |
| Protection against a compromised host or hypervisor | A VM inherits the host's trust. |
| Tor Browser fingerprint hardening | The browser's own defaults apply; HSCL1 does not modify them. |

## How to check it yourself

```bash
hscl privacy status                 # the table above
hscl privacy tor status             # SOCKS + launcher availability
hscl privacy tor launch             # refuses without Tor Browser (fail-closed)
hscl privacy session explain        # architecture, in plain language
hscl security status                # AppArmor, UFW, Secure Boot, LUKS
```

In a live guest, `free -m`, `findmnt /`, `lsblk` and `swapon --show` should show the same picture: overlay root,
zram swap, no mounted internal disks.

## Relationship to the other two modes

- **Workstation**: an installed, persistent system; the privacy properties above do not apply.
- **Security Lab**: isolated containers or VMs; unrelated to this mode, and it never mounts a host home
  directory.
- **Privacy**: this document. A live session with the properties above and no claim beyond them.

See also `docs/THREAT_MODEL.md`, `docs/SECURITY_LAB.md` and `docs/KNOWN_LIMITATIONS.md`.
