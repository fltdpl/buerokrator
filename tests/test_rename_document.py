from src.database.rename_document import (
    rename_document,
)

target = rename_document(
    "archive/2026/Vorsorge/pension_16.pdf",
    "pension",
    {
        "issuer": "Debeka",
        "policy_number": "123",
        "document_date": "01.11.2025",
        "document_subtype": "contract",
    },
)

print(target)
