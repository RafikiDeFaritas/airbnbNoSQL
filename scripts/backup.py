"""Sauvegarde de la base Redis (dump RDB + AOF) hors du conteneur Docker.

Usage:
    py scripts/backup.py [--container airbnb-redis] [--out-dir backups]

Déclenche un BGSAVE (snapshot RDB cohérent, non bloquant), attend sa fin, puis copie
`dump.rdb` et le dossier AOF (`appendonlydir`) du conteneur vers `backups/<timestamp>/`.
"""
import argparse
import subprocess
import time
from pathlib import Path

from redis_schema import get_redis_client


def backup(container: str, out_dir: str) -> Path:
    client = get_redis_client()
    last_save_before = client.lastsave()

    client.bgsave()
    print("BGSAVE lancé, attente de la fin du snapshot...")
    while client.lastsave() == last_save_before:
        time.sleep(0.5)
    print("Snapshot RDB terminé.")

    timestamp = time.strftime("%Y%m%d-%H%M%S")
    dest = Path(out_dir) / timestamp
    dest.mkdir(parents=True, exist_ok=True)

    subprocess.run(["docker", "cp", f"{container}:/data/dump.rdb", str(dest / "dump.rdb")], check=True)
    subprocess.run(
        ["docker", "cp", f"{container}:/data/appendonlydir", str(dest / "appendonlydir")],
        check=False,  # AOF peut être désactivé selon la config
    )

    print(f"Sauvegarde écrite dans {dest}")
    return dest


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--container", default="airbnb-redis")
    parser.add_argument("--out-dir", default="backups")
    args = parser.parse_args()
    backup(args.container, args.out_dir)
