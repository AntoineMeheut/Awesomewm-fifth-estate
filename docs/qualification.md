# Qualification — 11 octobre 2026

## État de la livraison

Implémentation initiale issue des deux spécifications du dépôt. La précision
ultérieure de l'utilisateur est intégrée : Awesome est déjà installé sur le
T430. L'installateur détecte le paquet ou le binaire existant et le réutilise,
sans demander son installation ou sa mise à niveau si celui-ci est présent.
Une version incompatible est signalée avant les modifications.

Le développement a lieu sur macOS arm64. Aucun accès au T430, serveur X11
Linux ou moteur Docker actif n'était disponible. **Il ne s'agit pas d'une
qualification graphique ou matérielle réussie.** Aucun compte, salon IRC ou
BBS n'a été contacté par l'application pendant les essais locaux.

## Références examinées

Les images `references/roYWIJ1.jpeg`, `references/u39fKGw.jpeg` et
`references/maquette-bureau.png` ont toutes été ouvertes visuellement. Leur
[analyse préalable](references-visuelles.md) décrit les choix de couleur,
police, bordures, barre supérieure et composition. Le bureau ne charge aucune
de ces images pendant son exécution.

## Sources et choix de versions

- Le [site Linux Mint](https://linuxmint.com/download.php), consulté au début du
  développement, affiche 22.3 Zena et l'édition Xfce. Le contrôle système
  exige Linux Mint 22.3, `UBUNTU_CODENAME=noble` et x86_64 ; une autre version
  devra être qualifiée explicitement.
- La [distribution PyPI Mastui](https://pypi.org/project/mastui/) annonce
  1.14.2, Python ≥ 3.9 et < 4. L'archive source 1.14.2 a été téléchargée et son
  SHA-256 vérifié :
  `1df50fb41bbfa5c8f07028aa94b5f2881b4732b2d6a62d5846f110fdeb38a8d1`.
  Le code `profile_manager.py`, `config.py`, `app.py`, `login.py` et `retro.py`
  de cette archive a été inspecté. Les profils réels sont sous
  `~/.config/mastui/profiles/<profil>/`, avec `.env` et `last_profile.txt` au
  niveau prévu par cette version. Les clés natives incluent `THEME`,
  `IMAGE_SUPPORT`, `IMAGE_RENDERER` et les intervalles de rafraîchissement.
  Le nom exact du thème est `retro-green-builtin` ; son texte gris et ses fonds
  sont adaptés aux couleurs communes du projet via les propriétés du thème
  Textual. L'assistant emploie un lien
  OAuth puis un code d'autorisation. Ce parcours a été vérifié dans le code,
  **pas avec un compte authentifié**.
- L'adaptateur utilise les classes de cette version pour appliquer les
  préférences sans modifier son installation. Il refuse une autre version.
  Les dépendances transitives sont résolues par pipx au moment de
  l'installation et leurs versions sont consignées ; elles ne constituent pas encore un verrouillage complet
  qualifié sur Mint.
- Les API ont été confrontées aux sources
  [Awesome 4.3, tags](https://github.com/awesomeWM/awesome/blob/v4.3/lib/awful/tag.lua)
  et [disposition](https://github.com/awesomeWM/awesome/blob/v4.3/lib/awful/layout/init.lua) :
  géométries par client, layouts par bureau et retrait des bordures par Awesome.
  Le thème vise l'API stable 4.x ; seule la validation en session confirmera
  son intégration complète.
- Les sources [Irssi 1.4.5](https://github.com/irssi/irssi/tree/1.4.5) confirment
  `--noconnect`, le chargement des scripts Perl `scripts/autorun`, `-tls` et
  `-tls_verify`. Les choix utilisateur alimentent un script de démarrage
  distinct du profil existant de l'utilisateur.
- Le [code GNU Inetutils Telnet](https://github.com/guillemj/inetutils/blob/master/telnet/commands.c)
  confirme le préfixe négatif du port pour lancer la négociation Telnet sur un
  port inhabituel. Le lanceur fournit `--` avant l'hôte pour préserver cet
  argument. Le flux est confié au client Telnet, sans filtrage de ses octets.
- La disponibilité exacte des paquets est contrôlée avec `apt-cache policy`
  sur la machine cible. Les versions effectivement installées sont inscrites
  dans `versions.json`. Aucun paquet système n'a été installé sur le Mac.

## Vérifications locales

`make test` a réussi : **31 tests Python** et **120 cas de géométrie Lua**.
Il vérifie les syntaxes Python, shell et Lua, puis les comportements
suivants dans des répertoires temporaires :

- configuration stricte, minimum 9 points, origine HTTPS, noms de profils et
  paramètres réseau ; génération Lua avec chemins contenant espaces et guillemets ;
- conservation d'Awesome existant, de ses fichiers et des profils applicatifs ;
- installation répétée, sauvegarde des originaux et de leurs permissions,
  conservation des préférences, sauvegarde des changements locaux ;
- récupération après erreur de disque simulée ou journal de transaction interrompu ;
- retrait avec préférences invalides, restauration d'un original supprimé,
  rejet d'un lien symbolique à la place d'un fichier géré ;
- verrou empêchant deux lancements simultanés d'un outil ;
- premier BBS sans connexion implicite, reconnexion exclusivement manuelle,
  séparation de l'encodage et de la palette ;
- Irssi hors ligne par défaut et configuration TLS explicite ;
- lecture réelle de la mémoire ou valeur inconnue si elle manque ;
- **120 combinaisons** de disposition : 1024×768, 1366×768, 1600×900,
  1920×1080, 2560×1440 ; polices 9/10/12/16 ; DPI 96/144 ; compact/large/auto.
  Les rectangles ont une surface positive et ne se recouvrent ni ne dépassent
  la zone disponible, y compris avec un écran décalé horizontalement.

`python3 tests/check_mastui_source.py /tmp/retro-mastui.tar.gz` a également
réussi : contrôle de l'archive officielle et des signatures, propriétés,
chemins de profils, thème et assistant utilisés par l'adaptateur, sans
exécuter l'application ni lire un compte.

Les tests de processus utilisent des doublures locales et ne valent pas
essais graphiques, APT ou protocolaires. Le Lua disponible sur le Mac est
5.5.1 ; le code reste dans le sous-ensemble utilisé par Lua 5.2/5.3 avec
Awesome 4.3, à vérifier par `awesome -k` sur la cible.

## Écarts et recette restante

| Point | État / justification |
| --- | --- |
| Entrée de session | `retro-awesome-<uid>.desktop`, au lieu du nom global unique proposé : évite la collision entre utilisateurs. Le lanceur système refuse un autre UID. |
| Assistant Mastui | Lancé au premier démarrage du panneau, dans la session réelle, pour rester utilisable aussi après une installation depuis une console. |
| Profil large | Mastui et BBS en colonnes séparées, trois autres outils empilés à droite ; le profil compact suit la maquette. |
| APT et dépendances | Détection et garde-fous codés ; installation réelle, réinstallation et retrait sous Mint à tester. |
| Visuel RF03 / RF15 | Analyse des références faite, mais aucune capture réelle disponible. Procédure de capture livrée, aucune image simulée présentée comme preuve. |
| Réseau RF05–RF07 / RF09 | Parcours et gestion d'échec codés ; OAuth, BBS, encodages, TLS IRC et perte réseau à tester sur la cible avec comptes autorisés. |
| Sessions RF02 / RF04 / RF10 | Géométrie et verrous testés localement ; apparition des cinq fenêtres, changements de vue et absence de doublons à confirmer sous X11. |
| Matériel RF01 / RF11 | RAM, affichage, pilotes, batterie, TrackPoint, AZERTY, luminosité, volume et veille à vérifier sur le T430. |
| Mémoire | Aucun résultat mesuré pour la cible 4 Gio ou l'objectif < 2 Gio utilisés. |
| Luit / CP437 | Conversion implémentée et paquet vérifié si sélectionné ; affichage réel et disponibilité du paquet à qualifier avant usage. |

La [recette T430](recette-t430.md) indique comment terminer ces étapes et
produire les deux captures demandées.
