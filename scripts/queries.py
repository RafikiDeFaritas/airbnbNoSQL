"""Requêtes d'agrégation métier sur l'index RediSearch `idx:listings`.

Réutilisées par le notebook d'analyse et par la WebApp Streamlit.
"""
import redis
import redis.commands.search.reducers as reducers
from redis.commands.search.aggregation import AggregateRequest, Desc
from redis.commands.search.query import Query

from redis_schema import INDEX_NAME


def avg_price_by_neighbourhood_group(r: redis.Redis) -> list[dict]:
    """Prix moyen et nombre d'annonces par borough (neighbourhood_group)."""
    req = (
        AggregateRequest("*")
        .group_by(
            "@neighbourhood_group",
            reducers.avg("price").alias("avg_price"),
            reducers.count().alias("n_listings"),
        )
        .sort_by(Desc("@avg_price"))
    )
    res = r.ft(INDEX_NAME).aggregate(req)
    return [row_to_dict(row) for row in res.rows]


def avg_price_by_room_type_and_group(r: redis.Redis) -> list[dict]:
    """Prix moyen par (borough, type de logement)."""
    req = AggregateRequest("*").group_by(
        ["@neighbourhood_group", "@room_type"],
        reducers.avg("price").alias("avg_price"),
        reducers.count().alias("n_listings"),
    )
    res = r.ft(INDEX_NAME).aggregate(req)
    return [row_to_dict(row) for row in res.rows]


def top_neighbourhoods_by_count(r: redis.Redis, n: int = 10) -> list[dict]:
    """Les n quartiers avec le plus d'annonces, prix moyen associé."""
    req = (
        AggregateRequest("*")
        .group_by(
            "@neighbourhood",
            reducers.count().alias("n_listings"),
            reducers.avg("price").alias("avg_price"),
        )
        .sort_by(Desc("@n_listings"))
        .limit(0, n)
    )
    res = r.ft(INDEX_NAME).aggregate(req)
    return [row_to_dict(row) for row in res.rows]


def top_hosts_by_listings(r: redis.Redis, n: int = 10) -> list[dict]:
    """Les n annonces des hôtes ayant le plus d'annonces au total.

    `host_id` est quasi unique par annonce dans ce dataset (101 759 valeurs pour 101 760
    lignes : un GROUPBY dessus ne révèle donc aucun "power host"). Le champ
    `calculated_host_listings_count`, déjà précalculé dans les données sources, porte la
    vraie information ; on trie directement dessus plutôt que de grouper.
    """
    query = Query("*").sort_by("calculated_listings_count", asc=False).paging(0, n)
    results = r.ft(INDEX_NAME).search(query)

    rows = []
    for doc in results.docs:
        full = r.json().get(doc.id)
        rows.append(
            {
                "host_id": full["host"]["id"],
                "host_name": full["host"]["name"],
                "calculated_listings_count": full["host"]["calculated_listings_count"],
                "review_rate_number": full["reviews"]["review_rate_number"],
                "listing_name": full["name"],
            }
        )
    return rows


def availability_stats_by_room_type(r: redis.Redis) -> list[dict]:
    """Disponibilité annuelle moyenne par type de logement."""
    req = AggregateRequest("*").group_by(
        "@room_type",
        reducers.avg("availability_365").alias("avg_availability"),
        reducers.avg("number_of_reviews").alias("avg_reviews"),
        reducers.count().alias("n_listings"),
    )
    res = r.ft(INDEX_NAME).aggregate(req)
    return [row_to_dict(row) for row in res.rows]


def row_to_dict(row: list) -> dict:
    """Convertit une ligne de résultat FT.AGGREGATE (liste plate clé/valeur) en dict."""
    return dict(zip(row[0::2], row[1::2]))
