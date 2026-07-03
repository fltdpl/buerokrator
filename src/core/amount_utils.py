def normalize_amount(value):
    """Wandelt einen Betrag (LLM-Ausgabe oder Benutzereingabe) in einen float um.

    Behandelt Währungszeichen sowie deutsche (1.234,56) und englische
    (1234.56) Zahlenformate. Gibt None zurück, wenn kein Betrag erkennbar ist.
    """
    if value is None:
        return None

    if isinstance(value, (int, float)):
        return float(value)

    text = str(value).replace("€", "").replace("EUR", "").replace("eur", "")
    text = text.replace(" ", "").strip()

    if not text:
        return None

    if "," in text and "." in text:
        # Deutsches Format: Punkt = Tausender, Komma = Dezimal
        text = text.replace(".", "").replace(",", ".")

    elif "," in text:
        text = text.replace(",", ".")

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
}

# Felder, die ihr Vorzeichen behalten dürfen (negativ = Erstattung).
SIGNED_AMOUNT_FIELDS = {"settlement_amount"}


def enforce_amount_signs(data):
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
