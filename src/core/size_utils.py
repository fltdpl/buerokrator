"""Dateigrößen menschenlesbar — EINE Formatierung für die ganze App.

Bewusst hier und nicht in `frontend/layout.py` neben `format_euro`: die
Dokumentenliste formatiert Dateigrößen aus `src/services` heraus, und ein
Service darf nicht ins Frontend greifen. Zwei Formatierungen nebeneinander
wären die Alternative gewesen — dieselbe Zahl sähe dann auf dem Dashboard
anders aus als in der Liste.

Deutsches Dezimalkomma wie überall in der Oberfläche (vgl.
`layout.format_euro`, `chart.py`).
"""

_EINHEITEN = ("KB", "MB", "GB", "TB")


def format_bytes(size) -> str:
    """`1536` → `2 KB`, `1572864` → `1,5 MB`. Leerwert → `-`.

    Ganze Zahlen bis KB, darüber eine Nachkommastelle: bei Byte und Kilobyte
    trägt die Nachkommastelle keine Information, bei Megabyte schon.
    """
    if size is None:
        return "-"

    try:
        wert = float(size)

    except (TypeError, ValueError):
        return "-"

    if wert < 1024:
        return f"{int(wert)} B"

    for einheit in _EINHEITEN:
        wert /= 1024

        if wert < 1024 or einheit == _EINHEITEN[-1]:
            break

    if einheit == "KB":
        return f"{wert:.0f} {einheit}"

    return f"{wert:.1f} {einheit}".replace(".", ",")
