"""Import (bulk) du dataset Airbnb nettoyé dans Redis.

Usage:
    py scripts/load_data.py [--csv data/Airbnb_Open_Data.csv] [--batch-size 1000] [--sample N]

Charge le CSV brut, applique le nettoyage (scripts/cleaning.py), crée l'index RediSearch,
puis insère les documents JSON par lots via pipeline (import de fichier volumineux performant).

--sample N tire un échantillon aléatoire de N annonces au lieu de tout charger : utile pour les
offres Redis Cloud gratuites à mémoire limitée (~30 Mo, largement en dessous des ~101 760
annonces complètes). L'analyse complète (notebook) reste, elle, basée sur le dataset entier.
"""
import argparse
import time

from cleaning import load_and_clean
from redis_schema import create_index, get_redis_client, listing_key, row_to_doc


def load(csv_path: str, batch_size: int = 1000, sample: int | None = None) -> None:
    client = get_redis_client()
    client.ping()

    df = load_and_clean(csv_path)
    print(f"{len(df)} annonces nettoyées disponibles.")

    if sample is not None and sample < len(df):
        df = df.sample(n=sample, random_state=42).reset_index(drop=True)
        print(f"Échantillon aléatoire de {len(df)} annonces retenu (random_state=42).")

    create_index(client, drop_existing=True)
    print("Index RediSearch recréé.")

    start = time.time()
    pipe = client.pipeline(transaction=False)
    for i, (_, row) in enumerate(df.iterrows(), start=1):
        doc = row_to_doc(row)
        pipe.json().set(listing_key(doc["id"]), "$", doc)
        if i % batch_size == 0:
            pipe.execute()
            print(f"  {i}/{len(df)} documents insérés...")
    pipe.execute()

    elapsed = time.time() - start
    print(f"Import terminé : {len(df)} documents en {elapsed:.1f}s.")
    print("Clés en base :", client.dbsize())


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", default="data/Airbnb_Open_Data.csv")
    parser.add_argument("--batch-size", type=int, default=1000)
    parser.add_argument("--sample", type=int, default=None, help="Nombre d'annonces à échantillonner aléatoirement")
    args = parser.parse_args()
    load(args.csv, args.batch_size, args.sample)
