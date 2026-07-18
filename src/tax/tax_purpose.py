"""Steuerlicher Zweck eines Beleg-Dokuments (DB-Spalte tax_purpose).

Vom Nutzer beim Prüfen gesetzt (nie vom LLM): kennzeichnet Belege, deren
Betrag in eine Belegsummen-Position der Steuererklärung einfließt —
Werbungskosten (Anlage N) oder Krankheitskosten (Anlage Außergewöhnliche
Belastungen). NULL = kein steuerlicher Zweck.

Bewusst NICHT abgedeckt: angabenbasierte Posten der Erklärung
(Entfernungspauschale, Homeoffice-Tage, anteilige Telefonkosten …) — die
entstehen aus Nutzerangaben, nicht aus Dokumenten (docs/05_Steuerlogik.md).
"""

WERBUNGSKOSTEN = "werbungskosten"
KRANKHEITSKOSTEN = "krankheitskosten"

TAX_PURPOSE_LABELS = {
    WERBUNGSKOSTEN: "Werbungskosten (Anlage N)",
    KRANKHEITSKOSTEN: "Krankheitskosten (agB)",
}
