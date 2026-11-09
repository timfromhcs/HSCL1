# Kommandozeile (hscl)

`hscl` ist das HSCL1-Kommandozeilenwerkzeug. Jeder Befehl akzeptiert `--json` für maschinenlesbare Ausgabe.

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
$ hscl appearance theme list
$ hscl language status
$ hscl language list
$ hscl privacy status
$ hscl privacy session explain
$ hscl logs show
$ hscl logs collect
$ hscl recovery status
```

| Exit-Code | Bedeutung |
|---|---|
| 0 | Erfolg |
| 1 | Fehler |
| 3 | `hscl doctor` hat mindestens eine fehlgeschlagene Prüfung gefunden |

Hier stehen nur Befehle, die es wirklich gibt. `hscl --help` zeigt die maßgebliche Liste.
