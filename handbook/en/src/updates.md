# Updates

HSCL1 receives updates through APT from the Ubuntu 26.04 LTS (`resolute`) archives. Nothing is sent to an HSCL1 server.

## Check for updates

```console
$ hscl system updates --check
```

This is a simulation: it lists what could be upgraded, how many packages come from the security pocket and whether a
restart is required. It installs nothing. If apt itself is broken, the command reports an error instead of "0 updates".

## Installed system

- **Security updates** are installed automatically (unattended upgrades, security pocket only).
- Other updates are installed by you, for example in Discover or with `sudo apt update && sudo apt upgrade`.
- HSCL1 never restarts the computer by itself. When a restart is required, `hscl system updates --check` says so.

## Live session

The live ISO is read-only. Changes, including installed updates, are lost when you shut down. To get newer packages
permanently, install HSCL1 or use a newer image.

## Prebuilt image

The prebuilt disk image updates like an installed system. A newer image is only needed for a fresh start.
