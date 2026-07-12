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
                "    employment: Arbeit",
            ]
        ),
        encoding="utf-8",
    )


def test_insert_sets_default_tax_relevance(tmp_path, monkeypatch):
    write_config(tmp_path)
    monkeypatch.chdir(tmp_path)
    init_database()

    # Gehaltsabrechnung -> Default steuerrelevant (1).
    insert_document(
        filename="lohn.pdf",
        archive_path="archive/2024/Arbeit/lohn.pdf",
        document_type="employment",
        extracted_data={"document_subtype": "gehaltsabrechnung", "employer": "ACME"},
    )
    # Arbeitsvertrag -> Default nicht steuerrelevant (0).
    insert_document(
        filename="vertrag.pdf",
        archive_path="archive/2024/Arbeit/vertrag.pdf",
        document_type="employment",
        extracted_data={"document_subtype": "arbeitsvertrag", "issuer": "ACME"},
    )

    by_name = {row["filename"]: row for row in list_documents()}

    assert by_name["lohn.pdf"]["tax_relevant"] == 1
    assert by_name["vertrag.pdf"]["tax_relevant"] == 0


def test_save_document_persists_override(tmp_path, monkeypatch):
    write_config(tmp_path)
    monkeypatch.chdir(tmp_path)
    init_database()

    insert_document(
        filename="vertrag.pdf",
        archive_path="archive/2024/Arbeit/vertrag.pdf",
        document_type="employment",
        extracted_data={"document_subtype": "arbeitsvertrag", "issuer": "ACME"},
    )
    document_id = list_documents()[0]["id"]

    # Nutzer hakt "steuerrelevant" an, obwohl der Default False wäre.
    save_document(
        document_id=document_id,
        archive_path="archive/2024/Arbeit/vertrag.pdf",
        document_type="employment",
        extracted_data={
            "document_subtype": "arbeitsvertrag",
            "issuer": "ACME",
            "document_date": "01.03.2024",
            "subject": "Abfindung",
        },
        tax_relevant=True,
    )

    assert get_document(document_id)["tax_relevant"] == 1
