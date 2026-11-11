# Dépannage

| Problème | Que faire |
|---|---|
| Écran noir dans une VM | Utiliser le VGA standard et désactiver l'accélération 3D. |
| Démarrage très lent | Activer l'accélération matérielle (KVM ou WHPX) ; l'émulation logicielle prend plusieurs minutes. |
| L'installateur affiche « no partitions » | La machine virtuelle n'a pas de disque. Attacher un disque virtuel jetable. |
| L'installateur s'arrête sur `hscl-verify-esp: … did not populate the EFI system partition` | Le système a été écrit mais aucun chargeur EFI n'a été déposé sur la partition EFI : la machine ne démarrerait pas. Rien n'est perdu : relancez l'installation et, si cela se reproduit, signalez le message exact de `/var/log/calamares.log`. |
| La fenêtre de l'installateur disparaît juste après le démarrage | Défaut intermittent connu (environ un démarrage sur six à douze). Sur les images actuelles, le lanceur la redémarre seul ; sur les anciennes, relancez-la. |
| Après la connexion, un « Welcome Center » avec des pages KDE apparaît | Uniquement sur les anciennes images. Les images actuelles ouvrent le Welcome Center sur la page HSCL1, et il ne s'ouvre pas du tout à la première connexion. |
| `hscl doctor` signale AppArmor désactivé | Normal dans WSL ou sur un noyau sans AppArmor ; sur une installation HSCL1 réelle, il doit être actif. |
