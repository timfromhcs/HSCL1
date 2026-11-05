# HSCL1 — Autonomous Build, Product, Security & Release Instructions

> **Product:** HSCL1 OS  
> **Publisher:** HCSMEDIA  
> **Credit:** Made with love by hcsmedia  
> **Repository target:** `HSCL1` (detect an existing repository and its configured remote before creating anything)  
> **Target release:** `v1.0.0` — stable, tested, documented, hardened to the stated threat model, and published  
> **Primary architecture:** Ubuntu 26.04 LTS / Kubuntu 26.04 LTS package foundation, KDE Plasma 6.6 LTS desktop, custom HCS experience, Calamares installer, bootable hybrid Live/Installer ISO  
> **Supported CPU architecture for v1:** `x86_64` / `amd64`  
> **Languages:** English (`en`), German (`de`), French (`fr`)  
> **Website:** Vercel-deployable project landing page with verified release downloads and installation guides

This file is the product contract and autonomous execution plan. Follow it as an engineering specification, not as a loose inspiration document. Build real software, real bootable media, real installation paths, real tests, and real documentation. Never replace missing functionality with mock screens, fake command output, placeholder downloads, or claims that a feature is complete when it is not.

---

# 0. ROLE, MISSION, AND OPERATING RULES

## 0.1 Your role

Act as a cross-functional operating-system engineering team with these responsibilities:

- Principal Linux distribution architect.
- Ubuntu/Debian package and image-build engineer.
- KDE Plasma / Qt / Wayland desktop engineer.
- Linux installer, bootloader, storage, and initramfs engineer.
- Linux hardening and threat-model engineer.
- Container and virtualization engineer.
- Rust / Python / Bash systems engineer.
- UX, visual identity, accessibility, and localization designer.
- QA, release engineering, supply-chain security, and documentation engineer.
- Frontend engineer for the Vercel landing page.

Work autonomously within the user's authorized repository and connected tools. Use the available GitHub, browser, MCP, coding, design, terminal, and test tools when useful. Prefer inspectable, reproducible commands and source changes over manual clicking. Keep a durable engineering log so that work can resume without guessing what has already been completed.

## 0.2 Mission

Build **HSCL1**, a polished, friendly, keyboard-capable Linux operating system that unifies the strongest practical ideas of:

1. **Omarchy:** opinionated defaults, beautiful themes, keyboard-driven productivity, tiling, a curated developer workflow, a central control menu, and an excellent CLI.
2. **Ubuntu:** a supported and familiar Linux foundation, broad hardware compatibility, accessible software installation, a conventional desktop, and practical daily-driver functionality.
3. **Kali Linux:** a curated penetration-testing and security-research toolchain, but isolated from the host package system and designed for authorized labs.
4. **Tails:** privacy-oriented workflows, disposable sessions, Tor integration, encrypted optional persistence, and explicit separation between normal browsing and high-privacy sessions.
5. **macOS + Windows 10 interaction metaphors:** a polished top menu/status bar, a centered app dock, familiar windows, a discoverable Start/Applications menu, task switching, snap/tiling layouts, and a settings/control-center experience. Do not copy Apple or Microsoft branding, artwork, icons, or proprietary interface assets. Create an original HCS design language.

The same OS image must be usable in a virtual machine and on supported physical PCs. One hybrid ISO should offer a live desktop and a graphical installer. The installed system and the live environment should share the same visual identity and core navigation wherever their different security and persistence models permit.

The final outcome is not just an ISO. It is a complete release system:

- A buildable, installable OS source repository.
- A live/installer ISO that has actually booted in automated VM tests.
- A real installation path to a disk-backed system.
- Daily-driver, Security Lab, and Privacy workflows with honest security boundaries.
- An HCS control center and CLI.
- A local AI/model setup workflow with hardware detection and safe CPU fallback.
- Automated tests, self-repair loops, SBOM, checksums, signatures, and release notes.
- An excellent multilingual README and Vercel landing page.
- A tagged GitHub `v1.0.0` release with real tested artifacts, if repository permissions and release credentials exist.

## 0.3 Non-negotiable rules

1. **No fake completion.** A package manifest is not a bootable ISO. An ISO that has not booted is not tested. A UI mockup is not a working control center. A command that only prints success is not implemented.
2. **Never destroy user data.** Do not run a disk-wiping installer, `dd`, `wipefs`, `mkfs`, `sgdisk --zap-all`, destructive partitioning, or real-host installation in development. All installer end-to-end tests must use disposable virtual disks. A real installer must require an explicit, informed, final confirmation before erasing any selected disk.
3. **Never mix distribution repositories.** Do not add Kali rolling repositories to the Ubuntu host. Do not mix Debian testing/unstable, Ubuntu interim, PPAs, or random third-party repositories into the core OS. The host uses the pinned Ubuntu 26.04 (`resolute`) repositories plus a separately signed HCS repository only if it is truly needed and maintained.
4. **Do not claim HSCL1 is Tails.** Do not claim anonymity, forensic invisibility, anti-surveillance guarantees, or Tails-equivalent security. The HSCL1 Privacy Session is a privacy-oriented feature with an explicit, tested threat model. The authentic Tails distribution remains a separate project and may be launched as a separately downloaded, signature-verified ISO.
5. **Do not claim Kali certification.** HSCL1 is not an official Kali release and is not endorsed by Offensive Security. Kali tools run in isolated containers or virtual machines, not by adding Kali repositories to the base system.
6. **Preserve Secure Boot where feasible.** Do not tell users to disable Secure Boot as the default. Use signed Ubuntu shim/GRUB/kernel components where the chosen image pipeline supports them. If the custom ISO cannot be Secure Boot compatible in v1, disclose the exact limitation and do not imply it works.
7. **No broad root execution from the desktop.** The UI and CLI run unprivileged by default. Privileged operations must use narrowly scoped PolicyKit actions, a reviewed helper, or explicit `sudo` commands. Never run arbitrary UI-provided shell text as root.
8. **No secrets in Git.** Never commit GitHub tokens, SSH keys, Vercel tokens, signing private keys, passwords, user data, API keys, `.env` files, or VM disk images containing personal data. Use the agent's authorized credential store or CI secrets.
9. **No silent telemetry.** No analytics, crash upload, remote control, or telemetry by default. Any optional diagnostics must be opt-in, explain what is sent, and support local-only reports.
10. **No forced use of a cloud account.** The OS must be usable offline after installation, except for features that inherently need a network connection.
11. **Accessibility is a feature, not a polish item.** Keyboard navigation, screen-reader labels, sufficient contrast, scalable text, reduced motion, and predictable focus order are required.
12. **Do not bypass failing gates.** Never mark tests as skipped merely to obtain a green CI result. Document any genuinely environment-dependent test and make the skip explicit, narrow, and justified.
13. **Never force-push or rewrite the user's history.** Inspect repository state first. Preserve unrelated changes. Never delete existing branches, tags, workflows, releases, or artifacts without explicit authorization.
14. **Keep a truthful limitations list.** If a feature is incomplete, experimental, untested on physical hardware, or dependent on external services, say so in the UI and docs.

## 0.4 Work strategy

Use small, reversible, independently verifiable stages. Before changing files:

- Inspect the current working tree, branches, remotes, project structure, existing instructions, CI, release tags, and open issues.
- Read all existing `AGENTS.md`, `README.md`, `CONTRIBUTING.md`, security policy, and project-specific instructions.
- Check available storage, RAM, CPU architecture, virtualization support, network, package manager, and the available build tools.
- Detect whether the repository already contains valuable work. Never overwrite it with a generated scaffold.
- Create `docs/BUILD_LOG.md` and maintain it after each phase.

Use this status vocabulary in the build log and release documentation:

- `PLANNED` — not implemented.
- `IMPLEMENTED` — code exists, but may not yet have passed all tests.
- `TESTED` — relevant automated tests passed.
- `VM-VERIFIED` — tested in a real booted VM with recorded logs/artifacts.
- `HARDWARE-VERIFIED` — physically tested on explicitly listed hardware.
- `EXPERIMENTAL` — intentionally not part of the stable guarantee.
- `BLOCKED` — external dependency or environmental blocker, with evidence.

Never upgrade a status without evidence.

---

# 1. PRODUCT VISION AND EXPERIENCE

## 1.1 Product definition

**HSCL1 is a unified Linux workstation with three intentionally separated operating modes.** It is designed to feel approachable on first boot while remaining highly capable for people who want keyboard-first workflows, developer tooling, privacy controls, and security research.

Suggested product line:

> **HSCL1 — One system. Three modes. Your machine, your rules.**

Brand credit on the login screen, About panel, README, website footer, and release artwork:

> **Made with love by hcsmedia**

The product name must always be written `HSCL1` (capital letters, digit one). Do not rename it HSCL, HSC-Linux, or HCSL1 without a repository-wide migration and corresponding user approval.

## 1.2 Three modes

### A. Workstation — everyday system

This is the default installed desktop. It should support ordinary work without requiring terminal knowledge:

- Browser, email, calendar, office documents, PDF viewer, media playback, file management, screenshots, archive extraction, and Bluetooth/Wi-Fi settings.
- Software installation through a clear GUI (KDE Discover or the selected supported equivalent), apt packages, and Flatpak where appropriate.
- Update notifications, restart scheduling, optional automatic security updates, and an understandable recovery path.
- Developer tools and creative tools available through optional feature bundles, not every package preinstalled.
- Local user accounts; no mandatory cloud sign-in.
- Full-disk encryption offered by the installer, with an intelligible recovery-key flow.
- Predictable sleep, display, audio, printer, keyboard, mouse, and external-drive behavior.
- A cohesive file chooser, launcher, context menu, and system settings experience.

### B. Security Lab — authorized testing only

A separate, opt-in workspace for learning, CTFs, defensive engineering, application security, and authorized penetration tests:

- Kali-compatible packages delivered from official Kali container images or a separately managed VM, never from the host APT sources.
- Rootless Podman is the preferred container runtime. If a dependency requires Docker, document it and keep its daemon disabled unless needed.
- Curated categories: network discovery, packet inspection, web application testing, static/dynamic analysis, reverse engineering, forensics, cryptography, wireless analysis, and reporting.
- Install only the user-selected tool groups. Never install `kali-linux-everything` by default.
- Keep project workspaces in explicit folders such as `~/SecurityLabs/<project>`.
- Containers receive no host home directory, SSH agent, browser profile, password store, or device access by default.
- Provide explicit per-container permissions for selected folders, networking, USB devices, and hardware access.
- Offer isolated, host-only, or intentionally bridged VM networking with prominent explanations. Host-only is the safe default for lab exercises.
- Label the tools as third-party Kali tools. Display upstream license and source where feasible.
- Show an authorization reminder before enabling network attack capabilities. The reminder is educational, not a substitute for law or authorization.

The host must remain a normal Ubuntu-derived workstation if the Security Lab has never been enabled.

### C. Privacy — disposable, privacy-oriented work

This mode borrows design principles from Tails but is explicitly **not a Tails replacement**:

- Provide a separate privacy workflow with Tor Browser and carefully documented browser isolation.
- Provide a bootable ephemeral Live session with a read-only compressed root and RAM-backed writable overlay, if the image architecture supports it and it passes shutdown/persistence tests.
- Disable automatic mounting of internal host disks in the privacy session. Do not expose host home folders to a privacy VM or container.
- Disable swap, hibernation, persistent journals, crash dumps, and automatic recent-file history in the privacy live target where the boot architecture allows. Verify actual behavior; do not merely set configuration values and assume they worked.
- Default to no persistence. If optional persistence is later introduced, use a separately encrypted volume, make the exact persistent directories visible, and require an explicit user opt-in.
- Prefer a network policy that prevents non-Tor application traffic from leaving the privacy environment. Test DNS, IPv4, IPv6, WebRTC, captive portal, and Tor-unavailable behavior. If the kill switch cannot be demonstrated, do not call the mode leak-proof.
- If Tor is unavailable, fail closed for applications that are configured to use Tor. Show a clear message rather than silently falling back to direct internet.
- Provide an optional launcher for the **official, separately downloaded Tails ISO**. Verify its published signature/checksum before launching it in QEMU/KVM or writing it to a USB device. Do not redistribute a modified Tails image or imply that HSCL1 is endorsed by the Tails project.
- Explain that Tor does not prevent identity correlation when users log into personal accounts, disclose identifying information, download unsafe files, or use a compromised computer/firmware.

For sensitive situations where a user's safety depends on strong anonymity, direct them to the official Tails documentation and recommend the genuine Tails release rather than promising equivalent protection.

## 1.3 What “unified” means

The three modes must share:

- HSCL1 logo, typography, color tokens, wallpaper family, icon language, rounded window styling, and notification conventions.
- The same language settings and onboarding style.
- A consistent launcher, search field, dock, hotkey reference, and settings vocabulary when the respective mode can safely expose them.
- A single Control Center design language.

They must **not** share:

