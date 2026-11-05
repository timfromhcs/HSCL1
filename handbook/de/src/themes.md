# Designs

HSCL1 enthält vier Designs: **hcs-midnight** (Standard), **hcs-light**, **hcs-nord** und **hcs-aurora**.

```console
$ hscl appearance theme list
$ hscl appearance theme show hcs-nord
$ hscl appearance theme set hcs-nord --dry-run
$ hscl appearance theme set hcs-nord
$ hscl appearance theme restore
```

`set` sichert zuerst die bisherige Auswahl unter `~/.config/hscl/appearance-backup/` und wendet dann Plasma-Farbschema und Hintergrundbild an. `--dry-run` zeigt nur den Plan.
