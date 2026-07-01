import base64
import json
from pathlib import Path

import streamlit as st

from src.core.amount_utils import normalize_amount
from src.core.document_display import (
    get_document_display_name,
)
from src.core.document_types import (
    DOCUMENT_TYPES,
    INSURANCE,
    INVOICE,
    PENSION,
    TAX,
    normalize_document_type,
)
from src.database.delete_document import (
    delete_document,
)
from src.database.document_repository import save_document, update_notes
from src.database.set_document_verified import (
    set_document_verified,
)

def _amount_input_value(amount):
    """Betrag für ein Textfeld aufbereiten: None/leer -> "" statt "None"."""
    if amount is None or amount == "":
        return ""

    return str(amount)


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


def display_document(
    row,
    show_back_button=False,
):

    document_id = row[0]
    filename = row[1]
    archive_path = row[2]
    document_type = row[3]
    extracted_data = row[4]
    verified = row[5]
    document_text = row[7] if len(row) > 7 else ""
    notes = row[8] if len(row) > 8 else ""

    try:
        data = json.loads(extracted_data)

    except Exception:
        data = {}

    pdf_path = Path(archive_path)

    if show_back_button:
        if st.button(
            "← Zurück",
            key=f"back_{document_id}",
        ):
            st.session_state["document_view"] = "list"

            st.rerun()

    with st.popover("☰ Optionen"):
        if pdf_path.exists():
            with open(
                pdf_path,
                "rb",
            ) as file:
                st.download_button(
                    "📥 Download",
                    data=file,
                    file_name=filename,
                    key=f"download_top_{document_id}",
                )

        if verified == 0:
            if st.button(
                "✅ Freigeben",
                key=f"verify_top_{document_id}",
            ):
                set_document_verified(
                    document_id,
                    1,
                )

                st.rerun()

        else:
            if st.button(
                "↩️ Widerrufen",
                key=f"unverify_top_{document_id}",
            ):
                set_document_verified(
                    document_id,
                    0,
                )

                st.rerun()

        if st.button(
            "🗑 Löschen",
            key=f"delete_{document_id}",
        ):
            st.session_state[f"confirm_delete_{document_id}"] = True

        if st.session_state.get(
            f"confirm_delete_{document_id}",
            False,
        ):
            st.warning("Dokument wirklich löschen?")
            col_yes, col_no = st.columns(2)

            with col_yes:
                if st.button(
                    "Ja löschen",
                    key=f"delete_yes_{document_id}",
                ):
                    try:
                        if pdf_path.exists():
                            pdf_path.unlink()

                    except Exception:
                        pass

                    delete_document(document_id)

                    st.session_state.pop(
                        f"confirm_delete_{document_id}",
                        None,
                    )

                    st.session_state["document_view"] = "list"

                    st.rerun()

            with col_no:
                if st.button(
                    "Abbrechen",
                    key=f"delete_no_{document_id}",
                ):
                    st.session_state.pop(
                        f"confirm_delete_{document_id}",
                        None,
                    )

                    st.rerun()

    st.markdown("---")

    display_name = get_document_display_name(
        document_type,
        data,
    )

    st.subheader(display_name)

    status_text = "🟢 Geprüft" if verified else "🟡 Ungeprüft"

    st.caption(f"{document_type} · {status_text}")

    st.markdown("")

    tab_info, tab_content, tab_edit = st.tabs(
        [
            "Info",
            "Inhalt",
            "Bearbeiten",
        ]
    )

    # --------------------------------------------------
    # INFO
    # --------------------------------------------------

    with tab_info:
        st.write(f"**Pfad:** {archive_path}")

        for key, value in data.items():
            label = LABELS.get(
                key,
                key,
            )

            st.write(f"**{label}:** {value}")

        st.markdown("---")

        notes = st.text_area(
            "📝 Notizen",
            value=notes,
            height=120,
            key=f"notes_{document_id}",
        )

        if st.button(
            "💾 Notiz speichern",
            key=f"save_notes_{document_id}",
        ):
            update_notes(
                document_id,
                notes,
            )

            st.success("Notiz gespeichert")

            st.rerun()

    # --------------------------------------------------
    # INHALT
    # --------------------------------------------------

    with tab_content:
        if document_text:
            st.text_area(
                "Dokumentinhalt",
                value=document_text,
                height=400,
                disabled=True,
            )

        else:
            st.info("Kein Dokumentinhalt gespeichert.")

    # --------------------------------------------------
    # BEARBEITEN
    # --------------------------------------------------

    with tab_edit:
        document_type = st.selectbox(
            "Dokumenttyp",
            DOCUMENT_TYPES,
            index=DOCUMENT_TYPES.index(normalize_document_type(document_type)),
            key=f"document_type_{document_id}",
        )

        issuer = st.text_input(
            "Aussteller",
            value=data.get(
                "issuer",
                "",
            ),
            key=f"issuer_{document_id}",
        )

        document_date = st.text_input(
            "Datum",
            value=data.get(
                "document_date",
                "",
            ),
            key=f"date_{document_id}",
        )

        updated_data = dict(data)

        updated_data["issuer"] = issuer
        updated_data["document_date"] = document_date

        if document_type == INVOICE:
            invoice_number = st.text_input(
                "Rechnungsnummer",
                value=data.get(
                    "invoice_number",
                    "",
                ),
                key=f"invoice_{document_id}",
            )

            amount = st.text_input(
                "Betrag",
                value=_amount_input_value(data.get("amount")),
                key=f"amount_{document_id}",
            )

            updated_data["invoice_number"] = invoice_number
            updated_data["amount"] = normalize_amount(amount)

        elif document_type == INSURANCE:
            policy_number = st.text_input(
                "Versicherungsnummer",
                value=data.get(
                    "policy_number",
                    "",
                ),
                key=f"policy_{document_id}",
            )

            insurance_type = st.text_input(
                "Versicherungsart",
                value=data.get(
                    "insurance_type",
                    "",
                ),
                key=f"insurance_type_{document_id}",
            )

            amount = st.text_input(
                "Betrag (Jahresbeitrag)",
                value=_amount_input_value(data.get("amount")),
                key=f"amount_{document_id}",
            )

            updated_data["policy_number"] = policy_number
            updated_data["insurance_type"] = insurance_type
            updated_data["amount"] = normalize_amount(amount)

        elif document_type == PENSION:
            product_name = st.text_input(
                "Produkt",
                value=data.get(
                    "product_name",
                    "",
                ),
                key=f"product_{document_id}",
            )

            policy_number = st.text_input(
                "Vertragsnummer",
                value=data.get(
                    "policy_number",
                    "",
                ),
                key=f"policy_{document_id}",
            )

            document_subtype = st.text_input(
                "Dokumenttyp",
                value=data.get(
                    "document_subtype",
                    "",
                ),
                key=f"subtype_{document_id}",
            )

            amount = st.text_input(
                "Betrag (Jahresbeitrag)",
                value=_amount_input_value(data.get("amount")),
                key=f"amount_{document_id}",
            )

            updated_data["product_name"] = product_name
            updated_data["policy_number"] = policy_number
            updated_data["document_subtype"] = document_subtype
            updated_data["amount"] = normalize_amount(amount)

        elif document_type == TAX:
            employer = st.text_input(
                "Arbeitgeber",
                value=data.get(
                    "employer",
                    "",
                ),
                key=f"employer_{document_id}",
            )

            tax_year = st.text_input(
                "Steuerjahr",
                value=data.get(
                    "tax_year",
                    "",
                ),
                key=f"tax_year_{document_id}",
            )

            updated_data["employer"] = employer
            updated_data["tax_year"] = tax_year

        if st.button(
            "💾 Änderungen übernehmen",
            key=f"save_{document_id}",
        ):
            save_document(
                document_id=document_id,
                archive_path=archive_path,
                document_type=document_type,
                extracted_data=updated_data,
                notes=notes,
            )

            st.success("Dokument aktualisiert")

            st.rerun()

    st.markdown("---")

    st.subheader("PDF")

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