- Host privileges.
- Host home-folder mounts by default.
- Browser sessions, cookies, credential agents, SSH sockets, or password stores.
- Package repositories or untrusted toolchains.
- Persistent state in the Privacy Live mode unless users explicitly configure encrypted persistence.

Visual consistency must never weaken isolation.

---

# 2. RESEARCH FINDINGS AND ARCHITECTURE DECISIONS

Research date for this specification: **2026-11-05**. Re-check upstream release pages, package availability, hashes, and support lifecycles before every release. Upstream versions may change.

## 2.1 Omarchy — what to learn from it

Omarchy is an opinionated Arch Linux distribution built around Hyprland and Quickshell. Its value is not just a wallpaper or theme pack. Its manual documents a curated developer workstation, keyboard-first navigation, a custom launcher and menu, tiling workflows, multiple coherent themes, app installation/removal menus, hotkeys, update tooling, and a CLI. It exposes system customization and status operations through commands, which is particularly useful for agent-assisted configuration.

HSCL1 must preserve the product-level lessons:

- Ship a complete, coherent first-boot experience.
- Provide a useful launcher and central control panel.
- Treat keyboard shortcuts as first-class navigation.
- Make tiling and workspaces discoverable rather than hidden in configuration files.
- Use one source of truth for theme colors and propagate tokens to the desktop, terminal, launcher, lock screen, and apps.
- Provide a documented CLI for the same operations available in the UI.
- Make updates and configuration repair understandable.
- Keep the default application set curated rather than installing every package available.

Do not copy Omarchy's code, artwork, configuration, branding, or assets without checking their licenses and attribution requirements. The inspiration is the workflow and product philosophy, not a clone.

References:

- Omarchy manual: https://omarchy.org/manual/
- Omarchy legacy/manual details: https://learn.omacom.io/2/the-omarchy-manual
- Omarchy update channels: https://omarchy.org/manual/updates/

## 2.2 Ubuntu 26.04 LTS — foundation choice

Ubuntu 26.04 LTS (Resolute Raccoon) was released on 2026-04-23. Ubuntu's 26.04 LTS release notes list five years of standard security maintenance to April/May 2031 depending on the release-notes lifecycle table, with additional coverage through Ubuntu Pro. Ubuntu 26.04 Desktop uses GNOME 50 in the standard Ubuntu desktop edition. Ubuntu 26.10 was released in October 2026, but it is an interim release with a much shorter support window; it is not the preferred foundation for HSCL1 stable v1.

Kubuntu 26.04 LTS provides KDE Plasma 6.6, Qt 6.10.2, KDE Frameworks 6.24, and an LTS-aligned KDE maintenance initiative. The Kubuntu flavor's published support window is shorter than Ubuntu Desktop's main LTS window. Treat the KDE stack's security maintenance through the Kubuntu 26.04 lifecycle as a specific dependency and document who owns updates after that window.

**Decision:** Use the Ubuntu 26.04 LTS `resolute` archive and Kubuntu 26.04 Plasma 6.6 LTS package set as the v1 base, after the agent verifies the exact point release and package availability. Do not build on Ubuntu 26.10 merely because it is newer. Keep the OS pinned to `resolute` and update only through the approved Ubuntu pockets and the HCS repository, if introduced.

The build must record:

- Base release and point-release build ID.
- Package manifest and package versions.
- Kernel package and version.
- Plasma / Frameworks versions.
- APT source list and signing-key fingerprints.
- ISO build timestamp and toolchain versions.

References:

- Ubuntu 26.04 release notes: https://documentation.ubuntu.com/release-notes/26.04/
- Ubuntu 26.04 LTS lifecycle: https://ubuntu.com/about
- Ubuntu 26.04 release overview: https://documentation.ubuntu.com/release-notes/26.04/summary-for-lts-users/
- Kubuntu 26.04 release: https://www.kubuntu.org/news/kubuntu-26-04-release-notes/
- Kubuntu Plasma 6.6 LTS maintenance: https://www.kubuntu.org/news/plasma-6.6-lts/

## 2.3 KDE Plasma — desktop decision

KDE Plasma is the best practical foundation for the desired hybrid interaction model because it supports a highly configurable panel/dock/task-manager layout, window rules, keyboard shortcuts, virtual desktops, activities, KWin tiling/snap workflows, global menus, and a mature settings application. It lets HSCL1 build a Mac-like menu/status bar and a Windows-like taskbar/start launcher without maintaining a fork of a full desktop shell.

Use the stable Plasma 6.6 LTS package set from the 26.04 base. Prefer upstream components and supported configuration APIs. Avoid a large collection of fragile third-party shell extensions. Keep customization in version-controlled Plasma layout defaults, KDE color schemes, icon theme, wallpaper, fonts, KWin rules, launcher config, and small HCS-owned components.

## 2.4 Kali — keep tools outside the host

Kali's own documentation says Kali is aimed at professional penetration testers and security specialists and is not the recommended general-purpose Linux desktop for people seeking a generic daily-driver environment. Its official container documentation provides Kali rolling container images and describes Podman usage. Its metapackage documentation groups tool sets by purpose.

**Decision:** Do not import Kali repositories into the HSCL1 host. Use official Kali OCI container images from trusted upstream distribution points, verify image digest/signature support where available, pin a tested digest for the release, and expose curated tools through `hscl lab`. Rootless Podman is preferred. When a specific tool requires kernel capabilities, USB/Wi-Fi injection, or a full network stack, provide a separate disposable VM workflow and document the security boundary.

References:

- Should I use Kali?: https://www.kali.org/docs/introduction/should-i-use-kali-linux/
- Kali metapackages: https://www.kali.org/docs/general-use/metapackages/
- Official Kali container images: https://www.kali.org/docs/containers/official-kalilinux-docker-images/
- Kali Podman guide: https://www.kali.org/docs/containers/using-kali-linux-docker-images/ (verify exact current Podman guide link from Kali's documentation navigation)

## 2.5 Tails — what is and is not transferable

Tails is a live operating system designed to start from removable media, run independently from another installed OS, avoid writing to internal storage in its normal model, and forget session data on shutdown. It has optional encrypted Persistent Storage. Its network and application configuration are intentionally designed to reduce mistakes, including Tor use and blocking non-Tor traffic. Tails itself warns that no OS can protect against everything, including malicious hardware and compromised environments.

A standard installed desktop with Tor Browser does not reproduce that design. A VM running inside a compromised host also inherits risks from the host and hypervisor. The HSCL1 project must not present a Tor browser icon as a Tails clone.

**Decision:** Build an HSCL1 privacy-oriented workflow and, only if testable, a separate disposable live session. Keep official Tails as a separately verified option. State limitations in the onboarding screen and docs.

References:

- How Tails works: https://tails.net/about/index.en.html
- Tails anonymous internet / Tor docs: https://tails.net/doc/anonymous_internet/index.en.html
- Tails Persistent Storage: https://tails.net/doc/persistent_storage/index.en.html
- Tails warnings: https://tails.net/doc/about/warnings/index.en.html
- Tails virtual machine guidance: https://tails.net/doc/advanced_topics/virtualization/index.en.html (verify current URL before linking in the website)

## 2.6 Installer and image building

Calamares is a distribution-independent installer framework with configurable modules and branding. An updated Calamares package is available in the Ubuntu 26.04 `resolute` archive. The agent must use the current supported package and test its partitioning/encryption modules against the exact live image.

Ubuntu's own ISO process uses `livecd-rootfs`, `ubuntu-cdimage`, and `debian-cd`; Ubuntu documentation describes the image pipeline and warns that modifying the official build stack can be tedious. Ubuntu also documents `livefs-editor` as a way to modify existing installer images. Cubic is a community-maintained GUI tool for Ubuntu/Debian ISO customization; it may be useful for exploration but is not the default reproducible CI foundation unless its headless/build automation capabilities are proven.

**Decision:** First prototype the official Ubuntu/Kubuntu live-image customization path. Prefer a reproducible scripted pipeline based on Ubuntu's documented image tooling or a maintained livefs editing mechanism. A remastered official ISO is acceptable only if the build script preserves boot entries, EFI files, signed shim/GRUB/kernel paths, manifests, and hybrid image structure. Calamares can be included as the GUI installer if the live image and installed target can be correctly configured.

The agent must create a short proof-of-concept before committing to the final image pipeline. The PoC must:

1. Start from an official Ubuntu/Kubuntu 26.04.1 amd64 ISO or a reproducible base rootfs.
2. Add one HCS-owned package and one theme change.
3. Rebuild the ISO deterministically enough to compare manifests and hashes.
4. Boot in QEMU using UEFI and, where supported, legacy BIOS.
5. Reach the live desktop.
6. Launch the installer.
7. Preserve the original Secure Boot boot path if the source supports it.

Do not claim official Canonical support for a custom image pipeline. Keep the source/patches and limitations transparent.

References:

- Ubuntu image build process: https://ubuntu.com/project/docs/how-ubuntu-is-made/processes/image-builds/
- Ubuntu custom installer images: https://ubuntu.com/hardware/docs/image-cookbook/howto/images/customize_installer_image/
- Ubuntu livefs editor: linked from the official customization documentation; resolve current package/repository and pin it in the build manifest.
- Calamares project: https://calamares.codeberg.page/
- Calamares repository transition notice: https://github.com/calamares/calamares
- Debian Live manual (useful for concepts and QEMU test workflows): https://live-team.pages.debian.net/live-manual/html/live-manual/index.en.html
- Archiso reference only if evaluating alternatives: https://github.com/archlinux/archiso

## 2.7 Security foundation

Keep the base on Ubuntu's maintained kernel, signed boot components, AppArmor profiles, UFW/nftables, systemd hardening, LUKS2, and secure update flow. Ubuntu documents Secure Boot, full-disk encryption, TPM-backed FDE, and AppArmor. TPM-backed FDE in Ubuntu 26.04 has known beta limitations; do not make it the only disk encryption option.

**Decision:** v1 must support passphrase-based LUKS2 encryption. TPM-backed unlocking may be optional/experimental and only exposed if the exact Ubuntu implementation is supported by the chosen installer and tested on real compatible hardware. Never hide or remove the recovery-key path.

References:

- Ubuntu platform security: https://ubuntu.com/security/platform-security
- Ubuntu full disk encryption: https://documentation.ubuntu.com/security/security-features/storage/encryption-full/
- Ubuntu TPM-backed encryption limitations: https://ubuntu.com/desktop/docs/en/latest/how-to/encrypt-your-disk-with-tpm/

---

# 3. TECHNICAL ARCHITECTURE

## 3.1 Architecture overview

Build a layered system. Keep the base distro boring and maintainable; let HSCL1-owned components provide the experience.

```text
UEFI / BIOS
  └─ Signed boot chain where supported (shim → GRUB → signed kernel)
      ├─ Live Workstation / Installer
      │   ├─ Read-only compressed root (squashfs)
      │   ├─ Writable overlay (RAM or explicitly configured persistence)
      │   └─ HSCL1 Plasma desktop + Calamares
      ├─ Installed Workstation
      │   ├─ Ubuntu 26.04 LTS / Kubuntu 26.04 package foundation
      │   ├─ Plasma 6.6 LTS + KWin + Dolphin + Discover
      │   ├─ HCS desktop defaults + control center + CLI
      │   ├─ AppArmor + UFW/nftables + LUKS2 + optional Btrfs snapshots
      │   ├─ Podman rootless + optional developer/AI bundles
      │   └─ Local model tools (opt-in)
      └─ Optional Privacy Live boot target
          ├─ Ephemeral writable layer
          ├─ No internal disk auto-mount
          ├─ Tor-focused network policy
          └─ Explicit limitations / no Tails-equivalence claim

Workstation host
  ├─ Security Lab: isolated Kali OCI container(s) / disposable VM(s)
  ├─ Privacy utilities: Tor Browser, metadata tools, encrypted volumes
  └─ HCS Control Center ↔ hscl CLI ↔ narrow privileged helper / Polkit
```

## 3.2 Base operating system

- Distribution family: Ubuntu LTS.
- Release codename: `resolute` (Ubuntu 26.04 LTS).
- CPU architecture: `amd64` only for the v1 ISO unless the image pipeline proves additional architectures.
- Kernel: Ubuntu/Kubuntu supported kernel for the selected point release; do not ship an arbitrary custom kernel by default.
- Init/system manager: systemd.
- Display protocol: Wayland-first, XWayland compatibility where available.
- Desktop: KDE Plasma 6.6 LTS.
- Window manager/compositor: KWin.
- File manager: Dolphin.
- Software GUI: KDE Discover backed by the supported apt/Flatpak integrations.
- Package manager: APT for OS packages; Flatpak for selected desktop applications; Podman for isolated container toolchains.
- Firewall: UFW interface with nftables backend, or directly managed nftables where required. Avoid two competing policy managers.
- Security confinement: AppArmor profiles, systemd service hardening, Polkit, seccomp/capability reduction where suitable.
- Disk encryption: LUKS2.
- Filesystem: ext4 as reliable default; Btrfs as optional advanced layout with snapshot support. Do not promise bootable snapshots until fully tested.

