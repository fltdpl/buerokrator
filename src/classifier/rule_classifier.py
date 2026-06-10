def classify(text):

    text = text.lower()

    if "lohnsteuerbescheinigung" in text:
        return {"document_type": "Steuern"}
    
    if "einkommensteuer" in text:
        return {"document_type": "Steuern"}

    if "zahnarzt" in text:
        return {"document_type": "Gesundheit"}

    if "versicherung" in text:
        return {"document_type": "Versicherungen"}

    if "bauspar" in text:
        return {"document_type": "Vorsorge"}

    if "nebenkostenabrechnung" in text:
        return {"document_type": "Wohnen"}

    return {"document_type": "Sonstiges"}






