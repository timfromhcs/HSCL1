# Dépannage

| Problème | À essayer |
|---|---|
| Écran noir dans une VM | Utiliser le VGA standard et désactiver l'accélération 3D. |
| Démarrage très lent | Activer l'accélération matérielle (KVM ou WHPX) ; l'émulation logicielle demande plusieurs minutes. |
| L'installateur indique « aucune partition » | Aucun disque n'est attaché à la machine virtuelle. Attachez un disque virtuel jetable. |
| `hscl doctor` signale AppArmor désactivé | Normal sous WSL ou avec des noyaux sans AppArmor ; sur une vraie installation HSCL1 il doit être actif. |
