import json
import shutil
from pathlib import Path

import streamlit as st

from src.core.amount_utils import normalize_amount
from src.core.document_display import (
    get_document_display_name,
)
from src.core.document_types import (
    DOCUMENT_TYPES,
    DOCUMENT_TYPE_LABELS,
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
from src.database.list_documents import get_next_unverified_id
from src.database.set_document_verified import (
    set_document_verified,
)


def _amount_input_value(amount):
    """Betrag für ein Textfeld aufbereiten: None/leer -> "" statt "None"."""
    if amount is None or amount == "":
        return ""

    return str(amount)


def _close_detail():
    """Schließt die Detailansicht, indem der Query-Parameter entfernt wird."""
    if "doc" in st.query_params:
        del st.query_params["doc"]


def _static_pdf_url(pdf_path, document_id):
    """Kopiert das PDF nach ./static/ und gibt eine lokale URL zurück.

    Streamlit liefert Dateien aus ./static/ unter app/static/ aus. Das umgeht
    das Größenlimit von base64-Data-URIs, sodass auch große PDFs (mehrere MB)
    im Viewer angezeigt werden. Kopiert wird nur, wenn die Kopie fehlt oder
    veraltet ist.
    """
    source = Path(pdf_path)
    target_dir = Path("static") / "pdf"
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / f"{document_id}.pdf"

    if not target.exists() or target.stat().st_mtime < source.stat().st_mtime:
        shutil.copy2(source, target)

    version = int(source.stat().st_mtime)

    return f"app/static/pdf/{document_id}.pdf?v={version}"


def _render_pdf(pdf_path, document_id, height=800):
    """Zeigt das PDF über Static Serving in einem iframe an."""
    if not pdf_path.exists():
        st.warning("PDF-Datei nicht gefunden.")
        return

    pdf_url = _static_pdf_url(pdf_path, document_id)

    st.markdown(
        f"""
        <iframe
            src="{pdf_url}"
            width="100%"
            height="{height}"
            type="application/pdf">
        </iframe>
        """,
        unsafe_allow_html=True,
    )


def _goto_next_unverified(current_id):
    """Springt zum nächsten ungeprüften Dokument oder zurück zur Übersicht."""
    next_id = get_next_unverified_id(exclude_id=current_id)

    if next_id is not None:
        st.query_params["doc"] = str(next_id)

    else:
        st.session_state["flash"] = "Alle Dokumente sind geprüft 🎉"
        _close_detail()


LABELS = {
    "issuer": "Aussteller",
    "document_date": "Datum",
    "amount": "Betrag",
    "invoice_number": "Rechnungsnummer",
    "insurer": "Versicherer",
    "insurance_type": "Versicherungsart",
    "policy_number": "Versicherungsnummer",
    "tax_year": "Steuerjahr",
    "month": "Monat",
    "employer": "Arbeitgeber",
    "product_name": "Produkt",
    "document_subtype": "Unterart",
    "description": "Art der Bescheinigung",
    "gross_amount": "Bruttolohn",
    "income_tax": "Lohn-/Einkommensteuer",
    "soli": "Solidaritätszuschlag",
    "church_tax": "Kirchensteuer",
    "net_amount": "Nettolohn",
    "settlement_amount": "Abrechnungsbetrag",
    "interest": "Guthabenszinsen",
    "capital_gains_tax": "Kapitalertragssteuer",
    "contributions_total": "Beiträge (Jahressumme)",
    "opening_balance": "Saldovortrag",
    "closing_balance": "Endsaldo",
}

TAX_SUBTYPE_LABELS = {
    "lohnsteuerbescheinigung": "Lohnsteuerbescheinigung (jährlich)",
    "gehaltsabrechnung": "Gehaltsabrechnung (monatlich)",
    "einkommensbescheinigung": "Einkommensbescheinigung (Finanzamt)",
    "bescheinigung": "Bescheinigung / Sonstiges",
}

PENSION_SUBTYPE_LABELS = {
    "contract": "Vertrag",
    "annual_statement": "Jahresmitteilung",
    "cost_statement": "Kostenmitteilung",
    "surrender_value_table": "Rückkaufswerte",
    "pension_information": "Renteninformation",
    "bauspar_jahresauszug": "Bauspar-Jahresauszug",
    "steuerbescheinigung": "Steuerbescheinigung",
}


def _subtype_selectbox(label, options, current, key, format_func):
    """Selectbox, die einen unbekannten Bestandswert erhält statt ihn zu überschreiben."""
    if current and current not in options:
        options = [current, *options]

    return st.selectbox(
        label,
        options,
        index=options.index(current) if current in options else 0,
        format_func=format_func,
        key=key,
    )


def display_document(
    row,
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

                    st.session_state["flash"] = "Dokument gelöscht"

                    _close_detail()

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
    type_label = DOCUMENT_TYPE_LABELS.get(document_type, document_type)

    st.caption(f"{type_label} · {status_text}")

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

            st.session_state["flash"] = "Notiz gespeichert"

            st.rerun()

        st.markdown("---")

        _render_pdf(pdf_path, document_id)

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
        form_col, pdf_col = st.columns([1, 1], gap="medium")

        with pdf_col:
            _render_pdf(pdf_path, document_id, height=900)

        with form_col:
            document_type = st.selectbox(
                "Dokumenttyp",
                DOCUMENT_TYPES,
                index=DOCUMENT_TYPES.index(normalize_document_type(document_type)),
                key=f"document_type_{document_id}",
            )

            updated_data = dict(data)

            # Aussteller/Datum sind für Steuerdokumente nicht relevant (die haben
            # eigene Felder je Unterart) und werden dort ausgeblendet.
            if document_type != TAX:
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

                document_subtype = _subtype_selectbox(
                    "Unterart",
                    list(PENSION_SUBTYPE_LABELS.keys()),
                    data.get("document_subtype", ""),
                    key=f"subtype_{document_id}",
                    format_func=lambda value: PENSION_SUBTYPE_LABELS.get(value, value),
                )

                updated_data["product_name"] = product_name
                updated_data["policy_number"] = policy_number
                updated_data["document_subtype"] = document_subtype

                capital_fields = {
                    "bauspar_jahresauszug": (
                        ("interest", "Guthabenszinsen"),
                        ("contributions_total", "Beiträge (Jahressumme)"),
                        ("opening_balance", "Saldovortrag"),
                        ("closing_balance", "Endsaldo"),
                    ),
                    "steuerbescheinigung": (
                        ("interest", "Kapitalerträge"),
                        ("capital_gains_tax", "Kapitalertragssteuer"),
                        ("soli", "Solidaritätszuschlag"),
                        ("church_tax", "Kirchensteuer"),
                    ),
                }

                if document_subtype in capital_fields:
                    # Kapitalertragsfelder statt generischem Jahresbeitrag.
                    for field, label in capital_fields[document_subtype]:
                        value = st.text_input(
                            label,
                            value=_amount_input_value(data.get(field)),
                            key=f"{field}_{document_id}",
                        )
                        updated_data[field] = normalize_amount(value)

                else:
                    amount = st.text_input(
                        "Betrag (Jahresbeitrag)",
                        value=_amount_input_value(data.get("amount")),
                        key=f"amount_{document_id}",
                    )
                    updated_data["amount"] = normalize_amount(amount)

            elif document_type == TAX:
                subtype_options = [
                    "lohnsteuerbescheinigung",
                    "gehaltsabrechnung",
                    "einkommensbescheinigung",
                    "bescheinigung",
                ]
                current_subtype = data.get("document_subtype", "")

                document_subtype = st.selectbox(
                    "Unterart",
                    subtype_options,
                    format_func=lambda value: TAX_SUBTYPE_LABELS.get(value, value),
                    index=subtype_options.index(current_subtype)
                    if current_subtype in subtype_options
                    else 0,
                    key=f"tax_subtype_{document_id}",
                )

                updated_data["document_subtype"] = document_subtype

                tax_year = st.text_input(
                    "Steuerjahr",
                    value=data.get("tax_year", ""),
                    key=f"tax_year_{document_id}",
                )
                updated_data["tax_year"] = tax_year

                if document_subtype == "einkommensbescheinigung":
                    # Finanzamt-Bescheinigung
                    finanzamt = st.text_input(
                        "Finanzamt",
                        value=data.get("issuer", ""),
                        key=f"tax_issuer_{document_id}",
                    )

                    income_tax = st.text_input(
                        "Einkommensteuer",
                        value=_amount_input_value(data.get("income_tax")),
                        key=f"income_tax_{document_id}",
                    )

                    soli = st.text_input(
                        "Solidaritätszuschlag",
                        value=_amount_input_value(data.get("soli")),
                        key=f"soli_{document_id}",
                    )

                    settlement_amount = st.text_input(
                        "Abrechnungsbetrag (Erstattung negativ)",
                        value=_amount_input_value(data.get("settlement_amount")),
                        key=f"settlement_{document_id}",
                    )

                    updated_data["issuer"] = finanzamt
                    updated_data["income_tax"] = normalize_amount(income_tax)
                    updated_data["soli"] = normalize_amount(soli)
                    updated_data["settlement_amount"] = normalize_amount(settlement_amount)

                elif document_subtype == "bescheinigung":
                    # Meldebescheinigung / Informationsschreiben: keine Beträge.
                    issuer = st.text_input(
                        "Aussteller",
                        value=data.get("issuer", ""),
                        key=f"tax_issuer_{document_id}",
                    )
                    description = st.text_input(
                        "Art der Bescheinigung",
                        value=data.get("description", ""),
                        key=f"description_{document_id}",
                    )
                    updated_data["issuer"] = issuer
                    updated_data["description"] = description

                else:
                    employer = st.text_input(
                        "Arbeitgeber",
                        value=data.get("employer", ""),
                        key=f"employer_{document_id}",
                    )
                    updated_data["employer"] = employer

                    gross_amount = st.text_input(
                        "Bruttolohn",
                        value=_amount_input_value(data.get("gross_amount")),
                        key=f"gross_{document_id}",
                    )
                    updated_data["gross_amount"] = normalize_amount(gross_amount)

                    if document_subtype == "gehaltsabrechnung":
                        month = st.text_input(
                            "Monat",
                            value=data.get("month", ""),
                            key=f"month_{document_id}",
                        )

                        net_amount = st.text_input(
                            "Nettolohn",
                            value=_amount_input_value(data.get("net_amount")),
                            key=f"net_{document_id}",
                        )

                        updated_data["month"] = month
                        updated_data["net_amount"] = normalize_amount(net_amount)

                    else:  # lohnsteuerbescheinigung
                        income_tax = st.text_input(
                            "Lohnsteuer",
                            value=_amount_input_value(data.get("income_tax")),
                            key=f"income_tax_{document_id}",
                        )

                        soli = st.text_input(
                            "Solidaritätszuschlag",
                            value=_amount_input_value(data.get("soli")),
                            key=f"soli_{document_id}",
                        )

                        church_tax = st.text_input(
                            "Kirchensteuer",
                            value=_amount_input_value(data.get("church_tax")),
                            key=f"church_tax_{document_id}",
                        )

                        updated_data["income_tax"] = normalize_amount(income_tax)
                        updated_data["soli"] = normalize_amount(soli)
                        updated_data["church_tax"] = normalize_amount(church_tax)

            def _save():
                save_document(
                    document_id=document_id,
                    archive_path=archive_path,
                    document_type=document_type,
                    extracted_data=updated_data,
                    notes=notes,
                )

            save_col, verify_col = st.columns(2)

            with save_col:
                if st.button(
                    "💾 Speichern",
                    key=f"save_{document_id}",
                    width="stretch",
                ):
                    _save()

                    st.session_state["flash"] = "Dokument aktualisiert"

                    st.rerun()

            with verify_col:
                # Kern des Prüf-Workflows: speichern, freigeben und direkt
                # zum nächsten ungeprüften Dokument springen.
                if st.button(
                    "✅ Speichern & Freigeben",
                    key=f"save_verify_{document_id}",
                    type="primary",
                    width="stretch",
                ):
                    _save()
                    set_document_verified(document_id, 1)

                    st.session_state["flash"] = "Gespeichert und freigegeben"
                    _goto_next_unverified(document_id)

                    st.rerun()