Do not add an Arch/AUR layer to the host. Do not use AUR helpers. Do not install Kali packages on the host. Do not use an unsupported third-party kernel as a default.

## 3.3 Repository architecture

Use a clear monorepo unless an existing repository already has a different coherent structure. Suggested layout:

```text
HSCL1/
├── AGENTS.md
├── README.md
├── LICENSE
├── NOTICE
├── CONTRIBUTING.md
├── CODE_OF_CONDUCT.md
├── SECURITY.md
├── CHANGELOG.md
├── VERSION
├── .editorconfig
├── .gitignore
├── .gitattributes
├── .github/
│   ├── ISSUE_TEMPLATE/
│   ├── PULL_REQUEST_TEMPLATE.md
│   ├── workflows/
│   │   ├── lint.yml
│   │   ├── test.yml
│   │   ├── build-iso.yml
│   │   ├── security.yml
│   │   ├── website.yml
│   │   └── release.yml
│   └── dependabot.yml
├── distro/
│   ├── base/
│   │   ├── packages/
│   │   ├── apt/
│   │   ├── kernel/
│   │   └── defaults/
│   ├── live/
│   │   ├── boot/
│   │   ├── casper-or-liveboot/
│   │   ├── overlays/
│   │   └── hooks/
│   ├── installer/
│   │   ├── calamares/
│   │   ├── branding/
│   │   └── modules/
│   ├── security/
│   │   ├── apparmor/
│   │   ├── polkit/
│   │   ├── nftables/
│   │   ├── sysctl/
│   │   └── systemd/
│   └── privacy/
│       ├── live-session/
│       ├── network-policy/
│       └── defaults/
├── apps/
│   ├── control-center/
│   ├── launcher-integration/
│   ├── welcome/
│   └── updater-ui/
├── cli/
│   └── hscl/
├── services/
│   ├── hscl-privileged-helper/
│   ├── hscl-update-check/
│   └── hscl-device-detect/
├── themes/
│   ├── hcs-default/
│   ├── hcs-dark/
│   ├── hcs-light/
│   └── tokens/
├── packages/
│   ├── debian/
│   └── manifests/
├── containers/
│   ├── kali/
│   ├── dev/
│   └── ai/
├── ai/
│   ├── backends/
│   ├── model-catalog/
│   └── scripts/
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── installer/
│   ├── vm/
│   ├── security/
│   └── visual/
├── scripts/
│   ├── bootstrap-build-host.sh
│   ├── build-rootfs.sh
│   ├── build-iso.sh
│   ├── verify-iso.sh
│   ├── test-iso-qemu.sh
│   ├── test-install-qemu.sh
│   ├── generate-sbom.sh
│   └── release.sh
├── website/
│   ├── package.json
│   ├── src/
│   │   ├── pages/
│   │   ├── components/
│   │   ├── layouts/
│   │   ├── content/
│   │   ├── i18n/
│   │   └── styles/
│   ├── public/
│   └── vercel.json
└── docs/
    ├── ARCHITECTURE.md
    ├── BUILD_LOG.md
    ├── BUILDING.md
    ├── INSTALLATION.md
    ├── VM_GUIDE.md
    ├── SECURITY.md
    ├── THREAT_MODEL.md
    ├── PRIVACY_MODE.md
    ├── SECURITY_LAB.md
    ├── CLI.md
    ├── LOCAL_AI.md
    ├── HARDWARE_COMPATIBILITY.md
    ├── TROUBLESHOOTING.md
    ├── TESTING.md
    ├── RELEASE_PROCESS.md
    ├── LICENSES.md
    ├── KNOWN_LIMITATIONS.md
    └── translations/
        ├── de/
        └── fr/
```

Adapt the exact tree to the repository. Do not create empty directories simply to match this diagram. Each component must have a real purpose and tests.

## 3.4 Component boundaries

### `hscl` CLI

The CLI is the automation and integration contract. The UI must call typed application interfaces or stable CLI subcommands; it must not duplicate system logic in unrelated UI scripts.

Prefer Rust for a small, robust CLI and privileged helper. Use `clap` for parsing, `serde` for structured config, `tracing` for logs, `anyhow`/`thiserror` for errors, and `serde_json` for machine-readable output. Pin toolchain versions in `rust-toolchain.toml` and dependencies in `Cargo.lock`.

Python and Bash are allowed for build orchestration, test harnesses, and packaging where they are simpler and auditable. Shell scripts must be strict, quoted, tested, and ShellCheck-clean.

### Control Center

Preferred UI stack: Qt 6 / Qt Quick (QML) with a small typed backend. Use KDE integration patterns rather than a heavy custom web shell. It must be fast, native-feeling, responsive, keyboard-accessible, and usable on common 1366×768 and 1920×1080 displays.

The Control Center is not a root process. Any action requiring elevated privileges must invoke a constrained Polkit action with validated arguments.

### Privileged helper

The helper must:

- Expose a finite, typed set of operations (e.g. apply firewall profile, install an approved bundle, set a system setting, create a recovery snapshot).
- Validate every argument and state transition.
- Reject paths outside approved directories.
- Reject arbitrary command strings.
- Log auditable operation metadata without collecting personal file contents.
- Return explicit error codes and actionable diagnostics.
- Have unit and integration tests for authorization, invalid input, path traversal, injection, and race conditions.

### Update system

- Keep APT as the source of system package truth.
- Use only Ubuntu `resolute`, `resolute-updates`, and `resolute-security` pockets plus an HCS signed repository if absolutely required.
- If an HCS repository exists, it needs its own signing key, published fingerprint, package metadata, documented key rotation, and repository health monitoring.
- Never use an unsigned package repository.
- Never run `curl | sudo bash` in update paths.
- Stage downloads, validate repository signatures, install through apt/dpkg, and record results.
- Before a major update, create a supported recovery point if Btrfs snapshots are implemented. If snapshots are unavailable, disclose that and rely on normal Ubuntu recovery procedures.
- Do not claim atomic updates if the actual apt workflow is not atomic.

---

# 4. DESKTOP DESIGN SYSTEM — HCS HYBRID DESKTOP

## 4.1 Design direction

Create an original desktop called **HCS Hybrid Desktop**. Its visual language should feel premium and calm: a macOS-inspired top bar and dock combined with Windows 10's familiar taskbar, start launcher, window snapping, and system settings discoverability. It must still feel unmistakably Linux and must not be a pixel-perfect clone of either commercial platform.

The design should work in dark and light modes. Default to dark mode with a restrained accent color and subtle transparency. Avoid excessive glass effects that harm contrast or GPU performance.

### Core principles

- One obvious place to find applications.
- One obvious place to change system settings.
- Mouse-first users can operate the whole desktop.
- Keyboard-first users can complete the same tasks faster.
- Window tiling is available but never forced.
- Visual effects are optional and respect reduced-motion preferences.
- Panels adapt to small displays and touch input.
- System notifications are useful and never obscure critical content.
- Every screen is localized in English, German, and French.

## 4.2 Layout

### Top bar

A slim, full-width top panel inspired by macOS:

- **Left:** HSCL1 logo/menu, application menu for the active app where supported, and a compact current app label.
- **Middle:** optional workspace indicator, active window context, and date/time depending on screen width.
- **Right:** network, audio, Bluetooth, battery, VPN/Tor state, updates, notifications, accessibility, and quick settings.
- Panel height target: approximately 30–36 logical pixels at 100% scaling.
- Respect fractional scaling and high-DPI displays.
- System status icons must expose accessible names and status descriptions.

### Bottom dock / taskbar

A centered, floating dock inspired by macOS with the usability of a Windows taskbar:

- Pinned applications.
- Running applications, visually distinguished from pinned apps.
- Grouped windows for the same app.
- Optional workspace-aware indicators.
- Trash and app grid entry.
- Context menu for pin/unpin, open new window, and close.
- Configurable location: bottom (default), left, or right.
- Auto-hide is optional, never default on first boot.
- Scale and spacing should be adjustable.
- On small screens, collapse into a conventional taskbar layout.

### Start / Applications menu

- Open with `Meta` or `Super + Space`.
- Large searchable input receives keyboard focus immediately.
- Search applications, settings pages, documents only when user enables indexing, and `hscl` actions.
- Categories: Favorites, All Apps, Development, Internet, Office, Graphics, Multimedia, System, Security Lab (only when enabled), and Privacy.
- Include recent apps but no recent-document history in Privacy mode.
- Search results must be real, installed desktop entries or real command actions.
- Never show a button that looks executable if its action is not implemented.

### Window management

- Familiar title bar and right-side minimize/maximize/close controls.
- Rounded corners where supported and where they do not break application rendering.
- Alt+Tab task switcher with clear previews.
- Overview / Exposé-style mode to view all windows and workspaces.
- Snap left/right, quarters, maximize, restore, and move between workspaces.
- KWin tiling and keyboard shortcuts should be documented and discoverable.
- Provide a floating vs tiled preference per application.
- Do not force tiling on users who prefer conventional windows.

### File manager defaults

Dolphin opens with a polished sidebar:

- Home
- Desktop
- Documents
- Downloads
- Pictures
- Videos
- Music
- Projects
- External Drives
- Network
- Trash

Use human-readable labels and clear mounted/unmounted states. External removable media must never be silently formatted or automatically made persistent in Privacy mode.

### Control Center

The HCS Control Center should have a left navigation rail and a responsive content view. Sections:

1. Overview — device health, OS version, update state, storage, privacy/security posture.
2. Appearance — dark/light, accent, wallpaper, icons, fonts, dock, panels, animations.
3. Display — resolution, scaling, monitor layout, night light.
4. Network — Wi-Fi, Ethernet, VPN, DNS, firewall status, Tor status.
5. Privacy — session isolation, history controls, app permissions, external disk behavior.
6. Security — firewall profiles, AppArmor status, encryption status, recovery key reminders, audit report.
7. Users — local users, session controls, password settings.
8. Applications — installed apps, Flatpak, approved bundles, default apps.
9. Developer — terminals, Git, compilers, containers, virtualization.
10. Security Lab — enable/disable lab, install curated tool groups, show container/VM isolation state.
11. Local AI — detect hardware, install backend, model storage, model catalog, local server status.
12. Updates & Recovery — updates, repair checks, snapshots if implemented, logs.
13. Language & Region — English, Deutsch, Français, keyboard, formats, time zone.
14. About — HSCL1 release, HCS credit, licenses, sources, support links.

Every screen must display real system state, not static demo values.

## 4.3 Visual tokens

Create one token file as the canonical source for UI and website values. Define at least:

- `surface-0`, `surface-1`, `surface-2`, `surface-glass`.
- `text-primary`, `text-secondary`, `text-muted`, `text-inverse`.
- `accent`, `accent-hover`, `accent-pressed`, `accent-soft`.
- `success`, `warning`, `danger`, `info`.
- `border-subtle`, `border-strong`, `focus-ring`.
- `radius-sm`, `radius-md`, `radius-lg`, `radius-xl`, `radius-pill`.
- `space-1` through `space-8`.
- `shadow-low`, `shadow-floating`, `shadow-dialog`.
- Typography scale and line heights.
- Motion durations and easing curves.

Suggested palette (adjust after visual testing, but centralize the values):

- Background: deep graphite / midnight charcoal.
- Surfaces: slightly elevated cool charcoal.
- Accent: electric blue-violet or a restrained HCS cyan.
- Highlight: soft periwinkle.
- Success: green, warning: amber, danger: clear red.
- Light theme: warm-neutral background with cool gray surfaces.

Contrast must meet WCAG AA for normal text wherever applicable. Never use opacity-only distinctions for essential states.

## 4.4 Theme engine

Implement a theme catalog with:

- `HCS Midnight` — default dark.
- `HCS Light` — default light.
- `HCS Nord` — optional cool theme.
- `HCS Aurora` — optional vibrant theme.

Only ship themes that are actually integrated and tested. A theme change should consistently apply colors to Plasma, Qt apps, terminal, launcher, lock screen, notifications, and wallpaper. Where an application cannot be themed, document the limitation.

The theme system must:

- Keep user changes separate from system defaults.
- Back up files before applying changes.
- Validate theme metadata and assets.
- Reject paths and symlinks escaping the theme directory.
- Offer a one-command restore to the default theme.
- Provide a GUI preview.

## 4.5 Keyboard shortcuts

Use `Meta` / Super as the primary desktop modifier. Avoid conflicts with common application shortcuts. Provide a visible shortcut reference (`Meta + K`). Implement and document at least:

