from src.classifier.document_extractor import extract_invoice
from src.ocr.ocr_service import extract_text_from_image_pdf

text = extract_text_from_image_pdf("examples/invoice/Rechnung_Zahnarzt_OCR.pdf")

result = extract_invoice(text)

print(result)
