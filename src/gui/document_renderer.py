import base64
import json
from pathlib import Path

import streamlit as st

from src.database.rename_document import (
    rename_document,
)
from src.database.set_document_verified import (
    set_document_verified,
)
from src.database.update_document import (
    update_document,
)

DISPLAY_NAMES = {
    "invoice": "Rechnungen",
    "insurance": "Versicherungen",
    "pension": "Vorsorge",
    "tax": "Steuern",
    "unknown": "Sonstiges",
}

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
    "product_name": "Produkt",
    "document_subtype": "Dokumenttyp",
}


def display_document(row):

    document_id = row[0]
    filename = row[1]
    archive_path = row[2]
    document_type = row[3]
    extracted_data = row[4]
    verified = row[5]

    try:
        data = json.loads(extracted_data)

    except Exception:
        data = {}

    status_icon = "🟢" if verified else "🟡"

    title = (
        f"{status_icon} {DISPLAY_NAMES.get(document_type, document_type)} - {filename}"
    )

    with st.expander(title):
        left_col, right_col = st.columns([1, 2])

        pdf_path = Path(archive_path)

        with left_col:
            st.write(f"**Pfad:** {archive_path}")

            st.markdown("---")

            edit_mode = st.toggle(
                "✏️ Bearbeiten",
                key=f"edit_{document_id}",
            )

            if edit_mode:
                issuer = st.text_input(
                    "Aussteller",
                    value=data.get("issuer", ""),
                    key=f"issuer_{document_id}",
                )

                document_date = st.text_input(
                    "Datum",
                    value=data.get("document_date", ""),
                    key=f"date_{document_id}",
                )

                updated_data = dict(data)

                updated_data["issuer"] = issuer
                updated_data["document_date"] = document_date

                if document_type == "invoice":
                    invoice_number = st.text_input(
                        "Rechnungsnummer",
                        value=data.get("invoice_number", ""),
                        key=f"invoice_{document_id}",
                    )

                    amount = st.text_input(
                        "Betrag",
                        value=str(data.get("amount", "")),
                        key=f"amount_{document_id}",
                    )

                    updated_data["invoice_number"] = invoice_number
                    updated_data["amount"] = amount

                elif document_type == "insurance":
                    policy_number = st.text_input(
                        "Versicherungsnummer",
                        value=data.get("policy_number", ""),
                        key=f"policy_{document_id}",
                    )

                    insurance_type = st.text_input(
                        "Versicherungsart",
                        value=data.get("insurance_type", ""),
                        key=f"insurance_type_{document_id}",
                    )

                    updated_data["policy_number"] = policy_number
                    updated_data["insurance_type"] = insurance_type

                elif document_type == "pension":
                    product_name = st.text_input(
                        "Produkt",
                        value=data.get("product_name", ""),
                        key=f"product_{document_id}",
                    )

                    policy_number = st.text_input(
                        "Vertragsnummer",
                        value=data.get("policy_number", ""),
                        key=f"policy_{document_id}",
                    )

                    document_subtype = st.text_input(
                        "Dokumenttyp",
                        value=data.get("document_subtype", ""),
                        key=f"subtype_{document_id}",
                    )

                    updated_data["product_name"] = product_name
                    updated_data["policy_number"] = policy_number
                    updated_data["document_subtype"] = document_subtype

                elif document_type == "tax":
                    employer = st.text_input(
                        "Arbeitgeber",
                        value=data.get("employer", ""),
                        key=f"employer_{document_id}",
                    )

                    tax_year = st.text_input(
                        "Steuerjahr",
                        value=data.get("tax_year", ""),
                        key=f"tax_year_{document_id}",
                    )

                    updated_data["employer"] = employer
                    updated_data["tax_year"] = tax_year

                if st.button(
                    "💾 Änderungen übernehmen",
                    key=f"save_{document_id}",
                ):
                    new_path = rename_document(
                        archive_path,
                        document_type,
                        updated_data,
                    )

                    update_document(
                        document_id=document_id,
                        filename=new_path.name,
                        archive_path=str(new_path),
                        document_type=document_type,
                        extracted_data=updated_data,
                    )

                    st.success("Dokument aktualisiert")

                    st.rerun()

            else:
                for key, value in data.items():
                    label = LABELS.get(
                        key,
                        key,
                    )

                    st.write(f"**{label}:** {value}")

            if pdf_path.exists():
                with open(pdf_path, "rb") as file:
                    st.download_button(
                        "📄 PDF herunterladen",
                        data=file,
                        file_name=filename,
                        key=f"download_{filename}",
                    )

            if verified == 0:
                if st.button(
                    "✅ Freigeben",
                    key=f"verify_{document_id}",
                ):
                    set_document_verified(
                        document_id,
                        1,
                    )

                    st.rerun()

            else:
                if st.button(
                    "↩️ Freigabe zurücknehmen",
                    key=f"unverify_{document_id}",
                ):
                    set_document_verified(
                        document_id,
                        0,
                    )

                    st.rerun()

        with right_col:
            if pdf_path.exists():
                with open(
                    pdf_path,
                    "rb",
                ) as pdf_file:
                    base64_pdf = base64.b64encode(pdf_file.read()).decode("utf-8")

                pdf_display = f"""
                <iframe
                    src="data:application/pdf;base64,{base64_pdf}"
                    width="100%"
                    height="1200"
                    type="application/pdf">
                </iframe>
                """

                st.markdown(
                    pdf_display,
                    unsafe_allow_html=True,
                )

            else:
                st.warning("PDF-Datei nicht gefunden.")