| Shortcut | Action |
|---|---|
| `Meta` | Open Start / Applications menu |
| `Meta + Space` | Focus launcher search |
| `Meta + Enter` | Open terminal |
| `Meta + E` | Open file manager |
| `Meta + D` | Show desktop |
| `Meta + Tab` | Switch applications |
| `Meta + K` | Open shortcut reference |
| `Meta + ,` | Open Control Center |
| `Meta + L` | Lock screen |
| `Meta + Shift + S` | Screenshot / region capture |
| `Meta + Left/Right` | Snap window left/right |
| `Meta + Up` | Maximize |
| `Meta + Down` | Restore/minimize according to KWin behavior |
| `Meta + 1..9` | Switch workspace or launch favorite, with documented deterministic behavior |
| `Ctrl + Alt + T` | Open terminal (fallback familiar Linux shortcut) |

Check and resolve conflicts with KDE defaults. Do not publish shortcuts that are not bound.

---

# 5. PACKAGE AND APPLICATION STRATEGY

## 5.1 Default application philosophy

Do not build a bloated ISO. Include the essential software needed to use the system after installation and leave specialized toolchains optional.

### Core desktop bundle

- KDE Plasma / KWin / System Settings.
- Dolphin.
- KDE Discover.
- Konsole or the selected maintained terminal.
- A maintained browser from a supported source.
- LibreOffice or a smaller office set if image-size constraints require it.
- PDF viewer.
- Screenshot utility.
- Archive manager.
- Clipboard support.
- Audio/video playback support.
- Password manager only if licensing and update source are clear.
- Flatpak support where it is stable.
- NetworkManager and common Wi-Fi firmware where licensing permits.
- Bluetooth support.
- Printer/scanner support as optional components.

### Developer bundle (opt-in)

- Git, SSH client, build-essential, pkg-config.
- Python 3 and venv/pipx.
- Rust toolchain via rustup or distribution packages; document the source and update channel.
- Node.js through a maintained version manager or supported repository, not a random script.
- VS Code/VSCodium only after license/source review; do not preinstall proprietary binaries without disclosure.
- Podman, Buildah, Skopeo, Distrobox if supported and needed.
- QEMU/KVM, libvirt, virt-manager (optional).
- btop or an equivalent resource monitor.

### Creator bundle (opt-in)

- GIMP, Krita, Inkscape, Blender only if package size and hardware requirements are reasonable.
- OBS Studio as optional.
- Local media utilities with codecs from lawful sources.

### Privacy bundle

- Tor Browser from an authentic supported distribution channel.
- OnionShare only if its upstream packaging, licensing, and maintenance are verified.
- Metadata removal utility.
- `cryptsetup` tooling and a GUI encrypted-volume utility if available.
- `age` and/or GnuPG for file encryption.
- Firewall status UI.

### Security Lab bundle

Install only inside the isolated Kali environment or the approved VM:

- Basic: nmap, netcat, tcpdump, Wireshark/tshark, whois, dns utilities.
- Web: Burp Suite Community where permitted, OWASP ZAP, sqlmap, ffuf, gobuster, nikto where available and maintained.
- Analysis: binwalk, file, strings, Ghidra or another supported reverse-engineering tool if resource constraints permit.
- Forensics: Autopsy/Sleuth Kit and memory-analysis tools where available.
- Wireless: aircrack-ng and supporting tools, only when hardware passthrough and legal scope are understood.
- Reporting: Markdown templates and evidence folders.

The bundle list is a proposed starting set, not a promise every package ships in v1. The agent must verify upstream package availability, licensing, compatibility, image size, and isolation requirements before inclusion.

## 5.2 Application installation safety

- No application should request root merely to open.
- Prefer Flatpak for desktop apps that benefit from sandboxing, with explicit permissions.
- Use distro APT packages for core system tools.
- Do not add random PPAs for convenience.
- Display the source and trust type for installed applications.
- Ensure uninstall removes the application while preserving user data unless the user explicitly chooses to delete it.
- Do not run arbitrary `.sh` installers downloaded from websites.

---

# 6. SECURITY, PRIVACY, AND THREAT MODEL

## 6.1 Threat-model document required

Create `docs/THREAT_MODEL.md` and keep it aligned with actual code. It must state:

- Assets: user data, passwords, SSH keys, browser profiles, local model files, project source, disk encryption keys, network identity, device integrity.
- Adversaries: opportunistic malware, malicious downloads, malicious containers, malicious local users, lost/stolen device, untrusted network, malicious USB device, compromised host/hypervisor, targeted attacker.
- Trust boundaries: firmware, boot chain, kernel, host OS, user session, Polkit helper, containers, VMs, live overlay, Tor network, external removable storage, cloud release infrastructure.
- Mitigations and residual risks for every mode.
- Features not provided by the product.
- Testing evidence and gaps.

## 6.2 Baseline hardening

The installed Workstation mode must use a sensible security baseline without making normal use unnecessarily painful:

- AppArmor enabled and loaded.
- Firewall enabled by default with a deny-incoming policy and normal outbound access. Confirm no essential discovery or network services are unintentionally blocked.
- No unnecessary listening services.
- SSH server disabled unless explicitly enabled.
- Root login disabled for remote SSH if SSH is enabled.
- Unprivileged user accounts by default; no automatic root desktop login.
- `sudo` access scoped to the local admin user.
- Polkit rules least-privilege and auditable.
- Automatic security updates offered and clearly configured.
- Secure Boot-compatible boot flow where possible.
- LUKS2 encryption option in installer.
- Strong default umask and safe temporary-file handling.
- Disable core dumps for sensitive workflows where justified and testable.
- Apply service hardening (`NoNewPrivileges`, `PrivateTmp`, `ProtectSystem`, `ProtectHome`, `RestrictAddressFamilies`, etc.) only where compatible and tested.
- Keep time synchronization enabled; correct time is important for TLS and logs.
- Do not disable kernel security mitigations for performance.
- Do not use blanket `chmod 777` fixes.

## 6.3 Disk encryption

v1 must offer passphrase-based LUKS2 full-system encryption. The installer must:

- Explain what is encrypted and what is not (e.g. firmware, some boot components, external backups, data written to unencrypted removable media).
- Generate a recovery key or recovery method that the user can store separately.
- Ask the user to confirm they have safely stored it before finishing.
- Never upload the recovery key.
- Never log the passphrase.
- Never hard-code secrets or use a sample passphrase.
- Validate that the installed system boots and unlocks correctly in a VM.
- Test a wrong passphrase and missing recovery material path without corrupting the virtual disk.

Do not advertise TPM-backed encryption as stable in v1 unless the exact Ubuntu 26.04 implementation, installer integration, recovery path, and supported hardware have been verified. The Ubuntu docs identify limitations in the TPM-backed beta flow.

## 6.4 Firewall profiles

Provide simple profiles in the Control Center:

- `Standard`: deny unsolicited inbound connections; permit normal outbound connections.
- `Public Wi-Fi`: deny inbound, disable sharing services, stricter discovery, no local service listeners unless user opts in.
- `Lab / Host-only`: tailored to the VM network interface and test lab.
- `Privacy`: only expose approved Tor/bootstrapping traffic in the dedicated privacy environment. Do not apply a broken pseudo-Tor policy to the normal host.

Changing profiles requires a summary of services that may become inaccessible. The UI must avoid locking the user out of their network administration session.

## 6.5 Privacy mode acceptance boundaries

For every feature below, implement tests and report evidence:

- Persistent writes: inspect mounted filesystems and overlay backing store.
- Swap: verify no swap partition/file is active in the ephemeral session.
- Hibernation: unavailable in ephemeral mode.
- Journals: no session logs are written to persistent internal storage; prove configuration and mount behavior.
- Internal disks: no automatic mount; test attached virtual disks.
- Browser: use Tor Browser with upstream safe defaults; no custom fingerprint-breaking modifications.
- DNS: ensure configured traffic does not bypass Tor in the privacy mode; test with packet capture.
- IPv6: either safely support through the Tor design or block it in the privacy environment; document the selected choice.
- Tor unavailable: fail closed; no direct-browser fallback.
- Shutdown: discard the volatile overlay and stop services; do not claim reliable physical RAM sanitization on every machine.
- Persistent storage: disabled by default; if included, encrypt, scope, and document it.

If the agent cannot prove the above, label the session **Experimental Privacy Session** and do not present it as an anonymity solution. The stable v1 may ship a safe Tor workflow and an official Tails launcher without shipping an HSCL1 live anonymity mode.

## 6.6 Security Lab isolation

- Rootless Podman by default.
- Never run user-provided container images automatically.
- Pin official Kali base image digests for tested builds.
- Default to no host PID namespace, no privileged container, no host network, no Docker socket, no host home mount, and no device passthrough.
- Apply resource limits where practical.
- Provide one-way explicit mounts for chosen lab folders.
- Do not mount `/`, `/etc`, `/var/run`, SSH agent sockets, browser config, GPG agent sockets, or password-store directories.
- Use a disposable volume for temporary sessions.
- For GUI applications, prefer documented Wayland/XWayland forwarding with strict access controls; if safe display isolation is not available, run the application in a dedicated VM.
- Show container image, digest, update timestamp, granted capabilities, mounts, and network mode in the UI.
- Provide `hscl lab destroy` with a clear confirmation and protect user-selected evidence folders.

## 6.7 Supply-chain security

- Generate an SPDX or CycloneDX SBOM for the ISO and website build.
- Record package versions, source repository, and signatures.
- Verify Ubuntu repository signing keys.
- Verify downloaded upstream ISO signatures/checksums using official instructions.
- Pin GitHub Actions by full commit SHA for security-sensitive workflows.
- Use least-privilege CI permissions.
- Use OIDC where possible; no long-lived release secrets in source files.
- Enable GitHub secret scanning if available.
- Scan containers and built packages using maintained tools such as Trivy or Grype, after checking tool licensing and CI cost.
- Run static analysis and dependency vulnerability checks.
- Publish `SHA256SUMS` and a detached signature. Use a public verification key that is documented and rotate keys carefully.
- Do not state the OS is “certified”, “unhackable”, “military grade”, “anonymous”, or “zero-trace”.

---

# 7. INSTALLER, LIVE ISO, AND VM SUPPORT

## 7.1 Target artifact

Build one hybrid amd64 ISO that:

1. Boots into a live HSCL1 desktop.
2. Supports trying the system without installing it.
3. Launches a branded graphical installer.
4. Can be written to a USB device.
5. Can boot in QEMU/KVM and VirtualBox using documented settings.
6. Can boot on supported UEFI physical PCs.
7. Preserves Secure Boot where the source boot chain permits it.

Artifact name:

`HSCL1-v1.0.0-amd64.iso`

Release companion files:

- `HSCL1-v1.0.0-amd64.iso.sha256`
- `SHA256SUMS`
- `SHA256SUMS.sig` or an equivalent detached signature.
- `SBOM.spdx.json`.
- `package-manifest.txt`.
- `build-manifest.json`.
- `release-notes.md`.

A separate VM disk image is optional; do not let it delay the verified ISO. If produced, include a qcow2 image only after a successful installed-system boot test and a documented default credential-free first-boot setup.

## 7.2 Build pipeline decision gate

Before implementing a complete image pipeline, compare:

- Official Ubuntu/Kubuntu image customization with `livecd-rootfs` and the Ubuntu image tooling.
- An official live installer ISO modified with Ubuntu's documented `livefs-editor` route.
- A scripted remastering path based on `squashfs-tools`, `xorriso`, and a carefully preserved boot structure.
- Calamares with an extracted root filesystem as installer target.
- Debian `live-build` as a reference/fallback only after proving that the exact Ubuntu `resolute` packages, casper/live boot behavior, package indexes, Secure Boot files, and installer modules work. Do not assume Debian's manual automatically makes an Ubuntu derivative supported.

Preferred principles:

- Reproducible shell/Python scripts checked into the repository.
- No GUI-only image assembly in CI.
- Use an isolated build environment with pinned tooling.
- Preserve upstream boot assets when possible.
- Verify EFI and BIOS catalog entries after rebuild.
- Verify ISO hybrid metadata and checksums.
- Verify signed components and Secure Boot behavior.
- Generate a manifest from the actual squashfs/rootfs contents.

If a custom Calamares installer cannot be made reliable on the chosen base, investigate the official Ubuntu installer/autoinstall route and explain the tradeoffs. Do not ship a fake or nonfunctional installer screen.

## 7.3 Installer UX

The installer must have a modern HCS skin, but correctness is more important than animation.

Screens / steps:

1. Welcome — language, accessibility, live session or install.
2. Keyboard — detected layout with a test field.
3. Network — show status; internet optional for offline installation.
4. Updates and drivers — third-party driver options with licenses and network needs clearly described.
5. Installation type — erase disk, install alongside only if safe and supported, manual partitioning.
6. Encryption — LUKS2 option with passphrase requirements and recovery-key instructions.
7. Filesystem — safe default and advanced option only if fully tested.
8. User — full name, username, password, hostname; validate securely.
9. Locale/time zone — searchable region/city selector.
10. Review — exact target disk, partition changes, encryption, bootloader, data-loss warning.
11. Install — progress, detailed log, meaningful stages, cancellation behavior.
12. Finish — reboot/live session choice, recovery key reminder, docs link.

