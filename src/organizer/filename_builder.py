from pathlib import Path

from src.organizer.date_utils import normalize_date
from src.organizer.issuer_normalizer import normalize_issuer


def build_filename(classification, extracted_data, original_file_path):

    suffix = Path(original_file_path).suffix

    document_date = extracted_data.get("document_date", "unknown_date")
    document_date = normalize_date(document_date)
    issuer = extracted_data.get("issuer", "unknown_issuer")
    amount = extracted_data.get("amount")
    invoice_number = extracted_data.get("invoice_number", "")
    invoice_number = invoice_number.replace("/", "-")
    document_date = document_date.replace(".", "-")
    issuer = normalize_issuer(issuer)
    issuer = issuer.replace(" ", "_").replace("/", "_")

    if amount is not None:
        return f"{document_date}_{issuer}_{invoice_number}_{amount:.0f}EUR{suffix}"

    return f"{document_date}_{issuer}{suffix}"
