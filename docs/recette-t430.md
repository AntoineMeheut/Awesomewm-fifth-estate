# Recette sur le ThinkPad T430

Ne cocher un point qu'après observation réelle. Utiliser des comptes et
contenus autorisés ; aucune publication, inscription ou réponse automatique.

## Avant l'installation

1. Ouvrir la session habituelle, conserver une copie du dépôt et noter la
   version avec `awesome --version`.
2. Exécuter `./install.sh diagnose --json`. Vérifier distribution, architecture,
   RAM, CPU, GPU, écrans, disques, NetworkManager, batterie et luminosité.
   Si lancé depuis une console, refaire le diagnostic depuis X11.
3. Exécuter `./install.sh plan`. Confirmer qu'Awesome existant est détecté et
   n'apparaît pas dans les paquets à ajouter.
4. Lancer `./install.sh install`, puis `./install.sh verify`.
   Noter les versions dans `~/.local/state/retro-awesome/versions.json`.

## Session et applications

- [ ] La session habituelle Awesome et Xfce restent sélectionnables.
- [ ] Retro Awesome ouvre exactement cinq panneaux applicatifs.
- [ ] La disposition compacte correspond à la maquette : Mastui/BBS à gauche,
  Irssi/ranger/htop à droite, sans minuscule police imposée.
- [ ] Super+1…6 fonctionnent sur AZERTY sans Majuscule ; souris et TrackPoint
  activent bureaux, fenêtres, sélection et menus.
- [ ] Super+m puis Super+1 restaure la disposition. Chaque vue dédiée réutilise
  la fenêtre, avec assez de place pour les formulaires Mastui et le BBS.
- [ ] Ranger navigue dans les vrais fichiers ; une suppression d'un **fichier
  temporaire créé pour ce test** exige confirmation. htop affiche les vrais PID.
- [ ] Mastui autorise un compte de test via son assistant natif, emploie le
  thème vert, reprend le profil et laisse les médias désactivés par défaut.
- [ ] Le BBS attend Entrée, puis négocie Telnet. Tester touches, menus, taille
  du terminal, accents et bordures en UTF-8, puis CP437 si nécessaire. Tester
  aussi la palette standard si le serveur emploie des couleurs peu lisibles.
- [ ] Irssi reste hors ligne sans configuration, puis rejoint exclusivement
  le réseau/salons explicitement choisis. Vérifier TLS et le certificat.
- [ ] Fermer un outil et utiliser Super+Maj+r : un seul exemplaire est rouvert.
- [ ] Recharger cinq fois avec Super+Ctrl+r, y compris dès l'ouverture : aucun
  doublon et aucune reconnexion des outils encore ouverts.
- [ ] Terminal libre en vue 7, dialogues accessibles, déplacement d'une fenêtre
  entre écrans/vues sans fermeture du processus.

## Incidents et portable

- [ ] Ouvrir sans réseau : le bureau, ranger et htop restent utilisables.
- [ ] Couper le réseau en cours d'utilisation. Le BBS reste ouvert après
  déconnexion et attend une reconnexion manuelle. Mastui ne boucle pas.
- [ ] Tester un hôte BBS inexistant et un jeton Mastodon révoqué dans un profil
  de test ; aucune donnée sensible n'apparaît dans le manifeste/diagnostic.
- [ ] Verrouiller avec Super+l. Vérifier que le mot de passe déverrouille et
  que les applications restent ouvertes. Ne pas lancer les essais de veille
  tant que ce verrouillage simple n'est pas opérationnel.
- [ ] Mettre en veille avec le menu d'énergie, puis par le couvercle. L'écran
  est verrouillé avant suspension ; au réveil, clavier, affichage et réseau
  reviennent, sans double verrouillage ni double veille.
- [ ] Tester les touches de volume, micro, luminosité et l'alimentation secteur.
  Vérifier les états sans batterie / sans interface Wi-Fi si applicable.
- [ ] Changer la résolution avec Super+p. Si un écran externe est disponible,
  le brancher/débrancher : aucun outil perdu ou dupliqué.
- [ ] Sur configuration 4 Gio, attendre la stabilisation puis relever `free -h`
  et les processus dans htop. Comparer à l'objectif < 2 Gio sans médias ;
  documenter les coûts réels si dépassé.

## Captures réelles et comparaison

Créer un dossier de captures privé :

```sh
mkdir -p artifacts/recette
chmod 700 artifacts/recette
scrot --delay 5 artifacts/recette/vue-ensemble.png
```

Pendant les cinq secondes, presser Super+1 et laisser les cinq panneaux
visibles. Pour la seconde capture, lancer depuis un terminal :

```sh
scrot --delay 5 artifacts/recette/mastui-agrandi.png
```

Pendant le délai, presser Super+5. Masquer ou recadrer les informations de
compte, messages privés et autres données sensibles **avant de partager**.
Garder une trace de la résolution via `xrandr --current` et des réglages de
police, marges et couleurs utilisés.

Comparer les deux captures aux photographies pour les noirs, verts, contrastes,
monospace, bordures, marges et barre. Comparer la vue d'ensemble à la maquette
pour la présence et l'emplacement des cinq outils. Noter les différences de
menus natifs, proportions liées à la résolution et limitations de colonnes.
Corriger les réglages utiles puis renouveler les captures.

## Cycle de vie

- [ ] Modifier la police et un paramètre BBS ; relancer `install` : les valeurs
  sont conservées. Les comptes et réglages natifs restent utilisables.
- [ ] Sur une VM Mint de test, provoquer un échec de dépendance et un échec
  d'activation de fichier. Vérifier l'absence d'entrée de session partielle,
  le journal, les sauvegardes et `recover` après interruption.
- [ ] Revenir à la session habituelle, exécuter `uninstall`. Vérifier retrait de
  la seule entrée Retro, restauration des originaux et conservation des profils,
  paquets et configurations Awesome/Xfce préexistants.

Reporter les résultats, les deux captures et les écarts observés dans
`docs/qualification.md`. Aucun test local sur macOS ne remplace cette recette.
