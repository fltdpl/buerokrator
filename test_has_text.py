from src.ocr.pdf_reader import has_text

result = has_text(
    #"examples/Beitragsquittung_2025.pdf"
    "examples/Rechnung_Zahnarzt_OCR.pdf"
)

print(result)