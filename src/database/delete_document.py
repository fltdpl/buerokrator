from src.database.database import open_connection
from src.database.tags import delete_tags_of_document


def delete_document(document_id):

    with open_connection() as conn:
        cursor = conn.cursor()

        # Ausdrücklich, nicht per ON DELETE CASCADE: SQLite erzwingt
        # Fremdschlüssel nur mit PRAGMA foreign_keys=ON, und das setzt diese
        # Anwendung nicht. Ohne diese Zeile bliebe je gelöschtem Dokument
        # eine Zuordnungszeile stehen und verfälschte die Nutzungszahlen.
        delete_tags_of_document(cursor, document_id)

        cursor.execute(
            """
            DELETE FROM documents
            WHERE id = ?
            """,
            (document_id,),
        )

        conn.commit()
