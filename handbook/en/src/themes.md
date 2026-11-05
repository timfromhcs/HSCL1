# Themes

HSCL1 ships four themes: **hcs-midnight** (default), **hcs-light**, **hcs-nord** and **hcs-aurora**.

```console
$ hscl appearance theme list
$ hscl appearance theme show hcs-nord
$ hscl appearance theme set hcs-nord --dry-run
$ hscl appearance theme set hcs-nord
$ hscl appearance theme restore
```

`set` first writes a backup of the previous selection to `~/.config/hscl/appearance-backup/`, then applies the Plasma colour scheme and wallpaper. `--dry-run` only prints the plan.
