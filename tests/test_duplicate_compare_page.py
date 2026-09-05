"""Die Gegenüberstellung im Frontend: Werte im Hinweis, Belege nebeneinander.

Bis dahin nannte die Warnung nur die NAMEN der widersprechenden Felder, und
der Link führte von der Seite weg — verglichen wurde aus dem Gedächtnis.

Alle Werte erfunden.
"""

import pytest

from nicegui.testing import User

pytest_plugins = ["nicegui.testing.user_plugin"]


@pytest.fixture(autouse=True)
def isolated_project(tmp_path, monkeypatch):
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
                "classifier:",
                "  model: gemma3:4b",
                "  temperature: 0.0",
                "  max_input_chars: 3000",
                "ocr:",
                "  language: deu+eng",
                "  tesseract:",
                "    windows: C:/Program Files/Tesseract-OCR/tesseract.exe",
                "    linux: /usr/bin/tesseract",
                "logging:",
                "  level: INFO",
                "supported_file_types:",
                "  - .pdf",
                "archive:",
                "  category_mapping:",
                "    invoice: Rechnungen",
                "    unknown: Sonstiges",
            ]
        ),
        encoding="utf-8",
    )
    (tmp_path / ".nicegui").mkdir()
    monkeypatch.chdir(tmp_path)

    from src.database.init_database import init_database

    init_database()


def _paar():
    """Zwei Belege desselben Ausstellers, die sich nur in der Nummer trennen.

    Die Rechnungsnummern stehen bewusst NICHT im Dateinamen: sonst wuerde ein
    Test auf "RE-4471" auch dann gruen, wenn die Vergleichstabelle fehlt.
    """
    from src.database.document_repository import insert_document

    links = insert_document(
        filename="2024-03-11_Musterversand_Scan.pdf",
        archive_path="archive/2024/Rechnungen/2024-03-11_Musterversand_Scan.pdf",
        document_type="invoice",
        extracted_data={
            "issuer": "Musterversand GmbH",
            "amount": 148.90,
            "document_date": "11.03.2024",
            "invoice_number": "RE-4471",
        },
    )
    rechts = insert_document(
        filename="2024-03-11_Musterversand_Scan (1).pdf",
        archive_path="archive/2024/Rechnungen/2024-03-11_Musterversand_Scan (1).pdf",
        document_type="invoice",
        extracted_data={
            "issuer": "Musterversand GmbH",
            "amount": 148.90,
            "document_date": "11.03.2024",
            "invoice_number": "RE-4477",
        },
    )

    return links, rechts


@pytest.mark.asyncio
async def test_hinweis_zeigt_die_werte_nicht_nur_die_feldnamen(user: User):
    """Stufe 1: an der Nummer selbst entscheidet sich der Fall, nicht am Wort
    "Rechnungsnummer"."""
    links, rechts = _paar()

    await user.open(f"/dokumente/{links}")

    await user.should_see("Mögliche Dublette")
    await user.should_see("RE-4471")
    await user.should_see("RE-4477")
    await user.should_see("abweichend")


@pytest.mark.asyncio
async def test_hinweis_verlinkt_die_gegenueberstellung(user: User):
    links, rechts = _paar()

    await user.open(f"/dokumente/{links}")

    await user.should_see("nebeneinander vergleichen")


@pytest.mark.asyncio
async def test_gegenueberstellung_zeigt_beide_belege_und_den_grund(user: User):
    """Stufe 2: beide Werte, der Meldegrund und beide Dokumente auf einer Seite."""
    links, rechts = _paar()

    await user.open(f"/dokumente/{links}/vergleich/{rechts}")

    await user.should_see("Gegenüberstellung")
    await user.should_see("Gemeldet, weil:")
    await user.should_see("RE-4471")
    await user.should_see("RE-4477")
    await user.should_see("In den Papierkorb")


@pytest.mark.asyncio
async def test_gegenueberstellung_sagt_es_wenn_das_paar_nicht_gemeldet_ist(user: User):
    """Die Seite ist über die Adresszeile erreichbar — und nach einer
    Korrektur kann die Meldung entfallen sein. Dann keine Warnung vortäuschen.
    """
    from src.database.document_repository import insert_document

    links = insert_document(
        filename="a.pdf",
        archive_path="archive/2024/Rechnungen/a.pdf",
        document_type="invoice",
        extracted_data={"issuer": "Musterversand GmbH", "amount": 10.0},
    )
    rechts = insert_document(
        filename="b.pdf",
        archive_path="archive/2024/Rechnungen/b.pdf",
        document_type="invoice",
        extracted_data={"issuer": "Andere Musterfirma", "amount": 99.0},
    )

    await user.open(f"/dokumente/{links}/vergleich/{rechts}")

    await user.should_see("NICHT als Dublette gemeldet")


@pytest.mark.asyncio
async def test_fehlendes_dokument_meldet_sich_statt_zu_scheitern(user: User):
    links, _ = _paar()

    await user.open(f"/dokumente/{links}/vergleich/9999")

    await user.should_see("gibt es nicht (mehr)")
