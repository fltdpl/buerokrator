import importlib


def write_test_config(tmp_path):
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "settings.yaml").write_text(
        "\n".join(
            [
                "database:",
                "  path: ./database/buerokrator.db",
            ]
        ),
        encoding="utf-8",
    )


def load_modules():
    import src.database.database as database
    import src.database.init_database as init_database
    import src.database.search as search

    for module in (database, init_database, search):
        importlib.reload(module)

    return database, search


def insert_document(database, **values):
    columns = ", ".join(values)
    placeholders = ", ".join("?" for _ in values)

    with database.open_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            f"INSERT INTO documents ({columns}) VALUES ({placeholders})",
            tuple(values.values()),
        )
        conn.commit()

        return cursor.lastrowid


def setup(tmp_path, monkeypatch):
    write_test_config(tmp_path)
    monkeypatch.chdir(tmp_path)

    return load_modules()


def test_search_finds_substring_inside_token(tmp_path, monkeypatch):
    # Vertragsnummern-Suche: Teilstring mitten im Wort muss treffen
    # (Substring-Semantik wie das frühere LIKE). Nummer erfunden.
    database, search = setup(tmp_path, monkeypatch)

    insert_document(
        database,
        filename="vertrag.pdf",
        document_text="Vertragsnummer KV9876543 Beitrag",
    )
    insert_document(database, filename="anders.pdf", document_text="ohne Nummer")

    results = search.search_documents("9876543")

    assert [row["filename"] for row in results] == ["vertrag.pdf"]


def test_search_is_case_insensitive(tmp_path, monkeypatch):
    database, search = setup(tmp_path, monkeypatch)

    insert_document(database, filename="a.pdf", document_text="Nebenkostenabrechnung")

    assert len(search.search_documents("nebenkosten")) == 1
    assert len(search.search_documents("NEBENKOSTEN")) == 1


def test_search_covers_all_indexed_columns(tmp_path, monkeypatch):
    database, search = setup(tmp_path, monkeypatch)

    insert_document(database, filename="nur_dateiname_xyzabc.pdf")
    insert_document(database, filename="b.pdf", extracted_data='{"issuer": "Musterkasse"}')
    insert_document(database, filename="c.pdf", notes="Rückfrage klären")

    assert len(search.search_documents("xyzabc")) == 1
    assert len(search.search_documents("Musterkasse")) == 1
    assert len(search.search_documents("Rückfrage")) == 1


def test_search_ranks_filename_hit_above_text_hit(tmp_path, monkeypatch):
    database, search = setup(tmp_path, monkeypatch)

    insert_document(
        database,
        filename="a.pdf",
        document_text="Der Bausparvertrag wird irgendwo im Text erwähnt.",
    )
    insert_document(database, filename="Bausparvertrag.pdf", document_text="Text")

    results = search.search_documents("Bausparvertrag")

    assert [row["filename"] for row in results] == [
        "Bausparvertrag.pdf",
        "a.pdf",
    ]


def test_search_index_follows_update_and_delete(tmp_path, monkeypatch):
    database, search = setup(tmp_path, monkeypatch)

    document_id = insert_document(
        database, filename="a.pdf", document_text="alter Inhalt"
    )

    with database.open_connection() as conn:
        conn.execute(
            "UPDATE documents SET document_text = ? WHERE id = ?",
            ("neuer Inhalt", document_id),
        )
        conn.commit()

    assert len(search.search_documents("neuer")) == 1
    assert search.search_documents("alter") == []

    with database.open_connection() as conn:
        conn.execute("DELETE FROM documents WHERE id = ?", (document_id,))
        conn.commit()

    assert search.search_documents("neuer") == []


def test_search_short_term_falls_back_to_like(tmp_path, monkeypatch):
    # Der Trigram-Tokenizer braucht 3 Zeichen — kürzere Begriffe laufen
    # über LIKE und finden trotzdem.
    database, search = setup(tmp_path, monkeypatch)

    insert_document(database, filename="a.pdf", document_text="VL-Vertrag")

    assert len(search.search_documents("VL")) == 1