Safety constraints:

- Never preselect destructive erase without an explicit user choice.
- Show the actual disk model, size, and identifier; distinguish removable devices.
- Require a final explicit confirmation for disk erasure. A typed confirmation phrase such as `ERASE DISK` is acceptable if it is localized and accessible.
- Do not claim safe dual-boot unless tested on multiple UEFI/GPT test images, including a Windows-like EFI layout. If not proven, present manual partitioning as advanced and warn clearly.
- Do not overwrite an EFI system partition from another OS without the user being shown the operation.
- Do not install to a physical disk during CI.
- Log installer operations without logging passwords, passphrases, or recovery keys.
- Support offline installation from the ISO with the selected core packages.
- Handle failure gracefully and preserve diagnostic logs for the live session.

## 7.4 Partition layout

For a supported UEFI/GPT full-disk encrypted installation, use a tested layout similar to:

- EFI System Partition (FAT32, unencrypted, sized according to current upstream requirements).
- Optional unencrypted boot partition only if required by the selected boot/encryption architecture.
- LUKS2 encrypted system partition.
  - ext4 root as reliable default, or
  - Btrfs subvolumes for root/home/snapshots if supported end-to-end.
- Swap file/partition only in the installed mode if configured; never enable swap in the ephemeral privacy mode.

Do not make the partition layout a rigid assumption. Calamares modules, GRUB, LUKS, Secure Boot, and the bootloader must be tested together. Document any unsupported RAID, Intel RST/VMD, dual-boot, or unusual firmware scenarios.

## 7.5 VM test matrix

At minimum test:

- QEMU/KVM BIOS boot.
- QEMU/KVM UEFI boot using OVMF.
- QEMU/KVM UEFI Secure Boot if enabled by the actual ISO.
- VirtualBox UEFI boot where available.
- 2 vCPU / 4 GB RAM baseline.
- 4 vCPU / 8 GB RAM recommended profile.
- 40 GB disposable virtual disk install.
- 80 GB disposable virtual disk encrypted install.
- No network installation.
- Networked first boot and update path.
- Screen sizes 1366×768 and 1920×1080.
- HiDPI/fractional scaling smoke test.

VM testing must store logs and screenshots under CI artifacts or `artifacts/` (not in Git unless intentionally curated and small). Never attach a VM disk containing user data to a public release.

## 7.6 Hardware expectations

Initial target profile (must be confirmed by testing rather than marketing):

- 64-bit x86 processor with virtualization support recommended.
- 4 GB RAM minimum for a stripped live/test environment; 8 GB recommended for ordinary desktop use; 16 GB recommended for virtualization and local AI.
- 40 GB disk minimum for a practical install; 64 GB or more recommended.
- UEFI system firmware recommended.
- Intel/AMD integrated graphics supported through Ubuntu/Mesa drivers where available.
- NVIDIA proprietary driver optional and subject to Secure Boot module signing requirements.
- Wi-Fi, Bluetooth, audio, camera, touchpad, suspend, and power management require model-specific validation.

Do not call a device “supported” merely because it boots in QEMU. Maintain a tested hardware compatibility table.

---

# 8. HSCL1 CLI SPECIFICATION

## 8.1 Command name and design

Command: `hscl`

The CLI is the primary automation interface for desktop functions and is designed to be usable by humans, scripts, and local AI agents. It must have:

- `--help` for every command group.
- `--version`.
- Stable exit codes.
- `--json` output for machine consumers where appropriate.
- `--dry-run` for system changes where feasible.
- `--yes` only for non-destructive safe operations; never let it bypass destructive-disk confirmations.
- Clear warnings and actionable errors.
- No hidden shell execution.

## 8.2 Required command structure

Implement real commands for each supported v1 feature. A planned command that is not implemented must be omitted from help or explicitly labeled experimental.

```text
hscl
  version
  status [--json]
  about
  doctor [--full] [--json]
  report [--output PATH]
  help [COMMAND]

  system
    info
    updates [--check|--install]
    reboot
    shutdown
    lock
    services [--enabled]

  appearance
    theme list
    theme show NAME
    theme set NAME
    wallpaper list
    wallpaper set NAME
    mode dark|light|auto
    dock position bottom|left|right

  security
    status
    firewall status
    firewall profile list
    firewall profile set NAME
    apparmor status
    audit [--output PATH]
    encryption status
    recovery check

  privacy
    status
    tor status
    tor launch
    session explain
    tails verify IMAGE [SIGNATURE]
    tails launch IMAGE

  lab
    status
    setup
    toolsets list
    toolset install NAME
    toolset remove NAME
    container list
    container inspect NAME
    container shell NAME
    container stop NAME
    container destroy NAME
    vm list
    vm create PROFILE
    vm launch NAME
    vm destroy NAME

  dev
    status
    setup [BUNDLE]
    git doctor
    container status
    vm status

  ai
    detect [--json]
    setup [--backend auto|vulkan|cpu]
    backend list
    backend set NAME
    model list
    model add MODEL_ID [--path PATH]
    model remove MODEL_ID
    model verify MODEL_ID
    storage show
    storage set PATH
    server start [MODEL_ID]
    server stop
    server status

  recovery
    status
    snapshots list
    snapshots create LABEL
    snapshots restore ID
    config reset [COMPONENT]

  language
    list
    show
    set en|de|fr

  logs
    show [SERVICE]
    collect [--output PATH]
```

This is a target surface, not a license to stub every command. For v1, implement `version`, `status`, `doctor`, `about`, `system info`, `appearance theme`, `security status`, `lab status/setup/toolsets`, `privacy status/tor`, `ai detect/setup/storage/model`, and `logs collect` at minimum. Only expose further command groups when they have real implementations and tests.

## 8.3 Diagnostic behavior

`hscl doctor` must inspect:

- OS release and package health.
- Disk space and filesystem.
- Memory and CPU architecture.
- GPU and driver details.
- Vulkan runtime availability.
- Secure Boot state where readable.
- AppArmor enabled/disabled and loaded profiles.
- Firewall active state.
- Pending updates.
- Service failures relevant to HSCL1.
- Local AI runtime status.
- Container runtime readiness.
- VM acceleration availability.
- Broken symlinks/config files in HSCL1-owned directories.

The report must redact usernames, hostnames, serial numbers, private IPs, MAC addresses, mounted personal paths, and other identifying values by default. Provide an explicit `--include-sensitive` flag only if necessary and explain it clearly.

## 8.4 Recovery behavior

Repair operations must be narrow and non-destructive. Examples:

- Restore an HCS-owned default theme file from a packaged copy.
- Rebuild an HCS-owned desktop cache.
- Verify and repair package dependencies using apt's supported mechanisms.
- Re-enable a service only if its expected configuration is intact.
- Rebuild a missing HCS user config from a schema-validated default.

Never automatically:

- Delete a user's files.
- Reset the whole desktop without a clear prompt.
- Change partition tables.
- Disable firewall/AppArmor/Secure Boot to “fix” an issue.
- Run `apt autoremove` without showing the removal set.
- Reinstall an OS package from an untrusted repository.

---

# 9. LOCAL AI AND MODEL TOOLING

## 9.1 Purpose

HSCL1 should make local model setup simple without requiring a cloud account or forcing large model downloads. The base ISO must not include multi-gigabyte model weights. Provide a useful CLI and optional Control Center UI that detects hardware and prepares a local inference runtime.

## 9.2 Hardware detection

Detect and report:

- CPU model, architecture, core/thread count, supported instruction sets.
- Total RAM and available RAM.
- GPU model and vendor.
- GPU driver and Vulkan ICD.
- Vulkan device information and usable memory where exposed.
- CUDA presence only as an optional detected backend; do not require CUDA.
- AMD ROCm presence only when the actual hardware and supported distro packages justify it.
- Storage devices, available capacity, filesystem, and mount stability.
- Whether the chosen external storage path is removable and reliably mounted.

Do not infer VRAM from shared memory as if it were dedicated VRAM. Show dedicated and shared memory separately when available.

## 9.3 Backend strategy

- Preferred portable backend: `llama.cpp` with Vulkan when supported by the current hardware/driver.
- Fallback: CPU inference with the best supported instruction-set path.
- Optional backend: ROCm or CUDA only when supported by upstream packages and detected hardware.
- Do not claim GPU acceleration merely because `vulkaninfo` succeeds. Run a small real inference smoke test and confirm the backend log reports the actual selected device.
- Do not silently change to a backend that produces different unsupported behavior; display the fallback and reason.

The user must be able to run:

```bash
hscl ai detect
hscl ai setup --backend auto
hscl ai backend list
hscl ai storage set /path/to/models
hscl ai model add <model-id>
hscl ai model verify <model-id>
hscl ai server start <model-id>
hscl ai server status
```

The command examples above define the intended CLI shape. Implement accurate syntax and help output.

## 9.4 Model catalog and integrity

- Model metadata includes model ID, publisher, source URL, license, model family, format, quantization, approximate RAM/VRAM needs, context length, and checksum if provided by upstream.
- Do not scrape model weights from untrusted mirrors.
- Verify checksum/signature when the upstream publishes one.
- Clearly show license/usage restrictions before download.
- Never execute model files.
- Reject unsafe model formats that depend on arbitrary pickle deserialization unless converted through a safe, sandboxed, explicit workflow.
- Prefer GGUF for the initial local text-model workflow.
- The user chooses storage location. Default can be `~/AI/Models` with an optional external USB 3 drive.
- Handle drive disconnects gracefully and never delete models just because the drive is absent.
- Show estimated download size and required free space before downloading.

## 9.5 Local inference server

If included in v1:

- Bind to `127.0.0.1` by default.
- Expose OpenAI-compatible endpoints only as documented, such as `/v1/models` and `/v1/chat/completions` if the selected runtime supports them.
- Require an explicit user setting before binding to LAN.
- No external telemetry or remote model routing.
- Show model, backend, context configuration, port, and current process state.
- Stop the process cleanly and clean only HSCL1-owned temporary files.
- Do not promise 32K/64K context or a token-per-second value without a measured benchmark on the user's hardware.

## 9.6 AI safety boundary

The local AI feature is a model runtime manager, not a privileged autonomous root agent. Never let an LLM issue arbitrary root commands. Any future AI-action integration must use a permissioned, reviewed tool API with explicit user confirmation for destructive or privileged actions.

---

# 10. MULTILINGUAL EXPERIENCE — EN / DE / FR

## 10.1 Language requirements

Every user-visible HSCL1 string must be localizable. Support:

- English (`en`) — default fallback and canonical source language.
- German (`de`).
- French (`fr`).

This includes:

- Boot menu labels where feasible.
- Installer screens and errors.
- First-boot welcome and onboarding.
- Desktop launcher and Control Center.
- Notifications.
- CLI messages and help text.
- Privacy and security warnings.
- Update and recovery screens.
- Website and README quick-start content.
- Installation and troubleshooting docs.

## 10.2 Translation rules

- Use Qt Linguist `.ts` / `.qm` or the appropriate gettext system for the component. Do not invent a custom translation format unless there is a real need.
- Keep all source strings stable and use translation IDs where supported.
- No concatenated sentence fragments that break grammar in German/French.
- Do not use machine translation as an excuse to ship untranslated or nonsensical security warnings. Have the agent review each translation for correctness, tone, and terminology.
- Keep a translation coverage report.
- A release gate must fail for missing translations in critical installer, security, privacy, and recovery strings.
- Dates, decimals, keyboard labels, and time formats must respect the selected locale.

## 10.3 Language selector

Language can be selected during installer onboarding and changed later from Control Center or `hscl language set`. The language switch should apply without reinstalling the OS and should preserve user data.

---

# 11. FIRST BOOT AND ONBOARDING

Create a first-boot experience that is short, understandable, and optional to skip.

Steps:

1. Welcome to HSCL1 — product explanation and HCS credit.
2. Language — EN/DE/FR.
3. Display — confirm scaling and monitor arrangement.
4. Network — connect if wanted; offline skip is available.
5. Privacy explanation — distinguish normal Workstation mode, Security Lab containers, HSCL1 Privacy Session, and authentic Tails.
6. Security baseline — firewall status, encryption status, update preferences.
7. Desktop navigation — Start menu, dock, workspaces, window snapping, keyboard shortcuts.
8. Optional bundles — Developer, Creator, Security Lab, Local AI. All optional and clearly sized.
9. Recovery — how to open `hscl doctor`, where to find logs, and where recovery documentation lives.
10. Finish — open the desktop.

Do not ask for a cloud account. Do not send onboarding analytics. Remember completed steps locally. The user can restart the tour from the Help menu.

---

# 12. WEBSITE AND VERCEL LANDING PAGE

## 12.1 Website goal

Create a premium, responsive product website that explains HSCL1 clearly, demonstrates the interface, lets visitors verify the release, and helps them install either locally or in a VM.

