<img src="banner.svg" alt="Centres d'entretien auto en France" width="100%">

# Centres d'entretien auto en France

Carte web de tous les centres d'entretien automobile des grandes enseignes en France, outre-mer compris, avec une fiche pour chaque centre.

**[Ouvrir l'application](https://ninjathune-human.github.io/centres-auto-france/)**

## Enseignes couvertes

Norauto, Feu Vert, Speedy, Midas, Point S, Euromaster, Vulco, Profil Plus, Roady, Carter-Cash, Eurorepar, Motrio, Top Garage.

## Fonctionnalités

- Un point coloré par centre, couleur par enseigne, sur fond de carte Esri clair ou sombre selon le réglage du système.
- Fiche au clic : adresse, téléphone, site, e-mail, horaires traduits en français, SIRET, lien d'itinéraire.
- Filtre par enseigne : un clic isole une enseigne, les clics suivants en ajoutent. Sans sélection, tout est affiché.
- Recherche par nom, ville ou code postal, tolérante aux fautes de frappe et à l'ordre des mots.
- Interface adaptée au PC, à l'iPad et à l'iPhone, au tactile comme au stylet.

## Données

Les centres proviennent d'[OpenStreetMap](https://www.openstreetmap.org), interrogé en direct via l'API Overpass au premier chargement. Le résultat est ensuite conservé 7 jours dans le navigateur.

La couverture dépend des contributeurs OpenStreetMap. Les grandes enseignes y sont bien recensées, mais certaines fiches n'ont ni téléphone ni horaires.

Données © contributeurs OpenStreetMap, sous licence [ODbL](https://opendatacommons.org/licenses/odbl/). Fond de carte © Esri.

## Déploiement

L'application tient en un seul fichier, `index.html`, sans installation ni dépendance locale.

1. Déposer `index.html`, `README.md` et `banner.svg` à la racine du dépôt.
2. Dans *Settings > Pages*, choisir la branche `main` et le dossier `/ (root)`.
3. L'application est en ligne à l'adresse `https://ninjathune-human.github.io/centres-auto-france/`.

Pour l'aperçu sur les réseaux sociaux, importer `banner.png` dans *Settings > General > Social preview*.

## Technique

[Leaflet](https://leafletjs.com) 1.9.4 avec rendu Canvas, tuiles Esri World Gray Canvas, API [Overpass](https://overpass-api.de). HTML, CSS et JavaScript natifs, en un seul fichier.
