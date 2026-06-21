import json


def get_document_display_name(
    document_type,
    extracted_data,
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

    if document_type == "invoice":
        document_label = "Rechnung"

    elif document_type == "insurance":
        document_label = data.get("insurance_type") or "Versicherung"

    elif document_type == "pension":
        document_label = data.get("product_name") or "Vorsorge"

    elif document_type == "tax":
        document_label = "Lohnsteuer"

    elif document_type == "bank":
        document_label = data.get("document_subtype") or "Bank"

    elif document_type == "housing":
        document_label = data.get("document_subtype") or "Wohnen"

    else:
        document_label = "Dokument"

    return f"{issuer} · {document_label}"
