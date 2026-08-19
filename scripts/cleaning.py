"""Nettoyage du dataset Airbnb Open Data (NYC).

Logique partagée entre le notebook d'exploration, le script de chargement Redis
et la WebApp, pour ne l'écrire qu'une seule fois.
"""
import pandas as pd

COLUMN_RENAME = {
    "id": "id",
    "NAME": "name",
    "host id": "host_id",
    "host_identity_verified": "host_identity_verified",
    "host name": "host_name",
    "neighbourhood group": "neighbourhood_group",
    "neighbourhood": "neighbourhood",
    "lat": "lat",
    "long": "long",
    "instant_bookable": "instant_bookable",
    "cancellation_policy": "cancellation_policy",
    "room type": "room_type",
    "Construction year": "construction_year",
    "price": "price",
    "service fee": "service_fee",
    "minimum nights": "minimum_nights",
    "number of reviews": "number_of_reviews",
    "last review": "last_review",
    "reviews per month": "reviews_per_month",
    "review rate number": "review_rate_number",
    "calculated host listings count": "calculated_host_listings_count",
    "availability 365": "availability_365",
    "house_rules": "house_rules",
}

NEIGHBOURHOOD_GROUP_FIXES = {
    "brookln": "Brooklyn",
    "manhatan": "Manhattan",
}

DROP_COLUMNS = ["country", "country code", "license"]


def _parse_money(series: pd.Series) -> pd.Series:
    return (
        series.astype("string")
        .str.replace(r"[\$,]", "", regex=True)
        .str.strip()
        .astype(float)
    )


def load_and_clean(csv_path: str) -> pd.DataFrame:
    df = pd.read_csv(csv_path, low_memory=False)

    df = df.drop(columns=[c for c in DROP_COLUMNS if c in df.columns])
    df = df.rename(columns=COLUMN_RENAME)

    df = df.drop_duplicates()

    df["neighbourhood_group"] = df["neighbourhood_group"].replace(NEIGHBOURHOOD_GROUP_FIXES)

    df["price"] = _parse_money(df["price"])
    df["service_fee"] = _parse_money(df["service_fee"])
    df["service_fee"] = df["service_fee"].fillna(df["service_fee"].median())

    df["minimum_nights"] = df["minimum_nights"].clip(lower=1, upper=365)
    df["minimum_nights"] = df["minimum_nights"].fillna(df["minimum_nights"].median())
    df["availability_365"] = df["availability_365"].clip(lower=0, upper=365)
    df["availability_365"] = df["availability_365"].fillna(df["availability_365"].median())

    df["last_review"] = pd.to_datetime(df["last_review"], format="%m/%d/%Y", errors="coerce")
    df["reviews_per_month"] = df["reviews_per_month"].fillna(0.0)
    df["number_of_reviews"] = df["number_of_reviews"].fillna(0)

    df["name"] = df["name"].fillna("Sans titre")
    df["host_name"] = df["host_name"].fillna("Inconnu")
    df["host_identity_verified"] = df["host_identity_verified"].fillna("unknown")
    df["cancellation_policy"] = df["cancellation_policy"].fillna("unknown")
    # colonne stockée en texte ("TRUE"/"FALSE") à cause des valeurs manquantes -> vrai booléen
    df["instant_bookable"] = (
        df["instant_bookable"].astype("string").str.upper().map({"TRUE": True, "FALSE": False}).fillna(False)
    )

    df = df.dropna(subset=["lat", "long", "price", "neighbourhood_group", "neighbourhood"])

    df["id"] = df["id"].astype(int)
    df["host_id"] = df["host_id"].astype(int)

    return df.reset_index(drop=True)
