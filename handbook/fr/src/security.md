# État de sécurité

```console
$ hscl security status
$ hscl doctor
```

Ces commandes indiquent ce qui est réellement activé sur votre système : pare-feu, AppArmor, Secure Boot, chiffrement du disque et état des sources APT. `hscl doctor` se termine avec le code 3 si une vérification échoue. Les rapports masquent les noms d'utilisateur, les noms d'hôte et les identifiants réseau.

HSCL1 ne prétend pas qu'un système est « sûr » ; il montre des preuves pour que vous puissiez décider.
