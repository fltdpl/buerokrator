from src.ocr.ocr_service import (
    extract_text_from_image_pdf
)


print("OCR-Test gestartet...\n")

text = extract_text_from_image_pdf(
    "examples/Rechnung_Zahnarzt_OCR.pdf"
)

print(
    f"{len(text)} Zeichen erkannt\n"
)

print(text[:1000])