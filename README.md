# Airbnb NYC — Analyse & WebApp sur Redis (NoSQL)

Projet Pro final — NoSQL & Big Data.

**🚀 WebApp en ligne : https://airbnbnosql-dfbvtppvosgzxtgxpwxu3c.streamlit.app/**

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

- Trello : https://trello.com/b/Kpg6iOJf/airbnb-nyc-projet-nosql
- Membres : Romain, Raphaël

## Lien vers la présentation

https://claude.ai/code/artifact/15af7132-a4d0-4f40-81b3-af01efe6acf0

Source éditable : [`presentation/index.html`](presentation/index.html) (diapositives HTML,
navigables au clavier/clic — pas besoin de compte pour l'ouvrir).

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

## Mise en production (Redis Cloud)

Le projet est aussi déployé sur une base **Redis Cloud** (offre gratuite), avec RedisJSON et
RediSearch. Les identifiants sont dans `.env` (non versionné — voir `.env.example` pour le
format) ; `scripts/redis_schema.py` les charge automatiquement via `python-dotenv`, donc tous les
scripts (`load_data.py`, `queries.py`, la WebApp...) s'y connectent sans configuration
supplémentaire dès que `.env` est renseigné.

⚠️ **Limite mémoire** : l'offre gratuite Redis Cloud (~30 Mo) ne suffit pas pour les 101 760
annonces complètes (~2 Ko/document avec l'index, soit ~215 Mo au total). En production, on charge
donc un **échantillon aléatoire représentatif de 11 000 annonces**
(`py scripts/load_data.py --sample 11000`, `random_state=42` pour la reproductibilité) — les
tendances observées (prix par borough, top quartiers...) restent cohérentes avec l'analyse
complète menée en local sur les 101 760 documents (voir le notebook).

## Charger les données dans Redis

```bash
py scripts/load_data.py                  # local : dataset complet (101 760 annonces)
py scripts/load_data.py --sample 11000    # Redis Cloud gratuit : échantillon (mémoire limitée)
```

## Lancer la WebApp

Déjà en ligne, connectée à Redis Cloud : **https://airbnbnosql-dfbvtppvosgzxtgxpwxu3c.streamlit.app/**

En local :

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
