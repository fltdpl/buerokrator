"""Tests für den PDF→Bild-Renderpfad der OCR (pypdfium2 statt Poppler).

Tesseract wird gemockt — geprüft wird, dass jede PDF-Seite als PIL-Bild in
der erwarteten Auflösung bei der OCR ankommt und die Seitentexte
zusammengesetzt werden.
"""

import pypdfium2 as pdfium
from PIL import Image

import src.ocr.ocr_service as ocr_service


def _write_pdf(path, pages=1, width=595, height=842):
    pdf = pdfium.PdfDocument.new()

    for _ in range(pages):
        pdf.new_page(width, height)

    pdf.save(path)
    pdf.close()


def test_extract_text_from_image_pdf_renders_all_pages(tmp_path, monkeypatch):
    pdf_path = tmp_path / "scan.pdf"
    _write_pdf(pdf_path, pages=3)

    seen_images = []

    def fake_ocr(image, lang):
        seen_images.append(image)
        return f"Seite {len(seen_images)}"

    monkeypatch.setattr(ocr_service, "_configure_ocr", lambda: "deu+eng")
    monkeypatch.setattr(ocr_service.pytesseract, "image_to_string", fake_ocr)

    text = ocr_service.extract_text_from_image_pdf(str(pdf_path))

    assert text == "Seite 1\nSeite 2\nSeite 3\n"
    assert all(isinstance(image, Image.Image) for image in seen_images)


def test_render_resolution_matches_200_dpi(tmp_path, monkeypatch):
    # A4-Seite: 595x842 pt (72 dpi) → bei 200 dpi ~1653x2339 px.
    pdf_path = tmp_path / "scan.pdf"
    _write_pdf(pdf_path, pages=1, width=595, height=842)

    seen_images = []

    monkeypatch.setattr(ocr_service, "_configure_ocr", lambda: "deu+eng")
    monkeypatch.setattr(
        ocr_service.pytesseract,
        "image_to_string",
        lambda image, lang: seen_images.append(image) or "",
    )

    ocr_service.extract_text_from_image_pdf(str(pdf_path))

    width, height = seen_images[0].size
    assert abs(width - 595 * 200 / 72) <= 2
    assert abs(height - 842 * 200 / 72) <= 2
