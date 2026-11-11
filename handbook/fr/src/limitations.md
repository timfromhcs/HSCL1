# Limitations connues

- Pré-alpha : rien n'a été testé sur du matériel physique. Tout ce qui suit a été mesuré dans des machines
  virtuelles (UEFI, QEMU/KVM ou WHPX).
- Les artefacts de version ne sont **pas signés** ; seules des sommes SHA-256 sont publiées.
- Secure Boot n'a pas été vérifié pour les images HSCL1.
- L'installateur s'arrête parfois 2 à 3 s après son démarrage (environ un démarrage sur six à douze) puis il est
  relancé par `/usr/bin/hscl-calamares`. Sur les images sans ce lanceur, relancez-le : la tentative suivante
  réussit en général.
- `hscl` (version, statut, doctor, thèmes, fonds d'écran, statut de confidentialité, commandes lab, détection IA)
  et le Control Center (Vue d'ensemble, Apparence, Sécurité, Mineur, À propos) sont implémentés. Le Security Lab
  et le mode Confidentialité sont des **flux en ligne de commande**, pas des modes de bureau distincts.
- Le Security Lab exécute les outils dans des conteneurs Podman sans privilèges. Les outils graphiques, le
  passage du Wi-Fi/USB et les profils de VM jetables ne sont pas fournis.
- Le mode Confidentialité n'est **pas Tails** : il n'y a ni coupure réseau vérifiée ni stockage persistant
  chiffré.
- Le Welcome Center n'affiche que la page HSCL1 lorsqu'il est ouvert depuis le menu ; le comportement au premier
  démarrage d'un système installé n'a pas été vérifié.
- Pour une icône de bureau dont le nom tient sur deux lignes, la seconde ligne se cale à gauche du centre.
- L'allemand et le français suivent la structure anglaise chapitre par chapitre.
