import json

from src.core.document_fields import whitelist_fields
from src.database.document_repository import insert_document, save_document
from src.database.init_database import init_database
from src.database.list_documents import get_document, list_documents


def write_config(tmp_path):
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "settings.yaml").write_text(
        "\n".join(
            [
                "paths:",
                "  archive: ./archive",
                "database:",
                "  path: ./database/buerokrator.db",
                "archive:",
                "  category_mapping:",
                "    invoice: Rechnungen",
            ]
        ),
        encoding="utf-8",
    )


def test_whitelist_fields_filters_and_passes_unknown_type():
    data = {"issuer": "X", "amount": 10, "currency": "EUR", "foo": "bar"}

    assert whitelist_fields("invoice", data) == {"issuer": "X", "amount": 10}
    # Nicht-Dict -> {}
    assert whitelist_fields("invoice", None) == {}
    # Typ ohne Schema -> unverändert (kein Datenverlust)
    assert whitelist_fields("unknown", data) == data


def test_save_document_strips_unknown_fields(tmp_path, monkeypatch):
    write_config(tmp_path)
    monkeypatch.chdir(tmp_path)

    init_database()

    # Altdaten mit Fremdfeldern (insert filtert bewusst nicht).
    insert_document(
        filename="f.pdf",
        archive_path="archive/2020/Rechnungen/f.pdf",
        document_type="invoice",
        extracted_data={"issuer": "Alt", "amount": 10, "currency": "EUR"},
    )

    document_id = list_documents()[0]["id"]

    # Bearbeiten/Speichern: Datei existiert nicht -> rename_document gibt den
    # Pfad unverändert zurück; entscheidend ist die Filterung von extracted_data.
    save_document(
        document_id=document_id,
        archive_path="archive/2020/Rechnungen/f.pdf",
        document_type="invoice",
        extracted_data={
            "issuer": "Neu",
            "document_date": "01.01.2020",
            "invoice_number": "1",
            "amount": 20,
            "currency": "EUR",
            "customer_number": "C-123",
        },
    )

    stored = json.loads(get_document(document_id)["extracted_data"])

    assert set(stored.keys()) == {
        "issuer",
        "document_date",
        "invoice_number",
        "amount",
    }
    assert stored["issuer"] == "Neu"


def test_whitelist_strips_string_values():
    # Ein Leerzeichen am Ende ("31.12.2019 ") machte Datumsfelder
    # unparsebar — mit kaputten Dateinamen als Folge.
    from src.core.document_fields import whitelist_fields

    data = whitelist_fields(
        "employment",
        {
            "document_subtype": "sv_meldung",
            "issuer": "Muster GmbH ",
            "period_end": "31.12.2023 ",
            "subject": " Jahresmeldung",
        },
    )

    assert data["issuer"] == "Muster GmbH"
    assert data["period_end"] == "31.12.2023"
    assert data["subject"] == "Jahresmeldung"
