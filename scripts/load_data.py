"""Import (bulk) du dataset Airbnb nettoyé dans Redis.

Usage:
    py scripts/load_data.py [--csv data/Airbnb_Open_Data.csv] [--batch-size 1000]

Charge le CSV brut, applique le nettoyage (scripts/cleaning.py), crée l'index RediSearch,
puis insère les documents JSON par lots via pipeline (import de fichier volumineux performant).
"""
import argparse
import time

from cleaning import load_and_clean
from redis_schema import create_index, get_redis_client, listing_key, row_to_doc


def load(csv_path: str, batch_size: int = 1000) -> None:
    client = get_redis_client()
    client.ping()

    df = load_and_clean(csv_path)
    print(f"{len(df)} annonces nettoyées à charger.")

    create_index(client, drop_existing=True)
    print(f"Index RediSearch recréé.")

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
    args = parser.parse_args()
    load(args.csv, args.batch_size)
