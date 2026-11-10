# Prise en main

## Essayer dans une machine virtuelle

Utilisez QEMU avec un micrologiciel UEFI (OVMF/edk2) ou le BIOS classique. Réglages testés (pré-alpha) :

| Réglage | Valeur |
|---|---|
| Mémoire | 4 Go |
| Processeurs | 4 |
| Graphique | VGA standard, sans 3D |
| Réseau | mode utilisateur (NAT) |

Le bureau live apparaît après environ deux minutes sur un hôte accéléré. Choisissez **Try or Install HSCL1** dans le menu de démarrage.

## Installation

L'installateur est **HSCL1 Installer**, un Calamares personnalisé. Il lui faut un disque que vous acceptez d'effacer :
**utilisez un disque virtuel jetable.**

- **Installation non chiffrée :** vérifiée avec **4 Go** de mémoire (ESP + racine ext4, se termine par « All done »).
- **Installation chiffrée LUKS2 :** donnez **8 Go** à la VM. Une tentative à 6 Go a paniqué une fois ; la valeur
  documentée est 8 Go.
- La partition système est chiffrée en LUKS2 et la phrase secrète est demandée à chaque démarrage. La partition EFI
  et un `/boot` séparé restent lisibles sans elle. Il y a **une** phrase secrète et **aucune clé de récupération** :
  si vous l'oubliez, les données sont irrécupérables.

L'installateur écrit sur le disque sélectionné. Aucun double démarrage vérifié n'est proposé, et rien n'a été testé
sur du matériel physique.
