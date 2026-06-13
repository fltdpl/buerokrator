from pathlib import Path
from time import perf_counter

from src.classifier.document_classifier import (
    classify,
)
from src.processor.document_processor import (
    extract_text,
)

INBOX_PATH = Path("inbox")


def main():

    pdf_files = sorted(INBOX_PATH.glob("*.pdf"))

    if not pdf_files:
        print("Keine PDF-Dateien in inbox gefunden.")

        return

    print()
    print("=" * 10)
    print("KLASSIFIKATIONSTEST")
    print("=" * 10)

    for pdf_file in pdf_files:
        print()
        print("-" * 10)
        print(f"Datei: {pdf_file.name}")

        try:
            startExtr = perf_counter()
            text = extract_text(str(pdf_file))
            durationExtr = perf_counter() - startExtr

            startClass = perf_counter()
            result = classify(text)
            durationClass = perf_counter() - startClass

            document_type = result.get("document_type", "unknown")

            print(f"Typ:                        {document_type}")
            print(f"Zeichen:                    {len(text)}")
            print(f"Dauer Extraktion:           {durationExtr:.2f}s")
            print(f"Dauer Klassifizierung:      {durationClass:.2f}s")

        except Exception as e:
            print(f"FEHLER: {e}")

    print()
    print("=" * 10)
    print("FERTIG")
    print("=" * 10)


if __name__ == "__main__":
    main()
