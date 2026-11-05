# Mises à jour

HSCL1 reçoit ses mises à jour via APT depuis les archives d'Ubuntu 26.04 LTS (`resolute`). Rien n'est envoyé à un serveur HSCL1.

## Rechercher des mises à jour

```console
$ hscl system updates --check
```

Il s'agit d'une simulation : la commande indique ce qui pourrait être mis à jour, combien de paquets proviennent du canal de sécurité et si un redémarrage est nécessaire. Rien n'est installé. Si apt lui-même est défaillant, la commande signale une erreur au lieu d'afficher « 0 mise à jour ».

## Système installé

- Les **mises à jour de sécurité** sont installées automatiquement (mises à jour automatiques, canal de sécurité uniquement).
- Les autres mises à jour sont installées par vous, par exemple dans Discover ou avec `sudo apt update && sudo apt upgrade`.
- HSCL1 ne redémarre jamais l'ordinateur de lui-même. Quand un redémarrage est nécessaire, `hscl system updates --check` l'indique.

## Session live

L'ISO live est en lecture seule. Les modifications, y compris les mises à jour installées, sont perdues à l'arrêt. Pour des paquets plus récents de façon durable, installez HSCL1 ou utilisez une image plus récente.

## Image préinstallée

L'image disque préinstallée se met à jour comme un système installé. Une image plus récente n'est utile que pour repartir de zéro.
