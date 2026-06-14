import json

import streamlit as st

LABELS = {
    "issuer": "Aussteller",
    "document_date": "Datum",
    "amount": "Betrag",
    "invoice_number": "Rechnungsnummer",
    "insurer": "Versicherer",
    "insurance_type": "Versicherungsart",
    "policy_number": "Versicherungsnummer",
    "tax_year": "Steuerjahr",
    "employer": "Arbeitgeber",
}


def display_metadata(extracted_data):

    try:
        data = json.loads(extracted_data)

    except Exception:
        st.write(extracted_data)

        return

    for key, value in data.items():
        label = LABELS.get(key, key)
        st.write(f"**{label}:** {value}")
