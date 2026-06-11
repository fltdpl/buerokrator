from pathlib import Path

from src.organizer.date_utils import normalize_date
from src.organizer.issuer_normalizer import normalize_issuer


def build_invoice_filename(extracted_data, suffix):

    document_date = extracted_data.get("document_date", "unknown_date")
    document_date = normalize_date(document_date)

    issuer = extracted_data.get("issuer", "unknown_issuer")
    issuer = normalize_issuer(issuer)
    issuer = issuer.replace(" ", "_").replace("/", "_")

    invoice_number = extracted_data.get("invoice_number", "")
    invoice_number = invoice_number.replace("/", "-")

    amount = extracted_data.get("amount")

    if amount is not None:
        return f"{document_date}_{issuer}_{invoice_number}_{amount:.0f}EUR{suffix}"

    return f"{document_date}_{issuer}{suffix}"


def build_tax_filename(extracted_data, suffix):

    employer = extracted_data.get("employer", "unknown_employer")
    tax_year = extracted_data.get("tax_year", "unknown_year")
    employer = employer.replace(" ", "_").replace("/", "_")

    return f"{tax_year}_{employer}_Lohnsteuerbescheinigung{suffix}"


def build_filename(classification, extracted_data, original_file_path):

    document_type = classification["document_type"]
    suffix = Path(original_file_path).suffix

    if document_type == "invoice":
        return build_invoice_filename(extracted_data, suffix)

    if document_type == "tax":
        return build_tax_filename(extracted_data, suffix)

    return f"{document_type}{suffix}"
