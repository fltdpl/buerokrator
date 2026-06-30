from src.classifier.document_extractor import extract_tax

text = """
Elektronische
Lohnsteuerbescheinigung

Arbeitgeber:
TRS GmbH

Kalenderjahr:
2025
"""

result = extract_tax(text)

print(result)
