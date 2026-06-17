import sqlite3

from src.core.config import load_config

config = load_config()


def get_connection():

    db_path = config["database"]["path"]

    return sqlite3.connect(db_path)
