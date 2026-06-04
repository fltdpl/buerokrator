from src.classifier.document_classifier import classify

sample_text = """
Zahnarztpraxis Müller

Rechnung

Gesamtbetrag: 145,80 €
"""

result = classify(sample_text)

print(result)