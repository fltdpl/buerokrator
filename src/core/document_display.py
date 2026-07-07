import json

from src.core.document_types import BANK, HOUSING, INSURANCE, INVOICE, PENSION, TAX

TAX_SUBTYPE_SHORT_LABELS = {
    "lohnsteuerbescheinigung": "Lohnsteuer",
    "gehaltsabrechnung": "Gehaltsabrechnung",
    "einkommensbescheinigung": "Einkommensbescheinigung",
    "bescheinigung": "Bescheinigung",
}


def get_document_display_name(
    document_type,
    extracted_data,
    year=None,
):

    if isinstance(
        extracted_data,
        str,
    ):
        try:
            data = json.loads(extracted_data)

        except Exception:
            data = {}

    else:
        data = extracted_data or {}

    issuer = (
        data.get("issuer") or data.get("insurer") or data.get("employer") or "Unbekannt"
    )

    issuer = issuer[:10]

    if document_type == INVOICE:
        document_label = "Rechnung"

    elif document_type == INSURANCE:
        document_label = data.get("insurance_type") or "Versicherung"

    elif document_type == PENSION:
        document_label = data.get("product_name") or "Vorsorge"

    elif document_type == TAX:
        subtype = data.get("document_subtype")
        if subtype == "bescheinigung":
            document_label = data.get("description") or "Bescheinigung"
        else:
            document_label = TAX_SUBTYPE_SHORT_LABELS.get(subtype, "Steuer")

    elif document_type == BANK:
        document_label = data.get("document_subtype") or "Bank"

    elif document_type == HOUSING:
        document_label = data.get("document_subtype") or "Wohnen"

    else:
        document_label = "Dokument"

    if year:
        return f"{year} · {issuer} · {document_label}"

    return f"{issuer} · {document_label}"
