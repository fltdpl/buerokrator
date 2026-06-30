from src.classifier.document_extractor import extract_pension
from src.processor.document_processor import extract_text

print(" ")
pdf_path = "examples/pension/2025 Debeka Kosten Rentenversicherung Nr880012345.pdf"
print(pdf_path)
text = extract_text(pdf_path)
result = extract_pension(text)
# print(result)
print(" ")

pdf_path = "examples/pension/2026-06-14_Scan_0001.pdf"
print(pdf_path)
text = extract_text(pdf_path)
result = extract_pension(text)
# print(result)
print(" ")

pdf_path = "examples/pension/2026-06-14_Scan_0014.pdf"
print(pdf_path)
text = extract_text(pdf_path)
result = extract_pension(text)
# print(result)
print(" ")

pdf_path = "examples/pension/2026-06-14_Scan_0041.pdf"
print(pdf_path)
text = extract_text(pdf_path)
result = extract_pension(text)
# print(result)
print(" ")
