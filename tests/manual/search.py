import sys

from src.database.search import search_documents


def main():
    if len(sys.argv) < 2:
        print("Benutzung:")
        print("python3 -m tests.test_search Suchbegriff")

        return

    search_term = sys.argv[1]
    results = search_documents(search_term)

    print()
    print(f"{len(results)} Treffer gefunden")
    print()

    for row in results:
        filename = row[0]
        archive_path = row[1]
        document_type = row[2]

        print(f"Typ: {document_type}")
        print(f"Datei: {filename}")
        print(f"Pfad: {archive_path}")
        print("-" * 60)


if __name__ == "__main__":
    main()
