import base64
from pathlib import Path

import streamlit as st

from src.organizer.filename_builder import (
    build_filename,
)
from src.processor.document_processor import (
    analyze_document,
    archive_analyzed_document,
)


def render_import_page():
    st.title("📥 Dokument importieren")
    uploaded_file = st.file_uploader(
        "PDF auswählen",
        type=["pdf"],
    )

    if uploaded_file:
        if st.button("Importieren und analysieren"):
            target = Path("inbox") / uploaded_file.name
            with open(
                target,
                "wb",
            ) as f:
                f.write(uploaded_file.getbuffer())

            result = analyze_document(str(target))

            st.session_state["analysis_result"] = result

        if "analysis_result" in st.session_state:
            result = st.session_state["analysis_result"]
            pdf_path = Path("inbox") / uploaded_file.name
            classification = result["classification"]
            extracted_data = result["extracted_data"]

            st.success("Dokument analysiert")
            st.subheader("Klassifikation")

            print(classification["document_type"])

            document_type = st.selectbox(
                "Dokumenttyp",
                [
                    "invoice",
                    "insurance",
                    "pension",
                    "tax",
                    "unknown",
                ],
                index=[
                    "invoice",
                    "insurance",
                    "pension",
                    "tax",
                    "unknown",
                ].index(
                    classification.get(
                        "document_type",
                        "unknown",
                    )
                ),
            )

            left_col, right_col = st.columns([1, 2])

            with left_col:
                st.subheader("Metadaten")
                edited_data = dict(extracted_data)
                issuer = st.text_input(
                    "Aussteller",
                    value=extracted_data.get(
                        "issuer",
                        "",
                    ),
                )
                document_date = st.text_input(
                    "Dokumentdatum",
                    value=extracted_data.get(
                        "document_date",
                        "",
                    ),
                )
                edited_data["issuer"] = issuer
                edited_data["document_date"] = document_date

                if document_type == "invoice":
                    invoice_number = st.text_input(
                        "Rechnungsnummer",
                        value=extracted_data.get(
                            "invoice_number",
                            "",
                        ),
                    )

                    amount = st.text_input(
                        "Betrag",
                        value=str(
                            extracted_data.get(
                                "amount",
                                "",
                            )
                        ),
                    )

                    edited_data["invoice_number"] = invoice_number
                    edited_data["amount"] = amount

                elif document_type == "insurance":
                    policy_number = st.text_input(
                        "Versicherungsnummer",
                        value=extracted_data.get(
                            "policy_number",
                            "",
                        ),
                    )

                    insurance_type = st.text_input(
                        "Versicherungsart",
                        value=extracted_data.get(
                            "insurance_type",
                            "",
                        ),
                    )

                    edited_data["policy_number"] = policy_number
                    edited_data["insurance_type"] = insurance_type

                elif document_type == "pension":
                    policy_number = st.text_input(
                        "Vertragsnummer",
                        value=extracted_data.get(
                            "policy_number",
                            "",
                        ),
                    )

                    document_subtype = st.selectbox(
                        "Untertyp",
                        [
                            "contract",
                            "annual_statement",
                            "cost_statement",
                            "surrender_value_table",
                            "pension_information",
                            "unknown",
                        ],
                    )

                    edited_data["policy_number"] = policy_number
                    edited_data["document_subtype"] = document_subtype

                st.subheader("Vorschau")
                st.json(edited_data)

                preview_filename = build_filename(
                    {
                        "document_type": document_type,
                    },
                    edited_data,
                    uploaded_file.name,
                )

                st.subheader("Dateiname")
                st.code(preview_filename)

            with right_col:
                st.subheader("PDF Vorschau")

                if pdf_path.exists():
                    with open(
                        pdf_path,
                        "rb",
                    ) as pdf_file:
                        pdf_bytes = pdf_file.read()

                    base64_pdf = base64.b64encode(pdf_bytes).decode("utf-8")

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

            if st.button("📦 Archivieren"):
                classification["document_type"] = document_type
                archive_analyzed_document(
                    str(Path("inbox") / uploaded_file.name),
                    classification,
                    edited_data,
                )
                st.success("Dokument archiviert")
                del st.session_state["analysis_result"]

                st.rerun()
