"""Verwaltung der PDF-Kopien für das Static Serving (static/pdf/<id>.pdf).

Der Viewer kopiert Archiv-PDFs nach static/pdf, damit Streamlit sie ausliefern
kann (siehe document_renderer._static_pdf_url). Ohne Aufräumen sammeln sich
dort Kopien gelöschter Dokumente — dieses Modul entfernt sie wieder.
"""

from pathlib import Path

STATIC_PDF_DIR = Path("static") / "pdf"


def remove_cached_pdf(document_id, base_dir=STATIC_PDF_DIR):
    """Entfernt die Static-Kopie eines Dokuments (z. B. nach dem Löschen)."""
    target = Path(base_dir) / f"{document_id}.pdf"

    try:
        target.unlink(missing_ok=True)

    except OSError:
        pass


def cleanup_pdf_cache(valid_ids, base_dir=STATIC_PDF_DIR):
    """Entfernt verwaiste Kopien, deren Dokument nicht mehr in der DB ist.

    Nicht dem Schema <id>.pdf entsprechende Dateien werden ebenfalls entfernt —
    in dieses Verzeichnis schreibt nur der Viewer. Gibt die Anzahl der
    gelöschten Dateien zurück.
    """
    base = Path(base_dir)

    if not base.is_dir():
        return 0

    valid = {int(document_id) for document_id in valid_ids}
    removed = 0

    for path in base.iterdir():
        if not path.is_file():
            continue

        keep = (
            path.suffix == ".pdf"
            and path.stem.isdigit()
            and int(path.stem) in valid
        )

        if keep:
            continue

        try:
            path.unlink()
            removed += 1

        except OSError:
            pass

    return removed
