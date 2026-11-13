# Limitations connues

- Pré-alpha : rien n'a été testé sur du matériel physique. Tout ce qui suit a été mesuré dans des machines
  virtuelles (UEFI, QEMU/KVM ou WHPX).
- Les artefacts de version ne sont **pas signés** ; seules des sommes SHA-256 sont publiées.
- Secure Boot est lu dans l'invité (`mokutil --sb-state`, `hscl doctor`), mais un démarrage positif en Secure Boot
  n'a pas été démontré : cet hôte ne peut pas entrer en SMM sous WHPX ni sous WSL/KVM. Aucune affirmation sur
  Secure Boot n'est faite.
- Le plantage au démarrage de l'installateur (un segfault dans la page de notes pendant que l'arbre de progression
  la dessinait) est corrigé depuis la 0.1.8. `/usr/bin/hscl-calamares` relance encore par précaution un assistant
  qui meurt dans sa première minute.
- `hscl` (version, statut, doctor, thèmes, fonds d'écran, statut de confidentialité, commandes lab, détection IA)
  et le Control Center (**onze pages en lecture seule** : Vue d'ensemble, Apparence, Sécurité, Confidentialité,
  Laboratoire de sécurité, IA locale, Mises à jour et récupération, Développement, Langue et région, Mineur,
  À propos) sont implémentés. Appliquer un thème est la seule action du panneau ; tout ce qui modifie le système
  reste en ligne de commande. Le Security Lab et le flux Confidentialité restent des **flux en ligne de commande**,
  pas des modes de bureau distincts.
- Le Security Lab exécute les outils dans des conteneurs Podman sans privilèges. Les outils graphiques, le
  passage du Wi-Fi/USB et les profils de VM jetables ne sont pas fournis.
- Le mode Confidentialité n'est **pas Tails** : il n'y a ni coupure réseau vérifiée ni stockage persistant
  chiffré.
- Le Welcome Center ouvre la page HSCL1 lorsqu'il est lancé depuis le menu ; une installation fraîche se connecte
  au bureau HSCL1 nu, car le fichier d'état est prérempli pour que la visite KDE n'apparaisse pas.
- Pour une icône de bureau dont le nom tient sur deux lignes, les lignes sont centrées sous l'icône (mesuré à 1 px
  près) ; la note antérieure sur une seconde ligne décalée à gauche venait de l'image affichée, pas d'une mesure.
- L'allemand et le français suivent la structure anglaise chapitre par chapitre.
