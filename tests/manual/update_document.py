from src.database.update_document import (
    update_document,
)

update_document(
    document_id=1,
    filename="TEST.pdf",
    archive_path="/tmp/TEST.pdf",
    document_type="pension",
    extracted_data={
        "issuer": "Debeka",
    },
)

print("ok")
