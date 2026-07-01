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
