from pathlib import Path

from src.organizer.category_mapper import get_archive_category
from src.organizer.date_utils import normalize_date
from src.organizer.issuer_normalizer import normalize_issuer


def get_unique_target_path(target):

    original_stem = target.stem
    suffix = target.suffix
    counter = 1

    while target.exists():
        target = target.parent / f"{original_stem}_{counter}{suffix}"

        counter += 1

    return target


def build_filename(classification, extracted_data, original_file_path):

    document_type = classification["document_type"]
    suffix = Path(original_file_path).suffix

    if document_type == "invoice":
        return build_invoice_filename(extracted_data, suffix)

    if document_type == "tax":
        return build_tax_filename(extracted_data, suffix)

    if document_type == "insurance":
        return build_insurance_filename(extracted_data, suffix)

    if document_type == "pension":
        return build_pension_filename(extracted_data, suffix)

    return f"{document_type}{suffix}"


def rename_document(
    current_path,
    document_type,
    extracted_data,
):

    current_path = Path(current_path)

    category = get_archive_category(document_type)

    target_folder = Path("archive") / current_path.parent.parent.name / category

    target_folder.mkdir(
        parents=True,
        exist_ok=True,
    )

    classification = {
        "document_type": document_type,
    }

    new_filename = build_filename(
        classification,
        extracted_data,
        current_path.name,
    )

    target = target_folder / new_filename

    target = get_unique_target_path(target)

    current_path.rename(target)

    return target


def build_invoice_filename(extracted_data, suffix):

    document_date = extracted_data.get("document_date", "unknown_date")
    document_date = normalize_date(document_date)

    issuer = extracted_data.get("issuer", "unknown_issuer")
    issuer = normalize_issuer(issuer)
    issuer = issuer.replace(" ", "_").replace("/", "_")

    invoice_number = extracted_data.get("invoice_number", "unknown_invoice")
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


def build_insurance_filename(extracted_data, suffix):

    document_date = extracted_data.get("document_date", "unknown_date")
    document_date = normalize_date(document_date)
    issuer = (
        extracted_data.get("issuer")
        or extracted_data.get("insurer")
        or "unknown_issuer"
    )
    issuer = normalize_issuer(issuer)
    issuer = issuer.replace(" ", "_").replace("/", "_")

    insurance_type = extracted_data.get("insurance_type", "unknown_insurance")
    insurance_type = insurance_type.replace(" ", "_").replace("/", "_")
    policy_number = extracted_data.get("policy_number", "unknown_policy")
    policy_number = policy_number.replace(" ", "-").replace("/", "-").replace(".", "-")

    return f"{document_date}_{issuer}_{insurance_type}_{policy_number}{suffix}"


def build_pension_filename(
    extracted_data,
    suffix,
):

    document_date = extracted_data.get(
        "document_date",
        "unknown_date",
    )
    document_date = normalize_date(document_date)

    issuer = extracted_data.get("issuer") or "unknown_issuer"
    issuer = normalize_issuer(issuer)
    issuer = issuer.replace(" ", "_").replace("/", "_")

    document_subtype = extracted_data.get(
        "document_subtype",
        "unknown",
    )

    policy_number = extracted_data.get(
        "policy_number",
        "unknown_policy",
    )

    policy_number = policy_number.replace(" ", "-").replace("/", "-").replace(".", "-")

    return f"{document_date}_{issuer}_{document_subtype}_{policy_number}{suffix}"
