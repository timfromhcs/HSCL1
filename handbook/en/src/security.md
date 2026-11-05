# Security status

```console
$ hscl security status
$ hscl doctor
```

These commands report what is actually enabled on your system: firewall, AppArmor, Secure Boot, disk encryption and APT source hygiene. `hscl doctor` exits with code 3 if a check fails. Reports hide user names, host names and network identifiers.

HSCL1 does not claim a system is "secure"; it shows evidence so you can decide.
