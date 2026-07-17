from src.database.database import open_connection
from src.database.list_documents import _DOCUMENT_FIELDS

# Gewichte für bm25 (Reihenfolge = FTS_COLUMNS in init_database.py:
# filename, document_type, extracted_data, document_text, notes).
# Treffer in Dateiname/Feldern zählen mehr als im langen OCR-Volltext.
_BM25_WEIGHTS = "5.0, 2.0, 3.0, 1.0, 2.0"

# Der Trigram-Tokenizer braucht mindestens 3 Zeichen; kürzere Begriffe
# laufen über das alte LIKE (unsortiert nach Relevanz, aber vollständig).
_MIN_FTS_LENGTH = 3


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
            SELECT {_DOCUMENT_FIELDS}
            FROM documents
            JOIN (
                SELECT
                    rowid AS fts_rowid,
                    bm25(documents_fts, {_BM25_WEIGHTS}) AS fts_rank
                FROM documents_fts
                WHERE documents_fts MATCH ?
            ) ON fts_rowid = documents.id
            ORDER BY fts_rank, documents.id DESC
            """,
            (quoted,),
        ).fetchall()

    return [dict(row) for row in rows]


def _search_documents_like(search_term):
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

    return [dict(row) for row in rows]