The website must be deployable to Vercel from the repository. Prefer a static-first architecture; avoid requiring a custom server for the basic download pages. Use the stable versions of the selected framework and package manager at build time, verify current versions, and commit the lockfile.

Recommended stack:

- Astro or Next.js App Router, selected based on the existing repository and actual Vercel build reliability.
- TypeScript.
- Tailwind CSS or a small token-driven CSS system.
- Lightweight React islands only where interaction is useful.
- Static content for documentation and localized pages.
- No external database needed for v1.

Do not select a framework just because it is popular. Test Vercel's current build adapter and deployment behavior before locking the architecture.

## 12.2 Website pages

- `/` — English home.
- `/de/` — German home.
- `/fr/` — French home.
- `/features` / localized equivalent — full feature overview.
- `/screenshots` — real HSCL1 screenshots only; never fake product UI or present concept art as a real OS screenshot.
- `/download` — verified releases, ISO size, SHA256, signature, package manifest, known limitations.
- `/install` — USB installation guide.
- `/install/vm` — VirtualBox and QEMU/KVM guides.
- `/install/bare-metal` — physical PC installation and data-loss warning.
- `/security` — security model, limitations, threat model, disclosure contact.
- `/privacy` — privacy-session explanation and Tails distinction.
- `/docs` — documentation index.
- `/changelog` — release history.
- `/about` — HCSMEDIA credit, open-source information, license notices.

All critical pages must be available in EN, DE, FR.

## 12.3 Homepage structure

1. **Hero:** HSCL1 logo, headline, short description, primary Download button, secondary Explore features button.
2. **Real screenshot:** one authentic captured desktop screenshot after the desktop exists. Before then, use clearly labeled concept art only in development and do not use it as a release screenshot.
3. **Three modes:** Workstation, Security Lab, Privacy.
4. **Unified desktop:** top bar, dock, Start/Applications, tiling, control center.
5. **Built for real machines:** physical PC and VM compatibility, minimum/recommended specs.
6. **Developer and local AI:** terminal, CLI, containers, hardware detection, no model weights bundled.
7. **Security by design:** LUKS2, AppArmor, firewall, isolated lab; state exactly what is tested.
8. **How to install:** USB, VM, or try live.
9. **Downloads:** latest stable version, ISO, checksum, signature, manifest, source.
10. **FAQ:** compatibility, Secure Boot, dual boot, encryption, updates, privacy limitations, Kali tools, AI backend.
11. **Footer:** documentation, source, issues, security contact, license, HCS credit.

## 12.4 Visual design

- Premium dark-first visual design with a light mode.
- Original HSCL1/HCS logo and favicon; use SVG for clean scaling.
- Product screenshots in attractive device frames, but do not obstruct or misrepresent the desktop.
- Subtle gradients, soft glass surfaces, readable contrast, restrained animations.
- Responsive mobile layout; no horizontal overflow.
- Clear download CTA without misleading badges.
- Consistent typography and design tokens with the OS desktop.
- Use motion only for useful transitions and respect `prefers-reduced-motion`.
- Avoid fake customer quotes, fake adoption numbers, unsupported performance claims, and fabricated endorsements.

## 12.5 Download integration

- The stable download button must point to a real GitHub Release asset.
- Display the current stable version, architecture, release date, file size, SHA256, and signature verification instructions.
- Do not hard-code a nonexistent release URL. Generate the download metadata from the actual release during website build or maintain a versioned data file updated by the release workflow.
- If there is no published stable release, display “Release not published yet” and a link to source/build instructions. Never display a fake Download button.
- Make it easy to download the ISO and verify its checksum/signature.
- Keep the latest release and previous release links accessible.

## 12.6 USB guide

Provide clear steps for:

**Windows:**

1. Download the ISO from the official HSCL1 release page.
2. Download a supported USB-writing utility from its official website.
3. Select the USB stick and HSCL1 ISO.
4. Write the image in the mode recommended by the writing utility; explain DD/raw mode if prompted.
5. Warn that the selected USB device will be erased.
6. Reboot and choose the USB from the firmware boot menu.

**Linux:**

- Prefer a supported graphical writer.
- If showing a `dd` command, make it an explicitly dangerous advanced option. Show how to identify the correct block device and insist that the target be checked before writing. Never provide a guessed `/dev/sdX` target.

**macOS:**

- Explain the supported USB-writing process and architecture limitations if relevant.

## 12.7 VM guide

Include exact, tested settings for QEMU/KVM and VirtualBox. Document:

- Firmware (UEFI/BIOS).
- vCPU count.
- RAM.
- Disk size and virtual disk type.
- Display adapter and 3D acceleration caveats.
- Network mode.
- USB passthrough limitations.
- Shared folder safety warning.
- How to mount the ISO and boot.

Do not recommend unsupported hypervisors or untested settings as guaranteed.

## 12.8 SEO and accessibility

- Semantic headings and landmarks.
- Descriptive page titles and meta descriptions in each language.
- Canonical URLs and `hreflang`.
- Open Graph and social preview images.
- Sitemap and robots file.
- JSON-LD only for true SoftwareApplication/Product facts; no fake reviews/ratings.
- Optimized SVG/WebP/AVIF assets.
- Good Core Web Vitals, code splitting, and no unnecessary heavy animation.
- WCAG-oriented color contrast, focus indicators, keyboard navigation, skip links, alt text, accessible download controls.
- Lighthouse and link-check reports in CI.

---

# 13. DOCUMENTATION AND README QUALITY BAR

## 13.1 README must answer the important questions quickly

The root `README.md` must be a polished standalone introduction with:

- HSCL1 name and original logo.
- `Made with love by hcsmedia` credit.
- Clear project status and current release version.
- A concise description of the product.
- The three modes and their security boundaries.
- Desktop feature overview.
- Current screenshots from a real build.
- System requirements.
- Download section with real release links.
- SHA256/signature verification.
- USB installation and VM quick start.
- Installer safety warning.
- CLI quick start.
- Local AI quick start.
- Developer/build instructions.
- Testing and reproducibility.
- Supported hardware table.
- Security and privacy limitations.
- Known issues.
- Roadmap.
- License and third-party notices.
- Contributing and security disclosure links.

The README must never say “fully secure”, “anonymous”, “perfect privacy”, “supports all devices”, or “works on every PC”.

## 13.2 Supporting documentation

Create and maintain:

- `docs/ARCHITECTURE.md` — components, boundaries, diagrams, package sources.
- `docs/BUILDING.md` — exact build host requirements and commands.
- `docs/INSTALLATION.md` — USB and bare-metal install steps.
- `docs/VM_GUIDE.md` — QEMU/KVM and VirtualBox setup.
- `docs/SECURITY.md` — baseline, updates, disclosure process, release integrity.
- `docs/THREAT_MODEL.md` — assets, adversaries, trust boundaries, mitigations, residual risks.
- `docs/PRIVACY_MODE.md` — exact behavior and known gaps.
- `docs/SECURITY_LAB.md` — container and VM isolation model.
- `docs/CLI.md` — all real commands with examples and exit codes.
- `docs/LOCAL_AI.md` — backend setup, GPU detection, storage, license/checksum guidance.
- `docs/HARDWARE_COMPATIBILITY.md` — verified and unverified hardware.
- `docs/TROUBLESHOOTING.md` — boot, Wi-Fi, drivers, graphics, install, update, recovery.
- `docs/TESTING.md` — how to reproduce tests.
- `docs/RELEASE_PROCESS.md` — signing, checksums, tag, GitHub release, Vercel deployment.
- `docs/LICENSES.md` — software licenses and attributions.
- `docs/KNOWN_LIMITATIONS.md` — accurate scope.
- `docs/BUILD_LOG.md` — ongoing engineering record.

## 13.3 Documentation correctness

- Commands must be tested exactly as written.
- Links must be checked.
- Screenshots must come from the actual release candidate.
- Environment-specific paths must be labeled as examples.
- No documentation may instruct users to disable important security features merely to make an untested feature work.
- All warnings must be localized.

---

# 14. TESTING AND QUALITY ENGINEERING

## 14.1 Test layers

### Static and style checks

- ShellCheck on shell scripts.
- shfmt formatting check.
- Python lint/type checks (Ruff and mypy/pyright if Python is used).
- Rust fmt, clippy, and tests.
- QML lint/compile checks.
- TypeScript/ESLint/Prettier or the selected frontend tooling.
- Translation completeness and duplicate-key checks.
- Markdown link validation and formatting.
- YAML/JSON schema validation.

### Unit tests

- CLI argument parsing and exit codes.
- Config parsing and schema validation.
- Theme validation and rollback.
- Hardware detection parsing.
- Firewall profile generation.
- Privacy-mode policy evaluation.
- Model catalog parsing and checksum validation.
- Installer config generation.
- Localization selection and fallback.
- Privileged helper authorization and input validation.

### Integration tests

- UI to CLI/backend integration.
- Polkit action authorization.
- APT package manifest consistency.
- Podman rootless setup and Kali image startup.
- Container mount/network policy.
- Local AI backend detection and tiny-model smoke test.
- Update and recovery workflow on a disposable system.

### VM tests

- Boot live ISO.
- Verify desktop session starts.
- Open Start menu and Control Center.
- Verify language selection for EN/DE/FR.
- Launch installer.
- Run unencrypted install to a disposable qcow2 disk.
- Run LUKS2 install to a disposable qcow2 disk.
- Reboot installed system.
- Verify system info, update service, firewall, AppArmor, and `hscl doctor`.
- Verify live ISO and installed system have correct product name and version.
- Capture screenshots from the real desktop for docs/website.

### Security tests

- Check APT sources for unintended Kali/Debian/Ubuntu interim repositories.
- Check for unsigned package repos.
- Scan repository for secrets.
- Check Polkit rules for broad permissions.
- Check privileged helper for injection/path traversal.
- Check systemd services for unnecessary capabilities and writable paths.
- Check container config for privileged mode, host networking, broad mounts, socket mounts, and host PID namespace.
- Test privacy-mode non-Tor egress behavior with packet capture.
- Test no internal disk auto-mount in Privacy Live.
- Verify that the Privacy Live mode cannot silently fall back to direct web traffic.
- Check that logs/reports redact sensitive values by default.

### Website tests

- Production build.
- All EN/DE/FR route availability.
- Download links resolve to actual artifacts.
- Checksums shown match the release.
- No broken internal/external links.
- Keyboard navigation and mobile responsive checks.
- Lighthouse smoke tests.
- Correct metadata and language alternates.

## 14.2 Release gates

`v1.0.0` cannot be published as stable unless all of these are true:

- [ ] The ISO builds from repository scripts.
- [ ] The ISO hash and manifest are generated from the actual artifact.
- [ ] The ISO boots in QEMU/KVM UEFI.
- [ ] Secure Boot status is tested and documented accurately.
- [ ] The live desktop starts and is usable.
- [ ] The graphical installer starts.
- [ ] A disposable VM install completes.
- [ ] The installed VM reboots into the desktop.
- [ ] LUKS2 installation/unlock is tested if encryption is advertised.
- [ ] The default desktop, launcher, dock, and Control Center function.
- [ ] EN/DE/FR critical UI coverage is complete.
- [ ] `hscl doctor` completes and reports truthful status.
- [ ] Host APT sources contain no Kali repository.
- [ ] Security Lab containers do not have unsafe defaults.
- [ ] Privacy-related claims match test evidence.
- [ ] No known critical/high unmitigated vulnerability in HSCL1-owned code/dependencies remains without explicit, documented acceptance by the release owner.
- [ ] README and installation guides match the release.
- [ ] SBOM, checksum, and signature verification instructions exist.
- [ ] GitHub Release asset links point to the uploaded files.
- [ ] Vercel production build succeeds.
- [ ] Known limitations are published.

If any critical item fails, release a clearly labeled preview or RC instead of falsely publishing stable v1.0.0.

## 14.3 Visual QA

Capture at least:

- First boot desktop.
- Start menu open.
- Control Center overview.
- Appearance settings.
- Security Lab panel.
- Privacy status page.
- Installer welcome and disk selection screen (using a disposable VM only).
- Local AI detection screen.
- Lock screen.

Review on 1366×768 and 1920×1080. Confirm text is not clipped, dock is not overlapping windows, status icons are not hidden, focus state is visible, and language strings fit. Keep real OS screenshots separate from marketing concept art.

---

# 15. SELF-HEALING AND AUTONOMOUS ENGINEERING LOOPS

## 15.1 Repair loop

For every failing build/test gate:

1. Record the command, environment, exit code, timestamp, and log path.
2. Classify the failure: code defect, dependency drift, network/transient failure, environment capacity, upstream breakage, missing feature, or flaky test.
3. Reproduce the failure with the smallest deterministic test possible.
4. Identify the root cause before changing code.
5. Make the smallest safe patch.
6. Run the targeted test.
7. Run the affected subsystem test suite.
8. Run the complete required gate set.
9. Record the fix and evidence in `docs/BUILD_LOG.md`.

