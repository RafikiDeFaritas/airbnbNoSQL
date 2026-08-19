"""Schéma Redis pour les annonces Airbnb : clés, index RediSearch, conversion document.

Modèle : un document JSON dénormalisé par annonce, clé `listing:<id>`.
Toutes les infos (y compris l'hôte) sont embarquées dans le document — pas de jointure,
comme attendu pour une base orientée document.
"""
import os
from datetime import datetime, timezone

import pandas as pd
import redis
from dotenv import load_dotenv
from redis.commands.search.field import GeoField, NumericField, TagField, TextField
from redis.commands.search.index_definition import IndexDefinition, IndexType

load_dotenv()

INDEX_NAME = "idx:listings"
KEY_PREFIX = "listing:"


def get_redis_client() -> redis.Redis:
    client = redis.Redis(
        host=os.getenv("REDIS_HOST", "localhost"),
        port=int(os.getenv("REDIS_PORT", 6379)),
        password=os.getenv("REDIS_PASSWORD") or None,
        decode_responses=True,
    )
    try:
        # Le timeout par défaut de FT.AGGREGATE (500ms) est trop court pour grouper
        # ~100k documents sur plusieurs champs. Sans effet sur certaines offres
        # managées (Redis Cloud peut refuser FT.CONFIG SET) -> on ignore l'échec.
        client.execute_command("FT.CONFIG", "SET", "TIMEOUT", "10000")
    except redis.ResponseError:
        pass
    return client


def listing_key(listing_id: int) -> str:
    return f"{KEY_PREFIX}{listing_id}"


def create_index(client: redis.Redis, drop_existing: bool = False) -> None:
    """Crée l'index RediSearch sur les documents JSON `listing:*` (dénormalisation + indexation)."""
    if drop_existing:
        try:
            client.ft(INDEX_NAME).dropindex()
        except redis.ResponseError:
            pass

    schema = (
        TextField("$.name", as_name="name"),
        TagField("$.neighbourhood_group", as_name="neighbourhood_group"),
        TagField("$.neighbourhood", as_name="neighbourhood"),
        TagField("$.room_type", as_name="room_type"),
        NumericField("$.host.id", as_name="host_id"),
        TagField("$.instant_bookable", as_name="instant_bookable"),
        TagField("$.cancellation_policy", as_name="cancellation_policy"),
        NumericField("$.price", as_name="price", sortable=True),
        NumericField("$.service_fee", as_name="service_fee"),
        NumericField("$.minimum_nights", as_name="minimum_nights"),
        NumericField("$.reviews.number_of_reviews", as_name="number_of_reviews", sortable=True),
        NumericField("$.reviews.reviews_per_month", as_name="reviews_per_month"),
        NumericField("$.reviews.review_rate_number", as_name="review_rate_number", sortable=True),
        NumericField("$.availability_365", as_name="availability_365", sortable=True),
        NumericField("$.construction_year", as_name="construction_year"),
        NumericField(
            "$.host.calculated_listings_count", as_name="calculated_listings_count", sortable=True
        ),
        GeoField("$.geo", as_name="geo"),
    )
    client.ft(INDEX_NAME).create_index(
        schema,
        definition=IndexDefinition(prefix=[KEY_PREFIX], index_type=IndexType.JSON),
    )


def row_to_doc(row: pd.Series) -> dict:
    """Convertit une ligne du DataFrame nettoyé en document JSON dénormalisé pour Redis."""
    last_review = row["last_review"]
    return {
        "id": int(row["id"]),
        "name": row["name"],
        "host": {
            "id": int(row["host_id"]),
            "name": row["host_name"],
            "identity_verified": row["host_identity_verified"],
            "calculated_listings_count": (
                None
                if pd.isna(row["calculated_host_listings_count"])
                else int(row["calculated_host_listings_count"])
            ),
        },
        "neighbourhood_group": row["neighbourhood_group"],
        "neighbourhood": row["neighbourhood"],
        "lat": float(row["lat"]),
        "long": float(row["long"]),
        "geo": f"{row['long']},{row['lat']}",
        "room_type": row["room_type"],
        "construction_year": None if pd.isna(row["construction_year"]) else int(row["construction_year"]),
        "price": float(row["price"]),
        "service_fee": float(row["service_fee"]),
        "minimum_nights": int(row["minimum_nights"]),
        "instant_bookable": bool(row["instant_bookable"]) if not pd.isna(row["instant_bookable"]) else None,
        "cancellation_policy": row["cancellation_policy"],
        "reviews": {
            "number_of_reviews": int(row["number_of_reviews"]),
            "reviews_per_month": float(row["reviews_per_month"]),
            "review_rate_number": (
                None if pd.isna(row["review_rate_number"]) else float(row["review_rate_number"])
            ),
            "last_review": None if pd.isna(last_review) else last_review.strftime("%Y-%m-%d"),
        },
        "availability_365": int(row["availability_365"]),
        "house_rules": None if pd.isna(row["house_rules"]) else row["house_rules"],
        "ingested_at": datetime.now(timezone.utc).isoformat(),
    }
