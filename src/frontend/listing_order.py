"""Zuletzt angezeigte Dokument-Reihenfolge der Liste (für Vor/Zurück im Detail).

Modul-global (Ein-Nutzer-Betrieb): Die Dokumentenliste hinterlegt hier die IDs
in ihrer aktuellen (gefilterten/sortierten) Reihenfolge; die Detailansicht
blättert mit den Pfeiltasten darin. Fällt die aktuelle ID heraus (Direktaufruf
per URL), blättert das Frontend über die Standardreihenfolge.
"""

_IDS = []


def set_listing_order(ids):
    _IDS[:] = [int(i) for i in ids]


def get_listing_order():
    return list(_IDS)


def adjacent_id(order, current_id, step):
    """Nachbar-ID in `order` relativ zu current_id (step -1 zurück, +1 vor).

    Gibt None, wenn current_id fehlt oder es keinen Nachbarn in die Richtung
    gibt. `order` wird übergeben (statt global gelesen), damit die Funktion
    ohne Zustand testbar ist.
    """
    if current_id not in order:
        return None

    index = order.index(current_id) + step

    if 0 <= index < len(order):
        return order[index]

    return None
