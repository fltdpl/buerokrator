import csv
import json
from io import StringIO

from src.database.export_csv import export_documents_csv


def test_export_documents_csv_uses_named_columns():
    rows = [
        {
            "id": 7,
            "filename": "2026-03-11_Amazon_RE-123_42EUR.pdf",
            "archive_path": "archive/2026/Rechnungen/2026-03-11_Amazon_RE-123_42EUR.pdf",
            "document_type": "invoice",
            "extracted_data": json.dumps(
                {
                    "document_date": "11.03.2026",
                    "issuer": "Amazon",
                    "amount": 42.5,
                    "invoice_number": "RE-123",
                    "policy_number": "",
                }
            ),
            "verified": 0,
            "created_at": "2026-07-01T10:00:00",
            "document_text": "OCR text",
            "notes": "notes",
        }
    ]

    csv_data = export_documents_csv(rows)
    parsed_rows = list(csv.reader(StringIO(csv_data), delimiter=";"))

    assert parsed_rows[0] == [
        "filename",
        "archive_path",
        "document_type",
        "document_date",
        "issuer",
        "insurance_type",
        "amount",
        "invoice_number",
        "policy_number",
    ]
    assert parsed_rows[1] == [
        "2026-03-11_Amazon_RE-123_42EUR.pdf",
        "archive/2026/Rechnungen/2026-03-11_Amazon_RE-123_42EUR.pdf",
        "invoice",
        "11.03.2026",
        "Amazon",
        "",
        "42.5",
        "RE-123",
        "",
    ]
