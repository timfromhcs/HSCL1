# Thèmes

HSCL1 propose quatre thèmes : **hcs-midnight** (par défaut), **hcs-light**, **hcs-nord** et **hcs-aurora**.

```console
$ hscl appearance theme list
$ hscl appearance theme show hcs-nord
$ hscl appearance theme set hcs-nord --dry-run
$ hscl appearance theme set hcs-nord
$ hscl appearance theme restore
```

`set` enregistre d'abord la sélection précédente dans `~/.config/hscl/appearance-backup/`, puis applique le jeu de couleurs Plasma et le fond d'écran. `--dry-run` affiche seulement le plan.
