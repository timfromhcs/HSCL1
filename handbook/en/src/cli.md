# Command line (hscl)

`hscl` is the HSCL1 command line tool. Every command accepts `--json` for machine-readable output.

```console
$ hscl version
$ hscl about
$ hscl status
$ hscl doctor
$ hscl system info
$ hscl security status
$ hscl security firewall status
$ hscl security audit
$ hscl ai detect
$ hscl ai setup
$ hscl ai backend list
$ hscl ai storage show
$ hscl ai server status
$ hscl appearance theme list
$ hscl appearance mode
$ hscl language status
$ hscl language list
$ hscl privacy status
$ hscl privacy session explain
$ hscl logs show
$ hscl logs collect
$ hscl recovery status
$ hscl dev status
$ hscl system info
```

| Exit code | Meaning |
|---|---|
| 0 | success |
| 1 | error |
| 3 | `hscl doctor` found at least one failing check |

Only commands that exist are documented here. Run `hscl --help` for the authoritative list.
