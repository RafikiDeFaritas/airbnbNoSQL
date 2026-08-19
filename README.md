# Airbnb NYC — Analyse & WebApp sur Redis (NoSQL)

Projet Pro final — NoSQL & Big Data.

## Contexte

Analyse du dataset [Airbnb Open Data (NYC)](https://www.kaggle.com/datasets/arianazmoudeh/airbnbopendata)
(~103 000 annonces), stocké dans une base NoSQL **Redis** (Redis Stack : RedisJSON + RediSearch),
avec un rapport analytique et une WebApp de visualisation.

## Stack technique

- **Base de données** : Redis Stack (RedisJSON pour le stockage document, RediSearch pour
  l'indexation et les agrégations) — équivalent d'un moteur orienté document, choisi à la place
  de MongoDB pour explorer l'écosystème Redis.
- **Python** : `redis-py`, `pandas` pour l'ETL et le CRUD.
- **WebApp** : Streamlit.
- **Conteneurisation** : Docker / docker-compose (dev local), migration possible vers Redis Cloud.

## Équipe & suivi des tâches

- Trello : _(lien à ajouter)_
- Membres : _(à compléter)_

## Lien vers la présentation

_(lien Google Slides à ajouter)_

## Structure du repo

```
.
├── data/                   # dataset (non versionné, voir "Récupérer les données")
├── notebooks/              # notebook d'exploration/nettoyage/ETL (non cleané)
├── scripts/                # scripts CRUD, chargement, administration Redis
├── webapp/                 # application Streamlit
├── docker-compose.yml      # Redis Stack en local
├── requirements.txt
└── README.md
```

## Récupérer les données

Télécharger le CSV depuis Kaggle et le placer dans `data/Airbnb_Open_Data.csv` :
https://www.kaggle.com/datasets/arianazmoudeh/airbnbopendata

## Installation

```bash
py -m venv .venv
.venv\Scripts\activate
py -m pip install -r requirements.txt
```

## Lancer Redis en local (Docker)

```bash
docker compose up -d
```

- Redis : `localhost:6379`
- RedisInsight (interface graphique) : http://localhost:8001

## Charger les données dans Redis

```bash
py scripts/load_data.py
```

## Lancer la WebApp

```bash
streamlit run webapp/app.py
```

À quoi sert l'app, ses fonctionnalités en détail, et son déploiement : voir
[`webapp/README.md`](webapp/README.md).

## Scripts

| Script | Rôle |
|---|---|
| `scripts/cleaning.py` | Nettoyage du CSV brut (fonction `load_and_clean`, réutilisée partout) |
| `scripts/redis_schema.py` | Clés, index RediSearch (`create_index`), conversion ligne → document JSON |
| `scripts/load_data.py` | Import bulk du dataset nettoyé dans Redis via pipeline (`py scripts/load_data.py`) |
| `scripts/queries.py` | Requêtes d'agrégation métier (`FT.AGGREGATE`), utilisées par le notebook et la WebApp |
| `scripts/backup.py` | Sauvegarde (`BGSAVE` + copie RDB/AOF hors du conteneur) : `py scripts/backup.py` |
| `scripts/restore.py` | Restauration d'une sauvegarde : `py scripts/restore.py backups/<horodatage>` |
| `scripts/security_setup.py` | Création d'utilisateurs ACL à privilèges restreints (`webapp` lecture seule, `loader` écriture limitée) |

## Performance & sécurité

- **Index** RediSearch (`TAG`/`NUMERIC SORTABLE`/`GEO`) sur les champs de filtre/tri fréquents,
  au lieu d'un `SCAN` + filtrage côté client.
- **Pipelines** pour tous les imports en masse (`load_data.py`) plutôt qu'un aller-retour réseau
  par document.
- **Persistance** RDB (snapshots) + AOF activés (voir `docker-compose.yml`) pour pouvoir
  restaurer après un incident.
- **Sécurité** : en local (dev), Redis tourne sans mot de passe pour simplifier ; en production
  (Redis Cloud), on active un mot de passe/TLS et des utilisateurs **ACL** à privilèges minimaux
  (`scripts/security_setup.py`) plutôt que d'utiliser le compte `default` partout.
