import sqlite3
from pathlib import Path

from src.core.config import load_config


def get_connection():
    config = load_config()

    db_path = config["database"]["path"]
    Path(db_path).parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    return sqlite3.connect(db_path)
