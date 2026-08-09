"""Persistenz der Tags — reine Abfragen, keine Normalisierung.

Alle Werte, die hier ankommen, sind bereits normalisiert (siehe
`src/services/tag_service.py`). Diese Schicht entscheidet nichts über
Schreibweisen; sie legt an, verknüpft und liest.
"""

from datetime import datetime

from src.database.database import open_connection


def _ensure_tag(cursor, name, key):
    """Gibt die ID des Tags zurück und legt es an, falls es fehlt.

    Ein vorhandenes Tag behält seine Schreibweise: wer „Knie-OP" angelegt
    hat, soll es nicht durch ein späteres „knie-op" an einem anderen
    Dokument umbenannt bekommen. Umbenennen ist eine eigene, sichtbare
    Handlung in der Verwaltung.
    """
    row = cursor.execute(
        """
        SELECT id FROM tags WHERE key = ?
        """,
        (key,),
    ).fetchone()

    if row is not None:
        return row["id"]

    # Laufende Nummer, KEIN Farbwert: welche Palette daraus wird, weiß
    # allein das Frontend (theme.TAG_COLORS, modulo Palettenlänge). Die
    # Persistenzschicht kennt keine Farben — sonst hinge die Datenbank an
    # der Darstellung.
    vergeben = cursor.execute("SELECT COUNT(*) AS n FROM tags").fetchone()["n"]

    cursor.execute(
        """
        INSERT INTO tags (name, key, color_index, created_at)
        VALUES (?, ?, ?, ?)
        """,
        (name, key, vergeben, datetime.now().isoformat(timespec="seconds")),
    )

    return cursor.lastrowid


def set_document_tags(document_id, eintraege):
    """Setzt die Tags eines Dokuments auf genau `eintraege` [(name, key)].

    Ersetzend, nicht ergänzend: die Detailansicht schickt den vollständigen
    Stand. Ein Tag, das dabei seine letzte Zuordnung verliert, bleibt als
    Vokabel bestehen — Aufräumen ist eine bewusste Handlung in der
    Verwaltung, kein stiller Nebeneffekt des Speicherns.
    """
    with open_connection() as conn:
        cursor = conn.cursor()

        tag_ids = []

        for name, key in eintraege:
            tag_id = _ensure_tag(cursor, name, key)

            if tag_id not in tag_ids:
                tag_ids.append(tag_id)

        cursor.execute(
            """
            DELETE FROM document_tags
            WHERE document_id = ?
            """,
            (document_id,),
        )

        cursor.executemany(
            """
            INSERT INTO document_tags (document_id, tag_id)
            VALUES (?, ?)
            """,
            [(document_id, tag_id) for tag_id in tag_ids],
        )

        conn.commit()


def tags_for_document(document_id):
    with open_connection() as conn:
        rows = conn.execute(
            """
            SELECT tags.id, tags.name, tags.key, tags.color_index
            FROM document_tags
            JOIN tags ON tags.id = document_tags.tag_id
            WHERE document_tags.document_id = ?
            ORDER BY tags.key
            """,
            (document_id,),
        ).fetchall()

    return [dict(row) for row in rows]


def list_tags():
    """Das ganze Vokabular mit Nutzungszahl — Grundlage der Auswahlliste.

    Verwaiste Tags (Nutzung 0) sind ausdrücklich dabei: sie sollen weiter
    auswählbar sein und in der Verwaltung auffallen.
    """
    with open_connection() as conn:
        rows = conn.execute(
            """
            SELECT tags.id, tags.name, tags.key, tags.color_index,
                   COUNT(document_tags.document_id) AS usage
            FROM tags
            LEFT JOIN document_tags ON document_tags.tag_id = tags.id
            GROUP BY tags.id
            ORDER BY tags.key
            """
        ).fetchall()

    return [dict(row) for row in rows]


def delete_tags_of_document(cursor, document_id):
    """Zuordnungen eines Dokuments entfernen — im Löschpfad aufgerufen.

    Nimmt den Cursor entgegen, damit das Löschen des Dokuments und seiner
    Zuordnungen in derselben Transaktion liegt.
    """
    cursor.execute(
        """
        DELETE FROM document_tags
        WHERE document_id = ?
        """,
        (document_id,),
    )
