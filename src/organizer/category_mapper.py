from src.core.config import load_config

config = load_config()


def get_archive_category(document_type):

    return config["archive"]["category_mapping"].get(document_type, "Sonstiges")