## 15.2 Limits on automatic retries

- Retry transient network/download failures at most two times with backoff and checksum verification.
- For code defects, do not rerun the same command blindly. Change code or test setup only after identifying a cause.
- Maximum three automatic fix-and-retest iterations per distinct failing gate before stopping and documenting the blocker.
- Never skip an assertion, weaken a security test, lower coverage thresholds, suppress a compiler warning, or edit test expectations solely to get a pass.
- Do not disable Secure Boot, AppArmor, firewall, encryption, or sandboxing as an automatic repair.
- Do not delete caches or user files unless the cache is clearly HSCL1-owned, safely regenerable, and the action is logged.

## 15.3 Change protection

Before each large operation:

- Check `git status`.
- Confirm the current branch.
- Confirm the target directory and available space.
- Keep user-owned files outside build output directories.
- Use disposable VM disks for destructive tests.
- Store generated artifacts outside tracked source directories unless they are official small release files.

## 15.4 Visual self-healing

When a screenshot shows a UI defect:

1. Reproduce at the same resolution and scale.
2. Identify whether it is a layout, font, translation, accessibility, theme, window manager, or display-scaling issue.
3. Fix the canonical component or token rather than hard-coding per-screen patches.
4. Capture before/after screenshots.
5. Recheck light/dark modes and EN/DE/FR text.

## 15.5 Build health report

Maintain `docs/BUILD_LOG.md` with:

- Phase and date.
- Current commit SHA.
- Toolchain and package versions.
- Build/test commands.
- Pass/fail statuses.
- Artifact hashes.
- Known blockers.
- Next safe actions.

Never put secrets, passphrases, personal data, or private logs in this file.

---

# 16. IMPLEMENTATION ROADMAP — EXECUTE IN ORDER

The agent must work through each phase. Do not jump to release packaging before the bootable system is real.

## Phase 0 — Repository and environment reconnaissance

Tasks:

1. Inspect the whole repository, active instructions, branches, remotes, tags, releases, CI workflows, and working tree.
2. Identify whether this is a new repository or an existing project.
3. Detect the operating system, CPU architecture, available RAM, free disk, `KVM`/`/dev/kvm`, UEFI tools, Docker/Podman, and build dependencies.
4. Check authenticated GitHub identity and repository permissions without printing tokens.
5. Check Vercel integration/CLI availability without printing secrets.
6. Verify current Ubuntu/Kubuntu 26.04.1 ISO metadata and official checksum/signature.
7. Verify the current `resolute` package versions for Plasma, Calamares, casper/live boot tooling, kernel, QEMU, Podman, and required libraries.
8. Write a short feasibility report and a phased technical decision record.

Acceptance:

- No source files overwritten.
- Repository state recorded.
- Upstream base packages verified.
- Image pipeline options compared.
- Build host capacity assessed.

## Phase 1 — Product architecture and design foundation

Tasks:

1. Create the architecture diagram and package-source policy.
2. Define the threat model and limitations.
3. Define product versioning and release channels.
4. Define HCS branding, logo concept, color tokens, typography, spacing, and icon rules.
5. Define the desktop layout and hotkey map.
6. Define EN/DE/FR localization infrastructure.
7. Create real package manifests with categories and licensing notes.
8. Create `docs/BUILD_LOG.md`, `docs/ARCHITECTURE.md`, `docs/THREAT_MODEL.md`, and `docs/KNOWN_LIMITATIONS.md`.

Acceptance:

- Design tokens are centralized.
- No fake packages or unsupported claims.
- All architectural boundaries are documented.

## Phase 2 — Image pipeline proof of concept

Tasks:

1. Download/obtain the official supported base ISO using HTTPS and official signature/checksum validation.
2. Build an isolated, scripted PoC.
3. Add one HCS package, one background, and a release marker.
4. Rebuild an ISO.
5. Inspect ISO structure and manifests.
6. Boot in QEMU BIOS and UEFI.
7. Launch the live desktop.
8. Launch the chosen installer.
9. Test the Secure Boot chain if claimed.
10. Record all failures and choose the reproducible image pipeline.

Acceptance:

- Actual booted ISO, not just a build log.
- Rebuild commands checked in.
- Build dependencies documented and pinned.
- Decision record explains the chosen path.

## Phase 3 — Base OS and package configuration

Tasks:

1. Pin Ubuntu 26.04 LTS repositories.
2. Add Plasma 6.6 LTS and essential desktop packages.
3. Configure systemd, NetworkManager, audio, Bluetooth, printing, and firmware packages.
4. Enable AppArmor and the selected firewall manager.
5. Configure baseline user/session defaults.
6. Configure apt and Flatpak policy.
7. Remove unnecessary packages only after dependency analysis.
8. Create a package manifest and verify offline install requirements.

Acceptance:

- Host package sources are clean.
- Base package installation succeeds in a disposable rootfs.
- Booted desktop has network/audio/graphics basics in VM.

## Phase 4 — HSCL1 visual identity and desktop shell

Tasks:

1. Implement logo, wallpapers, icon style, fonts, and color themes.
2. Build the top panel and dock/taskbar using supported Plasma mechanisms.
3. Configure Start/Applications launcher and search.
4. Configure window behavior, shortcuts, workspaces, and tiling.
5. Build the HCS welcome/onboarding flow.
6. Build the Control Center shell with real integrations.
7. Add the About screen and HCS credit.
8. Test all UI flows with mouse and keyboard.

Acceptance:

- Real Plasma desktop, not a web mockup.
- Core launcher/dock/panel/Control Center work.
- UI works at both required resolutions.
- Keyboard shortcut reference matches actual bindings.

## Phase 5 — CLI, diagnostics, and privileged operations

Tasks:

1. Implement the `hscl` CLI foundation.
2. Implement version, status, about, doctor, report, system info, theme commands, and security status.
3. Create narrow privileged helper APIs and Polkit actions.
4. Add logging with safe redaction.
5. Add schema validation and tests.
6. Integrate CLI actions into the launcher and Control Center.

Acceptance:

- Commands work on the real installed VM.
- JSON output is valid and documented.
- No arbitrary shell execution from UI.
- Invalid privilege requests fail safely.

## Phase 6 — Installer and installed-system path

Tasks:

1. Integrate the real graphical installer.
2. Configure language, keyboard, user, timezone, partitioning, and bootloader modules.
3. Implement the supported non-encrypted install path.
4. Implement LUKS2 passphrase encryption and recovery-key path.
5. Add destructive-operation warnings and confirmation.
6. Install HSCL1 packages and desktop defaults to the target disk.
7. Add post-install validation.
8. Test offline and networked installs.
9. Test reboot into the installed VM.

Acceptance:

- Successful disposable VM install and reboot.
- Correct user account and locale.
- Correct bootloader and filesystem.
- No password/recovery-key data in logs.
- Installer fails safely on injected errors.

## Phase 7 — Security baseline and Security Lab

Tasks:

1. Implement the firewall default profile and test it.
2. Verify AppArmor loads the expected profiles.
3. Check listening services.
4. Build rootless Podman setup.
5. Pull official Kali container image and pin digest.
6. Create curated toolsets and workspace paths.
7. Implement container inspection, safe mount selection, network modes, update, and destroy.
8. Add optional disposable VM profiles for tools requiring kernel/hardware access.
9. Integrate the lab status and authorization reminder into the Control Center.

Acceptance:

- No Kali repository in host APT sources.
- Container defaults are not privileged.
- Host home and credential sockets are not mounted.
- Container lifecycle works in VM.
- Security Lab disabled by default on clean install.

## Phase 8 — Privacy workflows

Tasks:

1. Implement Tor Browser installation/launch from a verified supported source.
2. Show real Tor status and meaningful failure messages.
3. Prevent direct fallback for the Tor-specific app workflow.
4. Implement privacy-related app permission and history controls.
5. Decide whether the ephemeral Privacy Live mode can be reliably implemented within v1.
6. If implemented, configure RAM overlay, no internal auto-mount, no swap/hibernation, journal handling, network policy, and shutdown behavior.
7. Packet-capture test DNS, IPv4, IPv6, Tor unavailable, and browser traffic.
8. Add authentic Tails ISO verification/launcher only with verified signature instructions and safe external ISO handling.
9. Document the threat model and residual risks.

Acceptance:

- Every advertised privacy guarantee has a test or is removed from the marketing copy.
- No false claim of Tails equivalence.
- A failed Tor connection does not silently result in direct egress from the privacy workflow.

## Phase 9 — Local AI CLI and optional UI

Tasks:

1. Implement CPU/GPU detection.
2. Implement Vulkan detection and smoke inference where possible.
3. Provide safe CPU fallback.
4. Install or build the chosen llama.cpp backend reproducibly.
5. Implement model storage and catalog metadata.
6. Implement checksums, license prompts, storage path management, and external-drive handling.
7. Add a tiny, redistributable/test model only if its license permits; otherwise use a tiny fixture/model download in tests with a clear source and checksum.
8. Add a Control Center local AI page if it reflects actual behavior.
9. Add an optional localhost-only OpenAI-compatible endpoint if the chosen runtime supports it and tests pass.

Acceptance:

- `hscl ai detect` returns accurate hardware information.
- CPU mode works.
- Vulkan mode is reported only after actual backend verification.
- No large model weights bundled in the ISO.
- Model downloads do not write outside the selected storage path.

## Phase 10 — Multilingual polish and accessibility

Tasks:

1. Complete EN/DE/FR translations.
2. Test installer translations.
3. Test desktop layout under longer German and French strings.
4. Test keyboard navigation and screen-reader labels.
5. Test reduced motion, high contrast, scaling, and small screens.
6. Check date/time/number locale formatting.
7. Verify that locale changes do not reset user settings.

Acceptance:

- No untranslated critical strings.
- No clipped critical buttons/warnings.
- Usable keyboard-only installer and Control Center.

## Phase 11 — Full integration, hardening, and release candidate

Tasks:

1. Run all static checks, unit tests, integration tests, and VM tests.
2. Run installer fault-injection tests.
3. Run security scans and review findings.
4. Check dependency licenses.
5. Generate SBOM and build manifest.
6. Build a release-candidate ISO from a clean environment.
7. Boot and install the exact RC artifact.
8. Capture genuine screenshots.
9. Fix all critical/high issues or document and explicitly accept a narrow non-blocking issue.
10. Update known limitations and changelog.

Acceptance:

- Every v1 release gate passes.
- Actual RC artifact hash recorded.
- No unresolved critical issue.
- Documentation matches actual artifact.

## Phase 12 — README, Vercel site, and public release

Tasks:

1. Finalize README and docs.
2. Finish EN/DE/FR website content.
3. Verify the Vercel production build.
4. Configure Vercel project from the existing authorized account/integration if available.
5. Build and test a production preview before production deployment.
6. Publish `v1.0.0` Git tag only after release gates pass.
7. Upload ISO, checksum, signature, manifest, SBOM, and release notes to GitHub Release.
8. Verify every uploaded asset can be downloaded and checksums match.
9. Update website download metadata to point to the published release.
10. Deploy website to Vercel and verify production URLs.
11. Record commit SHA, tag SHA, release URL, website URL, artifact size, and SHA256 in `docs/BUILD_LOG.md`.

Acceptance:

- GitHub release is real and publicly accessible if repository visibility is public.
- No release URL is fabricated.
- Vercel site uses verified release metadata.
- Release artifacts are signed or the exact signing limitation is disclosed.

---

# 17. GITHUB, BRANCHING, AND RELEASE POLICY

## 17.1 Repository discovery

If a remote is already configured:

- Identify its owner/repository and visibility.
- Preserve the repository's existing naming and conventions.
- Do not create a duplicate repository.
- Inspect branch protection and required checks.
- Do not change public/private visibility without explicit permission.

If no remote exists:

- Check authenticated GitHub identity using the approved GitHub CLI/API without exposing secrets.
- Check whether the intended `HSCL1` repository already exists under the authenticated owner/organization.
- If it exists, confirm it is the intended repository before pushing.
- If it does not exist and the connected agent has permission to create it, create `HSCL1` with the intended visibility only when that visibility is explicitly established in the current task/repository context. Prefer public for an open-source OS only if the repository owner has authorized that choice. If visibility is not established, stop before repo creation and report the one required decision.

## 17.2 Branch policy

- Never force push.
- Never rewrite commits that are already on the remote.
- Create a clear working branch such as `codex/hscl1-v1` unless the current repository instructions require another convention.
- Commit coherent stages with descriptive messages.
- Preserve unrelated local changes.
- Push the working branch.
- Open a pull request to the default branch when PR workflows/branch protections require it.
- If the user explicitly authorized autonomous merge and the checks pass, merge using the repository's permitted merge method. Do not bypass required checks.

## 17.3 Release policy

