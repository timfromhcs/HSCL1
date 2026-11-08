# HSCL1 Keyboard Shortcuts Reference

> **Product:** HSCL1 OS  
> **Publisher:** HCSMEDIA  
> **Credit:** Made with love by hcsmedia  
> **Configuration Source:** `/etc/xdg/kglobalshortcutsrc` & Look-and-Feel defaults  

HSCL1 uses `Meta` (Super / Windows key) as the primary desktop modifier for keyboard-driven productivity and window management, preventing collisions with standard terminal (`Ctrl+C`, `Ctrl+Z`) and application shortcuts.

---

## 1. Primary Shortcuts Overview

| Shortcut | Action | Component / Target | Configuration Key |
|---|---|---|---|
| `Meta` | Open Start / Applications menu | Plasma Kickoff | `[plasmashell]` `activate application launcher=Alt+F1` (Meta triggered) |
| `Meta + Space` | Focus launcher search | KRunner | `[org.kde.krunner.desktop]` `_launch=Meta+Space\tAlt+Space` |
| `Meta + Enter` | Open terminal | Konsole | `[org.kde.konsole.desktop]` `_launch=Meta+Return\tCtrl+Alt+T` |
| `Ctrl + Alt + T` | Open terminal (fallback) | Konsole | `[org.kde.konsole.desktop]` `_launch=Meta+Return\tCtrl+Alt+T` |
| `Meta + E` | Open file manager | Dolphin | `[org.kde.dolphin.desktop]` `_launch=Meta+E` |
| `Meta + D` | Show desktop | KWin | `[kwin]` `Show Desktop=Meta+D` |
| `Meta + Tab` | Switch applications | KWin Window Switcher | `[kwin]` `Walk Through Windows=Meta+Tab\tAlt+Tab` |
| `Meta + K` | Open shortcut reference | HSCL1 Shortcuts | `[hscl-shortcuts.desktop]` `_launch=Meta+K` |
| `Meta + ,` | Open Control Center | HSCL1 Control Center | `[hscl-control-center.desktop]` `_launch=Meta+,` |
| `Meta + L` | Lock screen | ksmserver | `[ksmserver]` `Lock Session=Meta+L\tScreensaver` |
| `Meta + Shift + S` | Rectangular region screenshot | Spectacle | `[org.kde.spectacle.desktop]` `RectangularRegionScreenShot=Meta+Shift+S\tMeta+Shift+Print` |
| `Meta + Left` | Snap window left (Quick Tile) | KWin | `[kwin]` `Window Quick Tile Left=Meta+Left` |
| `Meta + Right` | Snap window right (Quick Tile) | KWin | `[kwin]` `Window Quick Tile Right=Meta+Right` |
| `Meta + Up` | Maximize window | KWin | `[kwin]` `Window Maximize=Meta+Up` |
| `Meta + Down` | Minimize window / restore | KWin | `[kwin]` `Window Minimize=Meta+Down` |
| `Meta + 1..9` | Switch to virtual desktop 1 to 9 | KWin | `[kwin]` `Switch to Desktop 1..9=Meta+1..9` |
| `Meta + 1` | Switch to virtual desktop 1 | KWin | `[kwin]` `Switch to Desktop 1=Meta+1` |
| `Meta + 2` | Switch to virtual desktop 2 | KWin | `[kwin]` `Switch to Desktop 2=Meta+2` |
| `Meta + 3` | Switch to virtual desktop 3 | KWin | `[kwin]` `Switch to Desktop 3=Meta+3` |
| `Meta + 4` | Switch to virtual desktop 4 | KWin | `[kwin]` `Switch to Desktop 4=Meta+4` |
| `Meta + 5` | Switch to virtual desktop 5 | KWin | `[kwin]` `Switch to Desktop 5=Meta+5` |
| `Meta + 6` | Switch to virtual desktop 6 | KWin | `[kwin]` `Switch to Desktop 6=Meta+6` |
| `Meta + 7` | Switch to virtual desktop 7 | KWin | `[kwin]` `Switch to Desktop 7=Meta+7` |
| `Meta + 8` | Switch to virtual desktop 8 | KWin | `[kwin]` `Switch to Desktop 8=Meta+8` |
| `Meta + 9` | Switch to virtual desktop 9 | KWin | `[kwin]` `Switch to Desktop 9=Meta+9` |

---

## 2. Window Snapping & Tiling Layouts

- **Quarter Tiling:** Combine `Meta + Left` / `Meta + Right` followed by `Meta + Up` / `Meta + Down` to tile windows into screen corners.
- **Toggle Overview:** Press `Meta + W` to view an overview of all active windows and virtual desktops.
- **Cycle Applications in Reverse:** Press `Meta + Shift + Tab` or `Alt + Shift + Tab`.

---

## 3. Customization & Overrides

Per-user shortcut customizations are saved in `~/.config/kglobalshortcutsrc` and override the system defaults shipped in `/etc/xdg/kglobalshortcutsrc`. Shortcuts can be modified via:

1. **GUI:** System Settings -> Keyboard -> Shortcuts.
2. **Control Center:** Open HSCL1 Control Center (`Meta + ,`).
3. **CLI:** `kwriteconfig6 --file kglobalshortcutsrc --group <component> --key <action> <shortcut>`.
