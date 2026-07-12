from pathlib import Path

from src.core.document_types import (
    BANK,
    EMPLOYMENT,
    HOUSING,
    INSURANCE,
    INVOICE,
    LEGAL,
    PENSION,
    TAX,
)
from src.organizer.category_mapper import get_archive_category
from src.core.logger import logger
from src.organizer.date_utils import extract_year, normalize_date, normalize_month
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
    builders = {
        INVOICE: build_invoice_filename,
        TAX: build_tax_filename,
        INSURANCE: build_insurance_filename,
        PENSION: build_pension_filename,
        BANK: build_bank_filename,
        HOUSING: build_housing_filename,
        EMPLOYMENT: build_employment_filename,
        LEGAL: build_legal_filename,
    }

    builder = builders.get(document_type)
    if builder:
        return builder(extracted_data, suffix)

    return f"{document_type}{suffix}"


def rename_document(
    current_path,
    document_type,
    extracted_data,
):

    current_path = Path(current_path)

    if not current_path.exists():
        return current_path

    category = get_archive_category(document_type)

    # Jahr aus den (ggf. geänderten) Dokumentdaten ableiten, konsistent zu
    # archive_document. Vorher wurde das Jahr aus dem alten Pfad übernommen,
    # sodass umklassifizierte Dokumente im falschen Jahr-Ordner landeten.
    year = extract_year(extracted_data)

    target_folder = Path("archive") / year / category

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

    logger.info(f"Umbenennen: {current_path} -> {target}")
    if current_path.resolve() == target.resolve():
        return current_path

    if not current_path.exists():
        raise FileNotFoundError(f"Datei nicht gefunden: {current_path}")

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


def _clean_name(value, default):
    return (value or default).replace(" ", "_").replace("/", "_")


def build_tax_filename(extracted_data, suffix):

    tax_year = extracted_data.get("tax_year") or "unknown_year"
    subtype = (extracted_data.get("document_subtype") or "").lower()

    if subtype == "einkommensbescheinigung":
        # Finanzamt-Bescheinigung: jährlich, Aussteller = Finanzamt.
        issuer = _clean_name(extracted_data.get("issuer"), "Finanzamt")
        return f"{tax_year}-12_{issuer}_Einkommensbescheinigung{suffix}"

    # Standard/Default: Meldebescheinigung / Informationsschreiben.
    issuer = _clean_name(extracted_data.get("issuer"), "unknown_issuer")
    return f"{tax_year}_{issuer}_Bescheinigung{suffix}"


def _period_prefix(extracted_data):
    """Datumsteil aus dem Zeitraum (von–bis) oder None.

    Beide Daten -> "YYYY-MM-DD_bis_YYYY-MM-DD", nur Start -> "YYYY-MM-DD".
    Nach dem Startdatum sortierbar; unterscheidet Teilzeiträume.
    """
    start = extracted_data.get("period_start")
    end = extracted_data.get("period_end")

    if start and end:
        return f"{normalize_date(start)}_bis_{normalize_date(end)}"
    if start:
        return normalize_date(start)

    return None


def build_employment_filename(extracted_data, suffix):

    subtype = (extracted_data.get("document_subtype") or "").lower()
    tax_year = extracted_data.get("tax_year") or "unknown_year"
    period_prefix = _period_prefix(extracted_data)

    if subtype == "gehaltsabrechnung":
        employer = _clean_name(extracted_data.get("employer"), "unknown_employer")

        if period_prefix:
            return f"{period_prefix}_{employer}_Gehaltsabrechnung{suffix}"

        # Fallback (Altbestand ohne Zeitraum): Jahr-Monat wie bisher.
        month = normalize_month(extracted_data.get("month"))
        return f"{tax_year}-{month}_{employer}_Gehaltsabrechnung{suffix}"

    if subtype == "lohnsteuerbescheinigung":
        employer = _clean_name(extracted_data.get("employer"), "unknown_employer")

        # Mit Dienstverhältnis-Zeitraum: unterscheidet Teilzeiträume eines
        # Jahres (verhindert Namenskollision mehrerer Bescheinigungen).
        if period_prefix:
            return f"{period_prefix}_{employer}_Lohnsteuerbescheinigung{suffix}"

        # Fallback: jährlich, Datum als YYYY-MM, ohne Monat auf Jahresende.
        month = normalize_month(extracted_data.get("month"))
        if month == "00":
            month = "12"
        return f"{tax_year}-{month}_{employer}_Lohnsteuerbescheinigung{suffix}"

    if subtype == "sv_meldung":
        # SV-Meldung (§ 25 DEÜV): Meldezeitraum + Arbeitgeber + Betreff.
        issuer = _clean_name(
            normalize_issuer(extracted_data.get("issuer") or "unknown_issuer"),
            "unknown_issuer",
        )
        subject = _clean_name(extracted_data.get("subject"), "SV-Meldung")
        prefix = period_prefix or normalize_date(
            extracted_data.get("document_date", "unknown_date")
        )
        return f"{prefix}_{issuer}_{subject}{suffix}"

    # Arbeitsvertrag / Kündigung / Zeugnis / Sonstiges: Datum + Aussteller +
    # Betreff (Freitext).
    document_date = normalize_date(
        extracted_data.get("document_date", "unknown_date")
    )
    issuer = extracted_data.get("issuer") or "unknown_issuer"
    issuer = normalize_issuer(issuer)
    issuer = issuer.replace(" ", "_").replace("/", "_")
    subject = _clean_name(extracted_data.get("subject"), subtype or "Arbeit")

    return f"{document_date}_{issuer}_{subject}{suffix}"


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


def build_bank_filename(
    extracted_data,
    suffix,
):

    document_date = normalize_date(
        extracted_data.get(
            "document_date",
            "unknown_date",
        )
    )

    issuer = (
        extracted_data.get("issuer") or extracted_data.get("bank") or "unknown_bank"
    )

    issuer = normalize_issuer(issuer)
    issuer = issuer.replace(" ", "_")

    document_subtype = extracted_data.get(
        "document_subtype",
        "Kontoauszug",
    )

    return f"{document_date}_{issuer}_{document_subtype}{suffix}"


def build_housing_filename(
    extracted_data,
    suffix,
):

    document_date = normalize_date(
        extracted_data.get(
            "document_date",
            "unknown_date",
        )
    )

    issuer = (
        extracted_data.get("issuer")
        or extracted_data.get("landlord")
        or "unknown_housing"
    )

    issuer = normalize_issuer(issuer)
    issuer = issuer.replace(" ", "_")

    document_subtype = extracted_data.get(
        "document_subtype",
        "Wohnen",
    )

    return f"{document_date}_{issuer}_{document_subtype}{suffix}"


def build_legal_filename(
    extracted_data,
    suffix,
):

    document_date = normalize_date(
        extracted_data.get(
            "document_date",
            "unknown_date",
        )
    )

    issuer = extracted_data.get("issuer") or "unknown_issuer"
    issuer = normalize_issuer(issuer)
    issuer = issuer.replace(" ", "_").replace("/", "_")

    subject = _clean_name(extracted_data.get("subject"), "Recht")

    return f"{document_date}_{issuer}_{subject}{suffix}"