def test_search_treats_fts_syntax_as_literal_text(tmp_path, monkeypatch):
    # FTS5-Query-Syntax im Suchfeld darf weder crashen noch wirken.
    database, search = setup(tmp_path, monkeypatch)

    insert_document(database, filename="a.pdf", document_text="normaler Text")

    assert search.search_documents('Miete" OR "Text') == []
    assert search.search_documents("Text AND (NOT") == []
    assert search.search_documents("norm*") == []
    assert len(search.search_documents("normaler Text")) == 1


def test_search_after_reset_database(tmp_path, monkeypatch):
    # reset verwirft auch den FTS-Index; danach keine Geister-Treffer.
    database, search = setup(tmp_path, monkeypatch)
    import src.database.reset_database as reset_database

    importlib.reload(reset_database)

    insert_document(database, filename="a.pdf", document_text="Inhalt vor Reset")

    reset_database.reset_documents_table()

    assert search.search_documents("Inhalt") == []

    insert_document(database, filename="b.pdf", document_text="Inhalt nach Reset")

    assert len(search.search_documents("Inhalt")) == 1


def test_treffer_im_volltext_liefert_die_fundstelle(tmp_path, monkeypatch):
    # Der eigentliche Nutzen: in der Liste steht, WARUM das Dokument
    # gefunden wurde — die Passage aus dem OCR-Text. Werte erfunden.
    database, search = setup(tmp_path, monkeypatch)

    insert_document(
        database,
        filename="a.pdf",
        document_text=(
            "Musterversand GmbH, Beispielstadt. Position: Wartung "
            "Heizungsanlage, Arbeitslohn 210,00 EUR. Zahlbar in 14 Tagen."
        ),
    )

    treffer = search.search_documents("Heizungsanlage")[0]
    fundstelle = treffer["text_snippet"]

    assert search.SNIPPET_OPEN + "Heizungsanlage" + search.SNIPPET_CLOSE in fundstelle
    assert "Wartung" in fundstelle


def test_treffer_nur_im_dateinamen_liefert_keine_fundstelle(tmp_path, monkeypatch):
    # snippet() gibt auch ohne Treffer im Volltext eine Passage zurück —
    # dann den Textanfang, ohne Markierung. Die wäre irreführend: sie
    # enthält den gesuchten Begriff gar nicht.
    database, search = setup(tmp_path, monkeypatch)

    insert_document(
        database,
        filename="Heizungsanlage.pdf",
        document_text="Ein Volltext ganz ohne den gesuchten Begriff.",
    )

    treffer = search.search_documents("Heizungsanlage")[0]

    assert treffer["text_snippet"] is None


def test_kurze_suche_ueber_like_hat_das_gleiche_ergebnisformat(tmp_path, monkeypatch):
    # Unter drei Zeichen läuft die Suche über LIKE, nicht über FTS — die
    # Zeilen müssen trotzdem dieselben Schlüssel haben.
    database, search = setup(tmp_path, monkeypatch)

    insert_document(database, filename="ab.pdf", document_text="ab cd")

    treffer = search.search_documents("ab")[0]

    assert treffer["text_snippet"] is None


def test_fundstelle_wird_als_html_escaped(tmp_path, monkeypatch):
    # Der Volltext stammt aus fremden PDFs. Enthält er Markup, darf es in
    # der Liste niemals als Markup ankommen — nur die Hervorhebung, die
    # die Suche selbst gesetzt hat, wird zu echtem HTML.
    from src.frontend.pages.documents import _snippet_html

    database, search = setup(tmp_path, monkeypatch)

    insert_document(
        database,
        filename="a.pdf",
        document_text="Hinweis <script>alert(1)</script> zur Heizungsanlage",
    )

    fundstelle = search.search_documents("Heizungsanlage")[0]["text_snippet"]
    ausgabe = _snippet_html(fundstelle)

    assert "<script>" not in ausgabe
    assert "&lt;script&gt;" in ausgabe
    assert "<mark>Heizungsanlage</mark>" in ausgabe


def test_ohne_fundstelle_bleibt_die_zelle_leer(tmp_path, monkeypatch):
    from src.frontend.pages.documents import _snippet_html

    assert _snippet_html(None) == ""
