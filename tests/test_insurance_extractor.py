from src.classifier.document_extractor import extract_insurance
from src.processor.document_processor import extract_text

pdf_path = "examples/insurance/Unfall_Versicherungsschein.pdf"

text = extract_text(pdf_path)

result = extract_insurance(text)

print(result)
