from src.database.database import open_connection
from src.database.list_documents import _DOCUMENT_FIELDS

# Gewichte für bm25 (Reihenfolge = FTS_COLUMNS in init_database.py:
# filename, document_type, extracted_data, document_text, notes).
# Treffer in Dateiname/Feldern zählen mehr als im langen OCR-Volltext.
_BM25_WEIGHTS = "5.0, 2.0, 3.0, 1.0, 2.0"

# Der Trigram-Tokenizer braucht mindestens 3 Zeichen; kürzere Begriffe
# laufen über das alte LIKE (unsortiert nach Relevanz, aber vollständig).
_MIN_FTS_LENGTH = 3

# Spaltenindex von document_text in FTS_COLUMNS (init_database.py). Die
# Fundstelle kommt bewusst NUR aus dem OCR-Volltext: Treffer in Dateiname,
# Feldern und Notiz stehen in der Liste ohnehin schon sichtbar.
_SNIPPET_COLUMN = 3

# Markierung der Fundstelle. Steuerzeichen statt "<b>", weil der Text aus
# fremden PDFs stammt: er muss in der Oberfläche escaped werden, und danach
# wäre echtes Markup im Rohtext nicht mehr von unserem zu unterscheiden.
SNIPPET_OPEN = "\x02"
SNIPPET_CLOSE = "\x03"

# Beim Trigram-Tokenizer entspricht ein Token ungefähr einem Zeichen.
_SNIPPET_TOKENS = 60


def _passage(snippet):
    """Die markierte Fundstelle im Volltext — oder None.

    `snippet()` liefert auch dann eine Passage, wenn der Begriff im Volltext
    gar nicht vorkommt (der Treffer kam aus Dateiname, Feldern oder Notiz):
    dann den Textanfang, ohne Markierung. Die wäre irreführend, denn sie
    enthält den gesuchten Begriff nicht. Die Markierung ist das einzige
    verlässliche Zeichen für einen echten Volltext-Treffer.
    """
    if not snippet or SNIPPET_OPEN not in snippet:
        return None

    return snippet


def search_documents(search_term):
    if len(search_term) < _MIN_FTS_LENGTH:
        return _search_documents_like(search_term)

    # Als Phrase in Anführungszeichen: der Suchbegriff wird wörtlich gesucht
    # (Substring-Semantik wie früher LIKE), FTS5-Query-Syntax im Nutzertext
    # (AND, OR, *, Klammern …) bleibt wirkungslos.
    quoted = '"' + search_term.replace('"', '""') + '"'

    with open_connection() as conn:
        cursor = conn.cursor()

        rows = cursor.execute(
            f"""
            SELECT {_DOCUMENT_FIELDS}, fts_snippet
            FROM documents
            JOIN (
                SELECT
                    rowid AS fts_rowid,
                    bm25(documents_fts, {_BM25_WEIGHTS}) AS fts_rank,
                    snippet(
                        documents_fts, {_SNIPPET_COLUMN}, ?, ?, '…',
                        {_SNIPPET_TOKENS}
                    ) AS fts_snippet
                FROM documents_fts
                WHERE documents_fts MATCH ?
            ) ON fts_rowid = documents.id
            ORDER BY fts_rank, documents.id DESC
            """,
            (SNIPPET_OPEN, SNIPPET_CLOSE, quoted),
        ).fetchall()

    results = []

    for row in rows:
        document = dict(row)
        document["text_snippet"] = _passage(document.pop("fts_snippet"))
        results.append(document)

    return results


def _search_documents_like(search_term):
    """Fallback für Begriffe unter drei Zeichen.

    Ohne FTS gibt es kein `snippet()`; das Ergebnis führt `text_snippet`
    trotzdem mit (leer), damit die Zeilenform beider Suchwege gleich ist.
    """
    with open_connection() as conn:
        cursor = conn.cursor()

        rows = cursor.execute(
            f"""
            SELECT {_DOCUMENT_FIELDS}
            FROM documents
            WHERE

                filename LIKE ?
                OR document_type LIKE ?
                OR extracted_data LIKE ?
                OR document_text LIKE ?
                OR notes LIKE ?

            ORDER BY id DESC
            """,
            (
                f"%{search_term}%",
                f"%{search_term}%",
                f"%{search_term}%",
                f"%{search_term}%",
                f"%{search_term}%",
            ),
        ).fetchall()

    return [dict(row, text_snippet=None) for row in rows]
