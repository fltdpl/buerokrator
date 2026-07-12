"""Steuerrelevanz eines Dokuments (framework-frei, testbar).

Steuerrelevant = "dieses Dokument gehört in die Steuererklärung" — entweder
als Einkommen (Lohnsteuerbescheinigung) oder als absetzbarer Aufwand
(Vorsorge, Kapitalerträge). Das ist bewusst breiter als "absetzbar"
(`tax_summary.document_deductibility`), das nur Abzugsposten meint.

Seit die steuerrelevanten Dokumente über mehrere Lebensbereiche verstreut
sind (Arbeit, Vorsorge, Versicherung), ist die Relevanz nicht mehr 1:1 am
Dokumenttyp ablesbar. Deshalb ein pro Dokument gespeichertes Flag mit einem
aus Typ/Subtyp abgeleiteten Default, den der Nutzer beim Prüfen überstimmen
kann.
"""

from src.core.document_types import EMPLOYMENT, INSURANCE, PENSION, TAX


def default_tax_relevance(document_type, data):
    """Abgeleiteter Default für die Steuerrelevanz (bool).

    Bewusst grob; der Nutzer korrigiert Einzelfälle im Prüf-Formular.
    """
    data = data if isinstance(data, dict) else {}
    subtype = data.get("document_subtype")

    if document_type == EMPLOYMENT:
        # Lohn-/Gehaltsdokumente sind Einkommensnachweise; Vertrag/Kündigung/
        # Zeugnis in der Regel nicht steuerrelevant.
        return subtype in ("lohnsteuerbescheinigung", "gehaltsabrechnung")

    if document_type == TAX:
        # Finanzamt-Dokumente sind relevant; reine Melde-/Infobescheinigungen
        # nicht.
        return subtype != "bescheinigung"

    if document_type == PENSION:
        # Nur die Steuerbescheinigung (Kapitalerträge) ist automatisch
        # relevant; Verträge/Standmitteilungen überstimmt der Nutzer bei Bedarf.
        return subtype == "steuerbescheinigung"

    if document_type == INSURANCE:
        # Absetzbare Vorsorge (Kranken/Pflege/Haftpflicht …) ist relevant,
        # reine Sachversicherungen nicht. Wiederverwendung der bestehenden
        # (getesteten) Logik; lazy import, um Import-Zyklen zu vermeiden.
        from src.tax.tax_summary import DEDUCTIBLE, document_deductibility

        return document_deductibility(INSURANCE, data) == DEDUCTIBLE

    return False


def resolve_tax_relevance(document_type, data, stored):
    """Effektive Steuerrelevanz: gespeicherter Wert, sonst der Default.

    stored ist der DB-Spaltenwert (0/1/None); None = nie gesetzt (Altbestand
    oder frisch), dann greift der abgeleitete Default.
    """
    if stored is None:
        return default_tax_relevance(document_type, data)

    return bool(stored)
