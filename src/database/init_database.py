from src.database.database import get_connection


def init_database():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT,
            archive_path TEXT,
            document_type TEXT,
            extracted_data TEXT,
            created_at TEXT,
            verified INTEGER DEFAULT 0
        )
        """
    )

    conn.commit()
    conn.close()


if __name__ == "__main__":
    init_database()

    print("Datenbank initialisiert.")
