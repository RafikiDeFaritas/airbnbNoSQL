"""Restauration de la base Redis à partir d'une sauvegarde produite par backup.py.

Usage:
    py scripts/restore.py backups/20260819-143000 [--container airbnb-redis]

Arrête le conteneur, remplace le dump RDB (et l'AOF s'il existe) par la sauvegarde choisie,
puis redémarre le conteneur : Redis recharge automatiquement les données au démarrage.
"""
import argparse
import subprocess
from pathlib import Path


def restore(backup_dir: str, container: str) -> None:
    backup_path = Path(backup_dir)
    rdb_file = backup_path / "dump.rdb"
    if not rdb_file.exists():
        raise FileNotFoundError(f"Pas de dump.rdb dans {backup_path}")

    print(f"Arrêt du conteneur {container}...")
    subprocess.run(["docker", "stop", container], check=True)

    print("Restauration du dump RDB...")
    subprocess.run(["docker", "cp", str(rdb_file), f"{container}:/data/dump.rdb"], check=True)

    aof_dir = backup_path / "appendonlydir"
    if aof_dir.exists():
        # Le conteneur est arrêté : on ne peut pas "docker exec" pour nettoyer l'ancien
        # dossier AOF avant restauration. `docker cp` fusionne/écrase les fichiers du
        # backup mais ne supprime pas d'éventuels fichiers résiduels non présents dans
        # la sauvegarde (limitation acceptée ici, sans impact avec le nommage AOF de Redis).
        print("Restauration de l'AOF...")
        subprocess.run(["docker", "cp", str(aof_dir), f"{container}:/data/appendonlydir"], check=True)

    print(f"Redémarrage du conteneur {container}...")
    subprocess.run(["docker", "start", container], check=True)
    print("Restauration terminée.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("backup_dir", help="Dossier de sauvegarde (ex: backups/20260819-143000)")
    parser.add_argument("--container", default="airbnb-redis")
    args = parser.parse_args()
    restore(args.backup_dir, args.container)
