# Ligne de commande (hscl)

`hscl` est l'outil en ligne de commande de HSCL1. Chaque commande accepte `--json` pour une sortie lisible par machine.

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
```

| Code de sortie | Signification |
|---|---|
| 0 | succès |
| 1 | erreur |
| 3 | `hscl doctor` a trouvé au moins une vérification en échec |

Seules les commandes qui existent sont documentées ici. `hscl --help` donne la liste de référence.
