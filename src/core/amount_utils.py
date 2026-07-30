import re

# Ein einzelner Trenner in Dreiergruppen ("1.234", "12,345,678") ist eine
# Tausendertrennung, kein Dezimaltrenner: Geldbeträge haben keine drei
# Nachkommastellen. Ohne diese Regel erzeugt float() still einen
# Faktor-1000-Fehler.
def _is_thousands_grouping(text: str, separator: str) -> bool:
    return bool(
        re.fullmatch(rf"-?\d{{1,3}}(\{separator}\d{{3}})+", text)
    )


def normalize_amount(value: object) -> float | None:
    """Wandelt einen Betrag (LLM-Ausgabe oder Benutzereingabe) in einen float um.

    Behandelt Währungszeichen sowie deutsche (1.234,56) und englische
    (1,234.56) Zahlenformate. Gibt None zurück, wenn kein Betrag erkennbar ist.

    Regel bei zwei verschiedenen Trennern: der HINTERE ist der Dezimaltrenner
    ("1.234,56" deutsch, "1,234.56" englisch). Das Format wird also am Text
    erkannt und nicht angenommen — ein deutsches Dokument kann sehr wohl
    englisch formatierte Beträge tragen, und das LLM gibt beide Formen aus.
    """
    if value is None:
        return None

    if isinstance(value, (int, float)):
        return float(value)

    text = str(value).replace("€", "").replace("EUR", "").replace("eur", "")
    text = text.replace(" ", "").strip()

    if not text:
        return None

    last_comma = text.rfind(",")
    last_dot = text.rfind(".")

    if last_comma >= 0 and last_dot >= 0:
        decimal, thousands = (
            (",", ".") if last_comma > last_dot else (".", ",")
        )
        text = text.replace(thousands, "").replace(decimal, ".")

    elif last_comma >= 0:
        if _is_thousands_grouping(text, ","):
            text = text.replace(",", "")

        else:
            text = text.replace(",", ".")

    elif last_dot >= 0 and _is_thousands_grouping(text, "."):
        text = text.replace(".", "")

    try:
        return float(text)

    except Exception:
        return None


# Alle bekannten Geldfelder über die Dokumenttypen hinweg.
AMOUNT_FIELD_NAMES = {
    "amount",
    "interest",
    "capital_gains_tax",
    "soli",
    "church_tax",
    "contributions_total",
    "opening_balance",
    "closing_balance",
    "gross_amount",
    "net_amount",
    "income_tax",
    "settlement_amount",
    # Sozialversicherungsbeiträge der Lohnsteuerbescheinigung (Zeilen 22–27).
    "pension_insurance_employer",
    "pension_insurance_employee",
    "health_insurance",
    "care_insurance",
    "unemployment_insurance",
    "private_health_insurance",
    # Arbeitgeberleistungen der Lohnsteuerbescheinigung (Zeilen 17/18/20).
    "commuting_allowance_taxfree",
    "commuting_allowance_flat_taxed",
    "meal_allowance_taxfree",
    # § 35a-Summen der Wohnen-Abrechnungen.
    "household_services_amount",
    "craftsman_services_amount",
}

# Felder, die ihr Vorzeichen behalten dürfen (negativ = Erstattung).
SIGNED_AMOUNT_FIELDS = {"settlement_amount"}


def enforce_amount_signs(data: dict | None) -> dict | None:
    """Speichert Geldbeträge als Beträge (Magnitude).

    Steuern/Abzüge werden dadurch unabhängig davon, ob sie versehentlich mit
    oder ohne Minus eingetragen wurden, konsistent als positiver Betrag
    behandelt. Nur explizit vorzeichenbehaftete Felder (settlement_amount)
    behalten ihr Vorzeichen.
    """
    if not isinstance(data, dict):
        return data

    for field in AMOUNT_FIELD_NAMES:
        value = data.get(field)
        if isinstance(value, (int, float)) and field not in SIGNED_AMOUNT_FIELDS:
            data[field] = abs(value)

    return data
