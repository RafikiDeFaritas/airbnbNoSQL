"""Durcissement de la sécurité Redis via ACL (utilisateurs à privilèges restreints).

En local (Docker de dev), Redis tourne sans mot de passe pour simplifier le développement.
Ce script montre comment on sécurise l'instance avant la mise en prod (ex : Redis Cloud) :
- un utilisateur admin dédié (au lieu du compte `default`)
- un utilisateur `webapp` en lecture seule, restreint aux clés `listing:*`

Usage:
    py scripts/security_setup.py
"""
from redis_schema import get_redis_client


def setup_acl() -> None:
    client = get_redis_client()

    # Utilisateur applicatif : lecture seule, restreint aux clés listing:* et à l'index de recherche
    client.acl_setuser(
        "webapp",
        enabled=True,
        passwords=["+webapp_change_me"],
        keys=["~listing:*"],
        commands=["-@all", "+@read", "+ft.search", "+ft.aggregate", "+json.get", "+json.mget"],
    )
    print("Utilisateur 'webapp' créé (lecture seule, clés listing:*).")

    # Utilisateur d'ingestion : écriture limitée aux commandes JSON/index nécessaires au chargement
    client.acl_setuser(
        "loader",
        enabled=True,
        passwords=["+loader_change_me"],
        keys=["~listing:*"],
        commands=["-@all", "+json.set", "+json.del", "+ft.create", "+ft._list", "+ft.dropindex", "+ping"],
    )
    print("Utilisateur 'loader' créé (écriture restreinte, pour scripts/load_data.py).")

    print("\nUtilisateurs ACL configurés :", client.acl_list())


if __name__ == "__main__":
    setup_acl()