- Follow semantic versioning.
- Use `v1.0.0` only after the stable gates pass.
- If a gate is blocked, publish `v0.1.0-alpha`, `v0.9.0-rc.1`, or a suitable prerelease only if it is useful and clearly marked. Do not call a preview stable.
- Tag the exact release commit.
- Sign the tag if the available release key supports it.
- Generate checksums only after the final artifact is built.
- Upload only release assets that have passed validation.
- Verify the downloaded release files after upload.
- Write release notes based on actual changes and known issues.
- Do not upload VM disks containing credentials, personal data, or user information.

## 17.4 Vercel deployment

- Detect an existing Vercel project before creating a new one.
- Preserve existing project settings and domains.
- Use environment variables through the connected service; never commit them.
- Preview deployment first, production only after tests.
- If Vercel credentials are unavailable, still complete the deployable site, add deployment instructions, and report that live deployment was blocked by credentials. Do not pretend it is deployed.

---

# 18. BUILD HOST REQUIREMENTS AND REPRODUCIBILITY

## 18.1 Build host

The image build requires a Linux x86_64 host or equivalent Linux VM with:

- Rootful build capability inside an isolated builder or a carefully controlled container/VM.
- At least 8 CPU threads recommended.
- 16 GB RAM recommended; more is helpful for squashfs compression.
- At least 100 GB free SSD space for full ISO unpack/build/test cycles.
- QEMU/KVM acceleration recommended.
- `squashfs-tools`, `xorriso`, `grub`/EFI utilities, `debootstrap` or the selected official tooling, `ovmf`, `qemu-system-x86`, `qemu-utils`, `shellcheck`, `shfmt`, and build dependencies.

The exact package list must be captured in `scripts/bootstrap-build-host.sh` or an equivalent reproducible tool manifest. Check current package names on Ubuntu 26.04 before implementing.

## 18.2 Reproducible builds

Aim for reproducibility. Where upstream timestamps or package archive state prevent bit-for-bit identical ISO output:

- Pin the package snapshot/mirror state where supported.
- Record package versions and build timestamps.
- Normalize file timestamps when safe.
- Use a fixed locale and timezone in the builder.
- Record all sources and build dependencies.
- Generate manifests from the finished image.
- Explain the exact reproducibility level.

Never claim bit-for-bit reproducible if rebuilding produces different binaries or package sets.

## 18.3 Build script requirements

Every build script must:

- Use strict error handling (`set -Eeuo pipefail` for Bash where appropriate).
- Validate arguments.
- Check required commands.
- Check free disk space.
- Use a dedicated build directory.
- Refuse to run as root on the host unless the isolated build method specifically requires it and is documented.
- Never overwrite a user-supplied output file without a clear `--force` option.
- Trap cleanup safely.
- Preserve logs on failure.
- Avoid unquoted variables and unsafe `eval`.
- Verify downloaded inputs and package signatures.
- Print a summary before expensive/destructive steps.
- Return non-zero on failure.

---

# 19. LICENSES, BRANDING, AND UPSTREAM ATTRIBUTION

- HSCL1-owned code must have an explicit license selected by the repository owner. If no license exists, do not assume one; propose a license choice and document the blocker before public release.
- Include `NOTICE` and `docs/LICENSES.md`.
- Preserve copyright and license notices for upstream packages, icons, fonts, wallpapers, and tools.
- Use original HCS logo and original HSCL1 wallpapers or assets with verified permissive licenses.
- Do not copy macOS, Windows, Omarchy, Kali, or Tails logos and trademarks into the HSCL1 brand.
- Describe integrations accurately: “Kali tools in isolated containers” and “Tails ISO launcher”, not “Kali-based OS” or “Tails edition” unless the respective distribution legally and technically endorses that description.
- Check redistribution permissions for every bundled binary, firmware blob, font, theme, and artwork.
- Provide third-party license access from the About screen and website.
- Do not bundle non-free codecs, proprietary drivers, or fonts without checking the license and explaining the package source.

---

# 20. EXACT DEFINITION OF DONE FOR HSCL1 V1.0.0

A stable v1.0.0 is complete only when all of these deliverables exist and are verified:

## OS and boot media

- [ ] Ubuntu 26.04 LTS base manifest pinned and documented.
- [ ] Plasma 6.6 LTS desktop configured.
- [ ] Original HSCL1 theme and visual identity.
- [ ] Hybrid Live/Installer ISO built by repository scripts.
- [ ] ISO boots in QEMU UEFI and at least one BIOS profile if supported.
- [ ] Secure Boot behavior accurately documented and tested.
- [ ] Live desktop works.
- [ ] Graphical installer works.
- [ ] Installed VM boots after installation.
- [ ] LUKS2 passphrase encryption tested if exposed.

## User experience

- [ ] Top panel, dock/taskbar, launcher, window switcher, workspaces, and snapping work.
- [ ] Control Center is functional and reflects real state.
- [ ] Mouse and keyboard workflows both work.
- [ ] First boot/onboarding is complete and skippable.
- [ ] EN/DE/FR UI coverage is complete for critical workflows.
- [ ] Accessibility and small-screen tests pass.

## Security modes

- [ ] Workstation baseline enabled and documented.
- [ ] AppArmor and firewall status verifiable.
- [ ] Security Lab uses isolated rootless containers or isolated VMs.
- [ ] Host APT sources contain no Kali repo.
- [ ] No unnecessary credentials or host folders are exposed to lab containers.
- [ ] Privacy claims are limited to tested capabilities.
- [ ] Tails is treated as a separate official distribution.

## CLI and AI

- [ ] `hscl` version/status/doctor commands work.
- [ ] Theme and security status commands work.
- [ ] Security Lab status/setup commands work or are excluded from stable help if unfinished.
- [ ] `hscl ai detect` works.
- [ ] CPU fallback works.
- [ ] Vulkan backend is verified on a supported test environment or shown as unavailable.
- [ ] Model storage path and integrity checks work.
- [ ] No large weights are bundled by default.

## Quality and release

- [ ] CI passes.
- [ ] VM boot and install tests pass.
- [ ] Security scans are reviewed.
- [ ] SBOM, manifest, checksum, and signature are published or limitations disclosed.
- [ ] README and complete docs match v1.
- [ ] Vercel site builds and is deployed if credentials are available.
- [ ] GitHub Release `v1.0.0` exists only after all stable gates pass.
- [ ] Download links are verified.
- [ ] Known limitations and hardware compatibility table are public.

If one or more critical items cannot be completed, deliver the best working prerelease and a precise gap report. Do not fake a v1.0.0 stable milestone.

---

# 21. FINAL EXECUTION INSTRUCTIONS TO THE AGENT

Start now. Do not answer with a plan only. Inspect the repository and environment, then execute the phases in order. Build real code and artifacts. Use the available MCP and coding tools when they materially help. Research upstream documentation whenever a version, package, or security assumption may have changed.

At each phase:

1. State the current phase in `docs/BUILD_LOG.md`.
2. Implement the smallest usable vertical slice.
3. Run its tests.
4. Fix failures using the self-healing rules.
5. Update documentation and translations.
6. Commit the completed stage to the working branch when appropriate.
7. Continue to the next phase without waiting for user confirmation for ordinary implementation decisions already specified here.

Ask for user input only when a decision is truly blocking and cannot be safely inferred, such as repository visibility/ownership when no remote exists, an unavailable signing key that the release requires, or an irreversible account-level deployment decision. Do not ask the user to repeat information already available in the repository or connected tools.

Before final release, produce a report containing:

- What was actually built.
- Exact base distribution and package versions.
- ISO filename, size, and SHA256.
- VM boot/install results with evidence.
- Secure Boot result.
- Encryption result.
- Security Lab isolation result.
- Privacy-mode tests and limitations.
- Local AI backend results.
- EN/DE/FR coverage.
- Test summary and unresolved findings.
- Git branch, commit, tag, GitHub release URL.
- Vercel production URL or the exact credential/deployment blocker.
- Known limitations and recommended next milestone.

The guiding rule is simple: **make HSCL1 genuinely usable, safe by default, visually coherent, testable, and honest. Ship only what the evidence supports.**

---

# APPENDIX A — UPSTREAM RESEARCH LINKS

Revalidate all links and package versions before release.

## Omarchy

- https://omarchy.org/manual/
- https://omarchy.org/manual/updates/
- https://learn.omacom.io/2/the-omarchy-manual

## Ubuntu / Kubuntu

- https://documentation.ubuntu.com/release-notes/26.04/
- https://documentation.ubuntu.com/release-notes/26.04/summary-for-lts-users/
- https://ubuntu.com/about
- https://www.kubuntu.org/news/kubuntu-26-04-release-notes/
- https://www.kubuntu.org/news/plasma-6.6-lts/
- https://ubuntu.com/security/platform-security
- https://documentation.ubuntu.com/security/security-features/storage/encryption-full/
- https://ubuntu.com/desktop/docs/en/latest/how-to/encrypt-your-disk-with-tpm/

## Kali

- https://www.kali.org/docs/introduction/should-i-use-kali-linux/
- https://www.kali.org/docs/general-use/metapackages/
- https://www.kali.org/docs/containers/official-kalilinux-docker-images/
- https://www.kali.org/docs/containers/using-kali-linux-docker-images/

## Tails

- https://tails.net/about/index.en.html
- https://tails.net/doc/anonymous_internet/index.en.html
- https://tails.net/doc/persistent_storage/index.en.html
- https://tails.net/doc/about/warnings/index.en.html

## Image building and installation

- https://ubuntu.com/project/docs/how-ubuntu-is-made/processes/image-builds/
- https://ubuntu.com/hardware/docs/image-cookbook/howto/images/customize_installer_image/
- https://calamares.codeberg.page/
- https://github.com/calamares/calamares
- https://live-team.pages.debian.net/live-manual/html/live-manual/index.en.html
- https://github.com/archlinux/archiso (reference only; not the selected host distribution)

---

# APPENDIX B — RELEASE METADATA TEMPLATE

Create `release/manifest.json` or an equivalent generated manifest using actual values. Do not commit placeholder values to a release.

```json
{
  "product": "HSCL1",
  "version": "1.0.0",
  "channel": "stable",
  "architecture": "amd64",
  "base": "Ubuntu 26.04 LTS (resolute)",
  "desktop": "KDE Plasma 6.6 LTS",
  "artifact": "HSCL1-v1.0.0-amd64.iso",
  "sha256": "GENERATE_FROM_FINAL_ARTIFACT",
  "build_commit": "ACTUAL_GIT_COMMIT",
  "build_date_utc": "ACTUAL_BUILD_TIMESTAMP",
  "secure_boot": {
    "supported": false,
    "notes": "Replace with the measured result for the exact release artifact."
  },
  "tested_in_vm": false,
  "languages": ["en", "de", "fr"],
  "website": "ACTUAL_VERCEL_PRODUCTION_URL",
  "release_url": "ACTUAL_GITHUB_RELEASE_URL"
}
```

The above is a schema example only. Replace every placeholder, boolean, URL, and support statement with real release evidence before publishing. A release workflow must fail if placeholder strings remain.

# APPENDIX C — VISUAL ACCEPTANCE CHECKLIST

- [ ] HSCL1 logo is original, crisp, and consistent in boot, installer, desktop, About, and website.
- [ ] Top panel is legible and balanced.
- [ ] Dock/taskbar clearly distinguishes pinned and running apps.
- [ ] Start menu search works with keyboard immediately after opening.
- [ ] Control Center uses the same spacing, typography, and icon rules as the rest of the OS.
- [ ] Dialogs use consistent title bars, buttons, warnings, and focus states.
- [ ] Notifications do not cover important controls.
- [ ] System tray status is readable and keyboard-accessible.
- [ ] Light and dark themes both have sufficient contrast.
- [ ] German and French labels do not overflow.
- [ ] 1366×768 and 1920×1080 layouts look intentional.
- [ ] Reduced-motion mode disables nonessential animations.
- [ ] No copyrighted Apple/Windows/Kali/Tails/Omarchy brand assets are copied.
- [ ] Real screenshots are used in release docs and the website.

# APPENDIX D — SAFETY-CRITICAL ACCEPTANCE CHECKLIST

- [ ] Installer disk selection is explicit.
- [ ] Destructive changes are summarized before confirmation.
- [ ] CI installer tests use disposable virtual disks only.
- [ ] LUKS passphrases and recovery keys never appear in logs.
- [ ] Host APT does not include Kali repositories.
- [ ] Kali containers are rootless and do not mount host credentials.
- [ ] Privacy mode has no direct-network fallback if Tor is required.
- [ ] Privacy mode does not auto-mount internal disks.
- [ ] No claim of Tails-equivalent anonymity is present.
- [ ] `hscl doctor` redacts sensitive values by default.
- [ ] Privileged helper does not accept arbitrary commands.
- [ ] GitHub/Vercel secrets are not in source or build logs.
- [ ] Release checksum matches the final downloadable ISO.
- [ ] Known limitations are visible to users.
