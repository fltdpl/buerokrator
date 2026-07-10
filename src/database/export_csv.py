import csv
import json
from io import StringIO


def export_documents_csv(rows):
    output = StringIO()
    writer = csv.writer(output, delimiter=";")
    writer.writerow(
        [
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
    )

    for row in rows:
        filename = row["filename"]
        archive_path = row["archive_path"]
        document_type = row["document_type"]

        try:
            data = json.loads(row["extracted_data"])

        except Exception:
            data = {}

        issuer = data.get("issuer") or data.get("insurer") or ""
        insurance_type = data.get("insurance_type", "")

        if isinstance(insurance_type, list):
            insurance_type = ", ".join(insurance_type)

        writer.writerow(
            [
                filename,
                archive_path,
                document_type,
                data.get("document_date", ""),
                issuer,
                insurance_type,
                data.get("amount", ""),
                data.get("invoice_number", ""),
                data.get("policy_number", ""),
            ]
        )

    return output.getvalue()
