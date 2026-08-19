"""WebApp Streamlit — dashboard Airbnb NYC sur Redis (RedisJSON + RediSearch).

Lancer avec : streamlit run webapp/app.py
"""
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent / "scripts"))

import pandas as pd
import streamlit as st
import redis.commands.search.reducers as reducers
from redis.commands.search.aggregation import AggregateRequest
from redis.commands.search.query import Query

from queries import (
    avg_price_by_neighbourhood_group,
    avg_price_by_room_type_and_group,
    availability_stats_by_room_type,
    top_hosts_by_listings,
    top_neighbourhoods_by_count,
)
from redis_schema import INDEX_NAME, get_redis_client


def escape_tag(value: str) -> str:
    """Échappe un texte pour l'utiliser dans un filtre TAG RediSearch (`{val1|val2}`)."""
    for char in (" ", "/", "-", "."):
        value = value.replace(char, f"\\{char}")
    return value

st.set_page_config(page_title="Airbnb NYC — Redis Dashboard", layout="wide")


@st.cache_resource
def redis_client():
    client = get_redis_client()
    client.ping()
    return client


r = redis_client()

st.title("🏠 Airbnb NYC — Dashboard (Redis / RediSearch)")
st.caption(f"Base : {r.dbsize()} annonces indexées dans Redis (RedisJSON + RediSearch).")

# --- Filtres (sidebar) ---------------------------------------------------
st.sidebar.header("Filtres")

groups_res = r.ft(INDEX_NAME).aggregate(AggregateRequest("*").group_by("@neighbourhood_group"))
all_groups = sorted(row[1] for row in groups_res.rows)
selected_groups = st.sidebar.multiselect("Borough", all_groups, default=all_groups)

room_types = ["Entire home/apt", "Private room", "Shared room", "Hotel room"]
selected_room_types = st.sidebar.multiselect("Type de logement", room_types, default=room_types)

price_min, price_max = st.sidebar.slider("Prix ($)", 0, 1200, (0, 1200))

# --- Requête RediSearch filtrée -------------------------------------------
if not selected_groups or not selected_room_types:
    st.warning("Sélectionne au moins un borough et un type de logement.")
    filtered_df = pd.DataFrame(columns=["id", "name", "neighbourhood", "price", "lat", "long"])
else:
    group_filter = "|".join(escape_tag(g) for g in selected_groups)
    room_filter = "|".join(escape_tag(t) for t in selected_room_types)

    query_str = (
        f"(@neighbourhood_group:{{{group_filter}}}) "
        f"(@room_type:{{{room_filter}}}) "
        f"(@price:[{price_min} {price_max}])"
    )
    query = Query(query_str).paging(0, 500).return_fields("id", "name", "neighbourhood", "price", "lat", "long")
    results = r.ft(INDEX_NAME).search(query)

    st.subheader(f"Résultats du filtre : {results.total} annonces (aperçu des 500 premières)")

    rows = [
        {
            "id": doc.id.replace("listing:", ""),
            "name": getattr(doc, "name", ""),
            "neighbourhood": getattr(doc, "neighbourhood", ""),
            "price": float(getattr(doc, "price", 0)),
            "lat": float(getattr(doc, "lat", 0)),
            "long": float(getattr(doc, "long", 0)),
        }
        for doc in results.docs
    ]
    filtered_df = pd.DataFrame(rows)

col_map, col_table = st.columns([2, 1])
with col_map:
    if not filtered_df.empty:
        st.map(filtered_df.rename(columns={"lat": "latitude", "long": "longitude"}), size=20)
    else:
        st.info("Aucune annonce ne correspond aux filtres sélectionnés.")
with col_table:
    st.dataframe(filtered_df[["name", "neighbourhood", "price"]], height=420)

st.divider()

# --- Rapport analytique (questions métier, agrégations Redis) -------------
st.header("📊 Rapport analytique")

tab1, tab2, tab3, tab4 = st.tabs(
    ["Prix par borough", "Prix par type de logement", "Top quartiers", "Top hôtes"]
)

with tab1:
    q1 = pd.DataFrame(avg_price_by_neighbourhood_group(r))
    q1["avg_price"] = q1["avg_price"].astype(float)
    q1["n_listings"] = q1["n_listings"].astype(int)
    st.bar_chart(q1.set_index("neighbourhood_group")["avg_price"])
    st.dataframe(q1)

with tab2:
    q2 = pd.DataFrame(avg_price_by_room_type_and_group(r))
    q2["avg_price"] = q2["avg_price"].astype(float)
    pivot = q2.pivot(index="neighbourhood_group", columns="room_type", values="avg_price")
    st.bar_chart(pivot)
    st.dataframe(pivot.round(1))

with tab3:
    q3 = pd.DataFrame(top_neighbourhoods_by_count(r, n=10))
    q3["n_listings"] = q3["n_listings"].astype(int)
    q3["avg_price"] = q3["avg_price"].astype(float).round(1)
    st.bar_chart(q3.set_index("neighbourhood")["n_listings"])
    st.dataframe(q3)

with tab4:
    st.caption(
        "`host_id` est quasi unique par annonce dans ce dataset : le vrai signal de "
        "\"power host\" est le champ `calculated_host_listings_count`, déjà précalculé "
        "dans les données sources."
    )
    q5 = pd.DataFrame(top_hosts_by_listings(r, n=10))
    st.dataframe(q5)

st.divider()
st.caption(
    "Toutes les agrégations affichées sont exécutées directement dans Redis via `FT.AGGREGATE` "
    "(module RediSearch) — voir `scripts/queries.py`."
)
