from src.ocr.ocr_service import extract_text_from_image_pdf
from src.classifier.document_extractor import extract_invoice


text = extract_text_from_image_pdf(
    "examples/Rechnung_Zahnarzt_OCR.pdf"
)

result = extract_invoice(
    text
)

print(result)