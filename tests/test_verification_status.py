"""Der Prüfstatus gehört der Freigabe, nicht dem Speichern.

`update_document` setzte `verified = 1` fest in der UPDATE-Anweisung — damit
gab auch der Knopf „Speichern" das Dokument still frei, obwohl daneben ein
eigener Knopf „Speichern & Freigeben" steht. Der Unterschied war faktisch nur
die Weiternavigation. Freigeben ist jetzt ausschließlich Sache von
`set_document_verified`.

Alle Werte erfunden.
"""

from src.database.document_repository import insert_document, save_document
from src.database.init_database import init_database
from src.database.list_documents import get_document, list_documents
from src.database.set_document_verified import mark_document_verified
from src.database.update_document import update_document


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


def angelegtes_dokument():
    insert_document(
        filename="f.pdf",
        archive_path="archive/2020/Rechnungen/f.pdf",
        document_type="invoice",
        extracted_data={"issuer": "Musterfirma GmbH", "amount": 10.0},
    )

    return list_documents()[0]["id"]


def speichern(document_id):
    save_document(
        document_id=document_id,
        archive_path="archive/2020/Rechnungen/f.pdf",
        document_type="invoice",
        extracted_data={
            "issuer": "Musterfirma GmbH",
            "document_date": "01.01.2020",
            "amount": 20.0,
        },
    )


def test_speichern_laesst_ein_ungeprueftes_dokument_ungeprueft(tmp_path, monkeypatch):
    write_config(tmp_path)
    monkeypatch.chdir(tmp_path)
    init_database()

    document_id = angelegtes_dokument()
    speichern(document_id)

    row = get_document(document_id)

    assert row["verified"] == 0
    # Gespeichert wurde trotzdem.
    assert row["document_type"] == "invoice"


def test_speichern_laesst_ein_geprueftes_dokument_geprueft(tmp_path, monkeypatch):
    write_config(tmp_path)
    monkeypatch.chdir(tmp_path)
    init_database()

    document_id = angelegtes_dokument()
    mark_document_verified(document_id)
    speichern(document_id)

    assert get_document(document_id)["verified"] == 1


def test_update_document_ruehrt_den_pruefstatus_nicht_an(tmp_path, monkeypatch):
    # Eine Ebene tiefer abgesichert, falls save_document einmal umgebaut wird.
    write_config(tmp_path)
    monkeypatch.chdir(tmp_path)
    init_database()

    document_id = angelegtes_dokument()

    update_document(
        document_id=document_id,
        filename="f.pdf",
        archive_path="archive/2020/Rechnungen/f.pdf",
        document_type="invoice",
        extracted_data={"issuer": "Musterfirma GmbH"},
    )

    assert get_document(document_id)["verified"] == 0

    mark_document_verified(document_id)

    update_document(
        document_id=document_id,
        filename="f.pdf",
        archive_path="archive/2020/Rechnungen/f.pdf",
        document_type="invoice",
        extracted_data={"issuer": "Musterfirma GmbH"},
    )

    assert get_document(document_id)["verified"] == 1
