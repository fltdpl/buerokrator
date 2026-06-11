from pathlib import Path
import sys

sys.path.append(
    str(Path(__file__).resolve().parent.parent)
)

from time import time

from src.classifier.document_classifier import (
    classify
)

#text = """
#Zahnarztpraxis Müller
#Rechnung
#Gesamtbetrag: 145,80 €
#"""

text = """
Lohnsteuerbescheinigung 2025
Arbeitgeber Muster GmbH
"""


print("Starte Klassifikation...\n")

start = time()

result = classify(text)

duration = time() - start

print("\nErgebnis:")
print(result)

print(
    f"\nDauer: {duration:.2f} Sekunden"
)