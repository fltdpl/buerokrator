import json

from src.database.document_repository import insert_document
from src.database.init_database import init_database
from src.database.list_documents import list_documents
from src.services.document_service import (
    available_years,
    build_table_rows,
    filter_documents,
    move_document_to_trash,
    parse_document_row,
)


def write_config(tmp_path):
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "settings.yaml").write_text(
        "\n".join(
            [
                "paths:",
                "  inbox: ./inbox",
                "  archive: ./archive",
                "  exports: ./exports",
                "database:",
                "  path: ./database/buerokrator.db",
            ]
        ),
        encoding="utf-8",
    )


def make_row(
    document_id,
    document_type,
    year,
    data,
    verified=0,
    filename=None,
):
    filename = filename or f"{year}-01-01_dok.pdf"

    return {
        "id": document_id,
        "filename": filename,
        "archive_path": f"archive/{year}/Kategorie/{filename}",
        "document_type": document_type,
        "extracted_data": json.dumps(data),
        "verified": verified,
        "created_at": f"{year}-01-01T00:00:00",
        "document_text": "text",
        "notes": "",
        "tax_relevant": None,
    }


def test_move_to_trash_keeps_file_and_removes_db_row(tmp_path, monkeypatch):
    write_config(tmp_path)
    monkeypatch.chdir(tmp_path)

    init_database()

    folder = tmp_path / "archive" / "2024" / "Rechnungen"
    folder.mkdir(parents=True)
    pdf = folder / "rechnung.pdf"
    pdf.write_bytes(b"original")

    document_id = insert_document(
        "rechnung.pdf",
        "archive/2024/Rechnungen/rechnung.pdf",
        "invoice",
        {"amount": 10},
    )

    trashed = move_document_to_trash(document_id)

    # Datei ist NICHT vernichtet, sondern im Papierkorb.
    assert not pdf.exists()
    assert trashed.exists()
    assert trashed.resolve().parent == tmp_path / "trash"
    assert trashed.read_bytes() == b"original"

    # DB-Eintrag ist weg.
    assert list_documents() == []


def test_move_to_trash_avoids_name_collisions(tmp_path, monkeypatch):
    write_config(tmp_path)
    monkeypatch.chdir(tmp_path)

    init_database()

    folder = tmp_path / "archive" / "2024" / "Rechnungen"
    folder.mkdir(parents=True)

    trash = tmp_path / "trash"
    trash.mkdir()
    (trash / "doppelt.pdf").write_bytes(b"alt")

    (folder / "doppelt.pdf").write_bytes(b"neu")
    document_id = insert_document(
        "doppelt.pdf",
        "archive/2024/Rechnungen/doppelt.pdf",
        "invoice",
        {},
    )

    trashed = move_document_to_trash(document_id)

    # Vorhandene Papierkorb-Datei bleibt unangetastet.
    assert (trash / "doppelt.pdf").read_bytes() == b"alt"
    assert trashed.name != "doppelt.pdf"
    assert trashed.read_bytes() == b"neu"


def test_move_to_trash_unknown_id_returns_none(tmp_path, monkeypatch):
    write_config(tmp_path)
    monkeypatch.chdir(tmp_path)

    init_database()

    assert move_document_to_trash(999) is None


def test_filter_documents_combined():
    docs = [
        make_row(1, "invoice", 2023, {"issuer": "Amazon"}, verified=1),
        make_row(2, "invoice", 2024, {"issuer": "Telekom"}, verified=0),
        make_row(3, "insurance", 2024, {"insurer": "Debeka"}, verified=1),
    ]

    assert [r["id"] for r in filter_documents(docs, document_type="invoice")] == [1, 2]
    assert [r["id"] for r in filter_documents(docs, verified=True)] == [1, 3]
    assert [r["id"] for r in filter_documents(docs, from_year=2024)] == [2, 3]
    # Vertauschte Grenzen werden korrigiert.
    assert [r["id"] for r in filter_documents(docs, from_year=2024, to_year=2023)] == [1, 2, 3]
    # Aussteller-Filter findet auch insurer.
    assert [r["id"] for r in filter_documents(docs, issuer="debeka")] == [3]
    assert [r["id"] for r in filter_documents(docs, filename="2023")] == [1]


def test_available_years_and_parse_row():
    docs = [
        make_row(1, "invoice", 2023, {"amount": 5}),
        make_row(2, "bank", 2020, {}),
    ]

    assert available_years(docs) == [2020, 2023]

    parsed = parse_document_row(docs[0])
    assert parsed["id"] == 1
    assert parsed["data"] == {"amount": 5}
    assert parsed["verified"] is False


def test_build_table_rows_contains_display_fields():
    rows = build_table_rows(
        [make_row(1, "invoice", 2023, {"issuer": "Amazon", "amount": 42.5}, verified=1)]
    )

    assert rows[0]["id"] == 1
    assert rows[0]["verified"] is True
    assert rows[0]["year"] == 2023
    assert rows[0]["issuer"] == "Amazon"
    assert rows[0]["amount"] == 42.5
    assert rows[0]["created_at"] == "01.01.2023"
    # Datei existiert nicht -> Größe "-" statt Exception.
    assert rows[0]["file_size"] == "-"


def test_build_table_rows_uses_employer_as_issuer():
    # Lohnsteuer/Gehalt legen den Arbeitgeber in "employer" ab, nicht "issuer".
    rows = build_table_rows(
        [
            make_row(
                2,
                "employment",
                2024,
                {"document_subtype": "gehaltsabrechnung", "employer": "ACME AG"},
            )
        ]
    )

    assert rows[0]["issuer"] == "ACME AG"
