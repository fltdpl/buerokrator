from src.database.database import get_connection

conn = get_connection()
cursor = conn.cursor()
rows = cursor.execute(
    """
    SELECT
        filename,
        document_type
    FROM documents
    """
).fetchall()

for row in rows:
    print(row)

conn.close()
