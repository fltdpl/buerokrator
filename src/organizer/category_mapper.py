from src.core.config import load_config
from src.core.document_types import ARCHIVE_CATEGORY_LABELS, UNKNOWN


def get_archive_category(document_type):

    config = load_config()

    return config["archive"]["category_mapping"].get(
        document_type,
        ARCHIVE_CATEGORY_LABELS[UNKNOWN],
    )
