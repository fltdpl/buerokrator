CATEGORY_MAP = {
    "invoice": "Rechnungen",
    "tax": "Steuern",
    "insurance": "Versicherungen",
    "building_savings": "Vorsorge",
    "pension": "Vorsorge",
    "unknown": "Sonstiges",
}


def get_archive_category(document_type):

    return CATEGORY_MAP.get(document_type, "Sonstiges")
