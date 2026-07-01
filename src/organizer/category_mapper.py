from src.core.config import load_config
from src.core.document_types import ARCHIVE_CATEGORY_LABELS, UNKNOWN

config = load_config()


def get_archive_category(document_type):

    return config["archive"]["category_mapping"].get(
        document_type,
        ARCHIVE_CATEGORY_LABELS[UNKNOWN],
    )
