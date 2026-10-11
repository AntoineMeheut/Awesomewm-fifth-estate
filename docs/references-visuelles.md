# Analyse des références — 11 octobre 2026

Les trois images originales ont été ouvertes et examinées avant l'écriture du
thème et du moteur de disposition.

| Fichier examiné | Observations et conséquences |
| --- | --- |
| `references/roYWIJ1.jpeg` | Fond noir, vert assez saturé, texte secondaire nettement atténué, monospace dense. Bordures rectilignes très fines, marges minimales, barre supérieure sur une seule ligne. Les trois colonnes inspirent le profil large ; les reflets jaunes et le flou sont exclus. |
| `references/u39fKGw.jpeg` | Vert plus froid, contraste variable dans la photographie, grands panneaux empilés à gauche et supervision à droite. Sélections en aplat vert. Le thème garde une distinction claire entre sélection et texte ; il ne reproduit pas l'assombrissement photographique. |
| `references/maquette-bureau.png` | Deux colonnes asymétriques : Mastui au-dessus du BBS à gauche ; Irssi, ranger et htop à droite. Vert clair lisible, petits intervalles et bordure active lumineuse. Cette composition définit le profil compact par défaut. Les menus et contenus fictifs ne sont pas reproduits. |

Paramètres initiaux : fond `#020805`, texte `#80e89a`, secondaire `#519565`,
sélection `#80e89a` sur texte sombre, bordure inactive `#285b3b`, active
`#a5ffb9`. Bordures de 1 pixel, intervalles de 4 pixels, DejaVu Sans Mono
10 points (minimum accepté : 9). Une teinte ambre est réservée aux erreurs
et avertissements, également identifiés par du texte.

La barre reste en haut ; aucun panneau inférieur supplémentaire, effet CRT,
compositeur, image de fond ou dépendance d'exécution aux références.
La vue compacte alloue environ 58 % de la largeur à la colonne gauche et
62 % de sa hauteur à Mastui. La vue large ne s'active automatiquement que si
les dimensions estimées des cellules laissent assez de colonnes et de lignes.
Les vues dédiées emploient les mêmes fenêtres et connexions.

Ces choix sont une analyse de conception. La comparaison avec des captures
réelles sous Awesome sur le T430 reste une étape de recette distincte.
