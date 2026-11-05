# Command line (hscl)

`hscl` is the HSCL1 command line tool. Every command accepts `--json` for machine-readable output.

```console
$ hscl version
$ hscl about
$ hscl status
$ hscl doctor
$ hscl system info
$ hscl security status
$ hscl ai detect
$ hscl appearance theme list
```

| Exit code | Meaning |
|---|---|
| 0 | success |
| 1 | error |
| 3 | `hscl doctor` found at least one failing check |

Only commands that exist are documented here. Run `hscl --help` for the authoritative list.
