# WebApp — Airbnb NYC Dashboard (Redis)

## À quoi sert cette application ?

C'est le livrable "démo" du projet : une interface web qui permet d'explorer les ~102 000
annonces Airbnb de New York stockées dans Redis, sans écrire une seule requête. Elle sert deux
publics :

- **Le manager / le prof** : voir en un coup d'œil les résultats de l'analyse (rapport
  analytique demandé dans le sujet), sans ouvrir le notebook.
- **Un utilisateur final** : filtrer les annonces comme sur un vrai site (quartier, type de
  logement, budget) et visualiser leur répartition sur une carte.

Techniquement, elle démontre que la base **Redis** répond en temps réel à des requêtes de
filtrage et d'agrégation sur un volume de ~100k documents — l'objectif du projet n'est pas
seulement de stocker les données, mais de prouver qu'on peut les interroger efficacement.

## Fonctionnalités

### 1. Filtres interactifs (barre latérale)

- **Borough** (Manhattan, Brooklyn, Queens, Bronx, Staten Island)
- **Type de logement** (logement entier, chambre privée, chambre partagée, chambre d'hôtel)
- **Fourchette de prix** (curseur $0–$1200)

Chaque changement de filtre déclenche une requête `FT.SEARCH` sur l'index RediSearch
(`idx:listings`) — pas de scan ni de filtrage côté Python : le filtrage est fait par Redis.

### 2. Carte + tableau des résultats

Les annonces correspondant aux filtres sont affichées sur une carte (position `lat`/`long`) et
dans un tableau (nom, quartier, prix). Le nombre total de résultats trouvés est affiché, même si
seuls les 500 premiers sont chargés à l'écran (pour rester réactif).

### 3. Rapport analytique (4 onglets)

Reprend les questions métier traitées dans le notebook, mais interactif et toujours à jour car
calculé en direct sur la base :

| Onglet | Question métier |
|---|---|
| Prix par borough | Quel est le prix moyen des annonces par borough ? |
| Prix par type de logement | Le prix moyen dépend-il du type de logement, et est-ce pareil partout ? |
| Top quartiers | Quels quartiers ont le plus d'annonces, et à quel prix ? |
| Top hôtes | Quels hôtes ont le plus d'annonces au total ? |

Toutes ces requêtes sont exécutées via `FT.AGGREGATE` (module RediSearch) — voir
`scripts/queries.py`, le même code que celui utilisé et expliqué dans le notebook.

## Lancer l'application

Prérequis : Redis (Docker `docker compose up -d`) démarré et données chargées
(`py scripts/load_data.py`).

```bash
streamlit run webapp/app.py
```

L'application s'ouvre sur http://localhost:8501.

## Déploiement (Streamlit Community Cloud)

1. Pousser le repo sur GitHub.
2. Sur [share.streamlit.io](https://share.streamlit.io), créer une app pointant vers
   `webapp/app.py`.
3. Renseigner `REDIS_HOST`, `REDIS_PORT`, `REDIS_PASSWORD` dans les *Secrets* de l'app — la base
   Redis Cloud du projet est déjà prête (voir README principal, section "Mise en production").

## Limites connues

- La base Redis Cloud (offre gratuite) contient un **échantillon de 11 000 annonces** et non les
  101 760 complètes, faute de mémoire disponible — voir README principal pour le détail.
- La carte (`st.map`) affiche au plus 500 points pour rester réactive ; le compteur de résultats,
  lui, reflète le total réel.
- Pas d'authentification : en l'état, l'app est en lecture seule sur les données (aucune
  opération d'écriture n'est exposée côté interface), donc pas de risque de modification
  accidentelle des données par un visiteur.
