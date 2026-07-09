"""Regelbasierte Nachbearbeitung der LLM-Extraktion von Vorsorgedokumenten.

Die Parser korrigieren nur, was aus dem Text exakt herleitbar ist (Beträge,
Bilanzen, amtlich beschriftete Felder). Alles Identifizierende — Aussteller,
Produktname, Datum — bleibt beim LLM, damit ein Formularmuster niemandem
einen falschen Anbieter ins Archiv schreibt.
"""

from src.extraction.account_statement import parse_account_statement
from src.extraction.tax_certificate import parse_tax_certificate


def refine_pension_fields(text, data):
    """Ergänzt/korrigiert LLM-Felder; unverändert, wenn kein Parser greift."""
    parsed = parse_account_statement(text) or parse_tax_certificate(text)
    if not parsed:
        return data

    return {**(data or {}), **parsed}
