# Configuration de Retro Awesome

[← Retour au README](../README.md)

Ce guide détaille les connexions, l'apparence et la prise en compte des
réglages. Pour installer la session, suivre le [guide d'installation](../README.md#installation).

- [Avant la première installation](#avant-la-première-installation)
- [BBS](#bbs--section-bbs)
- [IRC](#irc--section-irc)
- [Mastodon](#mastodon--section-mastodon)
- [Apparence et widgets](#apparence-et-widgets--sections-desktop-et-theme)
- [Après l'installation](#après-linstallation)

## Avant la première installation

**Avant de lancer l'installation, modifier [config/settings.ini](../config/settings.ini)
dans le dossier du projet.** Il est possible de le préparer avant de copier
le projet sur le T430, ou directement sur le T430 :

```sh
nano config/settings.ini
```

Dans nano, enregistrer avec Ctrl+O, valider avec Entrée, puis quitter avec
Ctrl+X. Garder les cinq sections existantes et modifier leurs valeurs ; les
exemples ci-dessous remplacent uniquement la section correspondante, pas le
fichier entier. Ne pas ajouter une deuxième section du même nom. Écrire les
valeurs sans guillemets, les commentaires sur des lignes séparées commençant
par `#`, et les interrupteurs sous la forme `true` ou `false`.

Pour un premier essai, les réglages fournis suffisent. Voici les décisions à
prendre pour utiliser les connexions dès le premier démarrage :

| Élément | À préparer | Valeurs initiales |
| --- | --- | --- |
| BBS | L'hôte et le port Telnet du BBS choisi, si différent de l'exemple fourni. | `xibalba.vip`, port `44510`, UTF-8, palette verte, connexion manuelle. |
| IRC / Irssi | Le serveur de votre réseau, son port, votre pseudo et éventuellement les salons. Choisir si la connexion doit être automatique. | Laisser `host` et `channels` vides, avec `autoconnect = false`, si vous n'avez pas encore choisi de réseau. |
| Mastodon / Mastui | Vérifier l'adresse de votre instance ; choisir si Mastui s'ouvre immédiatement. | `https://mastodon.social`, `profile` vide et médias désactivés. L'autorisation du compte vient au premier lancement. |
| Bureau et couleurs | Ajuster seulement en cas de préférence de police ou de disposition. | Tous les réglages `[desktop]` et `[theme]`. |
| Ranger et htop | Aucun compte ni paramètre préalable. | Dossier personnel et statistiques réelles détectés automatiquement. |

La RAM, la résolution et le GPU ne sont pas à renseigner. **Ne mettre aucun
mot de passe, jeton Mastodon ou secret SASL dans `settings.ini`.** L'installateur
ne crée pas les comptes : leur identification se fait dans les applications.

À la première installation, ce fichier est copié vers
`~/.config/retro-awesome/settings.ini`. **Si ce fichier personnel existe déjà,
il est conservé et ses valeurs priment sur celles du modèle du projet.** Dans
ce cas, modifier directement le fichier personnel sur le T430 avant de
relancer l'installation :

```sh
nano ~/.config/retro-awesome/settings.ini
```

Ces chemins supposent les emplacements XDG habituels ; si `XDG_CONFIG_HOME`
est personnalisé, le fichier personnel se trouve dans son sous-dossier
`retro-awesome/`.

### BBS : section `[bbs]`

```ini
[bbs]
host = xibalba.vip
port = 44510
encoding = UTF-8
palette = green
autoconnect = false
```

| Paramètre | Ce qu'il faut indiquer |
| --- | --- |
| `host` | Nom du serveur ou adresse IP uniquement, sans `https://`, `telnet://`, chemin ni port ajouté. Par exemple, pour `xibalba.vip:44510`, écrire `host = xibalba.vip`. |
| `port` | Port **Telnet** donné par le BBS, séparé de l'hôte. Ici `44510`. Entier de 1 à 65535 ; ne pas utiliser son port SSH ou celui de son site web. |
| `encoding` | `UTF-8` par défaut. Choisir `CP437` si le BBS exige cet encodage pour les accents et bordures. L'installateur demandera alors `luit` et vérifiera sa disponibilité. |
| `palette` | `green` pour le thème vert ; `standard` pour conserver les distinctions habituelles des couleurs ANSI du BBS. Ce réglage est indépendant de l'encodage. |
| `autoconnect` | `false` : le panneau attend Entrée avant de se connecter. `true` : une tentative au démarrage du panneau. Dans les deux cas, une coupure attend une reconnexion manuelle. |

Le BBS demande ensuite votre identifiant et votre mot de passe dans ses propres
menus. Telnet transmet en clair : utiliser un mot de passe propre au BBS.

### IRC : section `[irc]`

**Irssi « hors ligne » signifie que son panneau est ouvert, mais qu'il n'est
connecté à aucun serveur IRC.** Votre accès Internet et les autres applications
restent disponibles. Il faut choisir un réseau IRC, le serveur de ce réseau
et un pseudo avant de discuter ; les salons sont les espaces nommés `#salon`.

Voici un exemple **fictif à adapter**. Remplacer `irc.example.net` par le vrai
serveur de votre réseau, ainsi que le pseudo et les salons :

```ini
[irc]
host = irc.example.net
port = 6697
network = Retro
nick = mon_pseudo
channels = #mon-salon #autre-salon
tls = true
autoconnect = false
```

| Paramètre | Ce qu'il faut indiquer |
| --- | --- |
| `host` | Serveur IRC communiqué par le réseau, sans `irc://`, `ircs://`, chemin ni port ajouté. Laisser vide si vous n'avez pas encore choisi de serveur. |
| `port` | Port indiqué par le réseau, de 1 à 65535. La valeur fournie est `6697`, à utiliser avec le réglage TLS correspondant du serveur. |
| `network` | Nom **local** donné à cette connexion dans Irssi. Il est possible de garder `Retro` ; ce nom ne remplace pas l'adresse du serveur. |
| `nick` | Pseudo souhaité, sans `@`. Pour ce fichier : lettres latines non accentuées, chiffres, `_` ou `-`, commençant par une lettre ou `_`, 40 caractères maximum. Le serveur peut imposer des règles supplémentaires. |
| `channels` | Salons à rejoindre lors de la connexion à ce serveur : chacun commence par `#`, séparés par des espaces, sans virgules ni guillemets. Laisser vide pour choisir les salons manuellement. |
| `tls` | `true` active TLS avec vérification du certificat. Conserver cette valeur si le réseau le prend en charge et utiliser son port TLS. `false` correspond à une connexion non chiffrée sur le port prévu par le réseau. |
| `autoconnect` | `false` : Irssi attend une connexion manuelle. `true` : il se connecte au serveur renseigné et rejoint les salons configurés dès le démarrage. Remplir `host` avant d'activer cette option. |

Pour `network`, utiliser les mêmes caractères et la même limite de longueur
que pour `nick`. Il n'est pas nécessaire de créer un compte pour remplir ces
champs ; un réseau ou salon peut toutefois exiger une identification ensuite.
Les secrets d'identification se configurent dans Irssi, pas dans ce fichier.

Avec l'exemple ci-dessus et `autoconnect = false`, une fois Irssi ouvert, taper
cette commande **dans Irssi**, pas dans un terminal shell :

```text
/connect Retro
```

Remplacer `Retro` si vous avez changé `network`. Les salons renseignés seront alors
rejoints. Si `channels` est vide, rejoindre un salon choisi avec
`/join #nom-du-salon`. Pour tout laisser à configurer plus tard, conserver
`host =`, `channels =` et `autoconnect = false` du fichier fourni.

### Mastodon : section `[mastodon]`

```ini
[mastodon]
instance = https://mastodon.social
profile =
autoconnect = true
media = off
refresh_interval = 60
```

| Paramètre | Ce qu'il faut indiquer |
| --- | --- |
| `instance` | Adresse HTTPS de votre instance, par exemple `https://mastodon.social`. Pas de `/auth/sign_in`, de chemin de profil, de pseudo ou de jeton dans l'URL. Elle préremplit l'assistant d'autorisation ; elle ne déplace pas un compte existant vers une autre instance. |
| `profile` | **Laisser vide pour un premier compte.** Mastui proposera son assistant ou reprendra son dernier profil. Pour sélectionner un profil déjà présent sur le T430, indiquer son nom exact sous `~/.config/mastui/profiles/`, sans chemin ; ce n'est pas un champ pour saisir arbitrairement un identifiant de connexion. |
| `autoconnect` | `true` ouvre Mastui au démarrage du panneau : assistant s'il manque un compte, ou reprise du profil. `false` attend Entrée avant d'ouvrir le client. L'autorisation initiale reste toujours manuelle. |
| `media` | `off` désactive les images, réglage initial conseillé pour ce bureau. `ansi` autorise leur rendu ANSI. |
| `refresh_interval` | Intervalle de rafraîchissement des fils et notifications, en secondes : entier de 10 à 3600, `60` par défaut. Sous 4 Gio détectés, l'adaptateur impose au moins 120 secondes et désactive le fil fédéré au chargement. |

Au premier lancement, Super+5 agrandit Mastui pour remplir son assistant.
« Get Auth Link » fournit le lien à ouvrir dans un navigateur pour autoriser
le compte ; le code obtenu se recopie dans Mastui. Il n'y a donc aucun mot
de passe ou jeton à préparer dans le fichier avant l'installation.

### Apparence et widgets : sections `[desktop]` et `[theme]`

Ces réglages sont facultatifs : les valeurs fournies suivent les références
visuelles du projet. Les tailles et intervalles numériques sont des entiers.

| Paramètre `[desktop]` | Valeur initiale | Rôle et valeurs admises |
| --- | --- | --- |
| `font` | `DejaVu Sans Mono` | Police monospace disponible sur le T430. La police initiale fait partie des dépendances de l'installation. |
| `font_size` | `10` | Taille en points, de 9 à 28. La taille n'est jamais réduite automatiquement pour faire entrer les panneaux. |
| `layout` | `auto` | `compact` : deux colonnes selon la maquette ; `wide` : trois colonnes ; `auto` choisit selon la surface, la police et le DPI. |
| `gap` | `4` | Espacement des panneaux en pixels, de 0 à 32. |
| `border` | `1` | Épaisseur des bordures en pixels, de 0 à 8. |
| `bar_height` | `24` | Hauteur minimale de la barre supérieure en pixels, de 18 à 64. Elle peut être augmentée automatiquement pour la police et le DPI. |
| `cpu_interval` | `2` | Actualisation des widgets CPU et RAM, en secondes, de 1 à 60. |
| `status_interval` | `10` | Actualisation des widgets réseau et batterie, en secondes, de 5 à 300. |

Chaque couleur `[theme]` s'écrit au format `#RRGGBB`, sans guillemets :

| Paramètre `[theme]` | Valeur initiale | Rôle |
| --- | --- | --- |
| `background` | `#020805` | Fond presque noir. |
| `foreground` | `#80e89a` | Texte principal vert clair. |
| `muted` | `#519565` | Vert secondaire atténué. |
| `border` | `#285b3b` | Couleur des bordures inactives ; à distinguer de l'épaisseur `border` dans `[desktop]`. |
| `active` | `#a5ffb9` | Bordure active, curseur et accents lumineux. |
| `selection` | `#80e89a` | Fond des sélections, avec texte sombre. |
| `warning` | `#e6c56e` | Avertissements et erreurs, également signalés par leur texte. |

Après avoir enregistré vos choix, poursuivre avec le diagnostic et le plan
du [guide d'installation](../README.md#installation). `plan` vérifie aussi que
les paramètres sont lisibles et respectent les valeurs acceptées ; il ne teste
pas la disponibilité des serveurs ni les identifiants de compte.

## Après l'installation

Le fichier `~/.config/retro-awesome/settings.ini` regroupe la police, les
couleurs, la disposition, les cadences et les paramètres réseau **sans secrets**.
Modifier désormais ce fichier personnel : changer uniquement le modèle du
projet ne remplace pas des préférences déjà installées.

```sh
nano ~/.config/retro-awesome/settings.ini
```

La taille de police commence à 10 points et ne peut pas être réglée sous 9
par ce fichier. `layout = compact`, `wide` ou `auto` contrôle les colonnes.
`auto` estime les cellules disponibles à partir de la surface, de la police
et du DPI. Les dimensions sont recalculées par Awesome lors des changements
XRandR. La taille réelle des cellules reste à apprécier visuellement.

Après modification, utiliser **Super+Ctrl+r** pour valider les paramètres et
recharger le bureau. Les applications déjà ouvertes restent actives ; ce
raccourci ne reconnecte pas Irssi et ne redémarre pas les terminaux.

| Réglage modifié | Quand le changement prend effet |
| --- | --- |
| Disposition, barre, bordures et widgets du bureau | Après Super+Ctrl+r. |
| Serveur, pseudo, salons ou connexion automatique IRC | Au prochain lancement du panneau Irssi. Le sélectionner avec Super+2, fermer avec Super+Maj+c, puis rouvrir avec Super+Maj+r. Cela interrompt sa connexion actuelle. |
| Hôte, port ou encodage BBS | À la prochaine tentative de connexion ; aucune connexion en cours n'est coupée par l'édition du fichier. |
| Palette ou connexion automatique BBS | Au prochain lancement du panneau BBS, avec la même procédure de fermeture/réouverture, après Super+4. |
| Options Mastui | Au prochain lancement du panneau Mastui, après Super+5 puis fermeture/réouverture. |
| Police et couleurs des terminaux | Au prochain lancement de chaque panneau concerné. Le rechargement du bureau conserve les terminaux existants. |

Super+Maj+r rouvre les outils fermés et conserve ceux qui sont encore ouverts.
La police peut aussi être ajustée temporairement dans xterm avec Ctrl+clic droit.

- **Mastui** : Super+5 agrandit l'assistant natif. L'instance est préremplie avec
  `https://mastodon.social`. « Get Auth Link » fournit un lien d'autorisation à
  ouvrir ponctuellement dans le navigateur ; recopier le code dans Mastui.
  Aucun mot de passe n'est demandé par l'installateur. Les prochains lancements
  reprennent le dernier profil ; `profile` peut désigner un profil existant.
  Le thème natif `retro-green-builtin`, adapté à la palette commune, et les
  médias désactivés sont appliqués par l'adaptateur de cette version.
  `media = ansi` autorise les images légères.
  Les actions de publication restent manuelles. Sans réseau, l'écran peut
  demander une nouvelle autorisation : attendre le retour du réseau avant de
  réessayer ; aucun redémarrage automatique en boucle.
- **BBS** : le premier panneau propose Entrée pour joindre `xibalba.vip:44510`.
  Modifier `host`, `port`, `encoding`, `palette` et `autoconnect` si nécessaire.
  `palette = standard` rétablit les couleurs ANSI habituelles. CP437 emploie
  `luit` et nécessite une réinstallation pour ajouter ce paquet s'il manque.
  La disponibilité de luit est vérifiée dans les dépôts configurés. Après une
  coupure, Entrée réessaie, `q` ferme. Aucune frappe n'est rejouée.
- **Irssi** : le panneau indique comment choisir pseudo, serveur et salons.
  Dans `[irc]`, renseigner `host`, `nick`, `network`, `channels` (séparés par espaces) et
  activer `autoconnect` pour une connexion au démarrage. TLS vérifié est activé
  par défaut. Le profil séparé se trouve dans `~/.config/retro-awesome/irssi`.
  Les secrets SASL éventuels se configurent dans Irssi, jamais dans les arguments
  d'un lanceur ou dans `settings.ini`.
- **Ranger** : démarre dans le véritable dossier personnel. Suppression avec
  confirmation, souris active, prévisualisation d'images désactivée.
- **htop** : affiche les processus et ressources réels ; le mode monochrome
  prend les couleurs du terminal. Les réglages natifs sont conservés.

Sous 4 Gio détectés, l'adaptateur Mastui espace davantage les rafraîchissements
et désactive son fil fédéré au chargement. Les cinq outils restent présents.

