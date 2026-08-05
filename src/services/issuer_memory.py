"""Aussteller-Gedächtnis: was der geprüfte Bestand über einen Anbieter weiß.

Die meisten Dokumente kommen von einem Aussteller, der im Bestand längst
vorkommt. Dieses Wissen wird hier nutzbar gemacht, und zwar OHNE Training:
kein Modell, keine Gewichte, nur Abfragen auf den geprüften Dokumenten. Eine
frische Installation ohne Bestand verhält sich damit exakt wie bisher.

Eine Verwendung, im Prüf-Workflow: `type_mismatch` meldet, wenn der erkannte
Dokumenttyp von dem abweicht, den dieser Aussteller bisher ausnahmslos
lieferte. Am Bestand gemessen deckt das rund drei Viertel der Dokumente ab —
bei ihnen würde eine Fehlklassifikation auffallen — und kostet dabei fast
keine Fehlalarme.

Es ist ein HINWEIS, nie Automatik. Der Mehrheitstyp eines Ausstellers liegt
gemessen seltener richtig als die Klassifikation selbst und darf sie deshalb
nicht überstimmen (dasselbe Muster wie beim Dubletten-Hinweis).

Bewusst NICHT hier: Vorschläge für leere Felder aus konstanten Werten des
Ausstellers. Gebaut, am Bestand gemessen und wieder entfernt — sie waren
strukturell unsichtbar, weil das einzige Feld mit genug Substanz (`employer`)
ausgerechnet bei den Subtypen leer ist, deren Formular es gar nicht führt.
Details in `docs/decisions/013_kein_trainiertes_modell.md`.

Grundlage sind ausschließlich geprüfte Dokumente (`verified = 1`): ein
Gedächtnis, das aus ungeprüften Erkennungsfehlern lernt, verfestigt sie.
"""

import json
import re
from collections import Counter

from src.database.issuer_history import list_verified_summaries
from src.database.list_documents import get_document
from src.organizer.issuer_normalizer import normalize_issuer

# Felder, die einen Aussteller tragen — gleiche Auflösung wie in Liste,
# Filter und Dubletten-Prüfung (employment nennt ihn "employer").
_ISSUER_FIELDS = ("issuer", "insurer", "employer")

# So viele geprüfte Vordokumente braucht der Plausibilitäts-Hinweis. Bei einem
# einzigen Vordokument ist „der Aussteller liefert ausnahmslos Typ X" keine
# Aussage, sondern ein Zufall.
MIN_DOCUMENTS_FOR_HINT = 2


def _compact(value):
    """Vergleichsform: ohne Leerraum, Groß-/Kleinschreibung egal."""
    return re.sub(r"\s+", "", value or "").casefold()


def _data_of(row):
    try:
        data = json.loads(row["extracted_data"])

    except Exception:
        return {}

    return data if isinstance(data, dict) else {}


def _issuer_of(data):
    """Kanonischer Aussteller eines Extraktionsergebnisses ("" wenn keiner)."""
    for field in _ISSUER_FIELDS:
        value = data.get(field)

        if isinstance(value, str) and value.strip():
            return normalize_issuer(value.strip())

    return ""


def _verified_of(issuer, exclude_id=None):
    """Geprüfte Dokumente dieses Ausstellers."""
    canonical = normalize_issuer((issuer or "").strip())

    if not canonical:
        return []

    wanted = _compact(canonical)
    found = []

    for row in list_verified_summaries():
        if row["id"] == exclude_id:
            continue

        data = _data_of(row)

        if _compact(_issuer_of(data)) != wanted:
            continue

        found.append((row, data))

    return found


def type_memory(issuer, exclude_id=None):
    """Welche Typen dieser Aussteller bisher lieferte — oder None.

    {"document_type": Mehrheitstyp, "counts": {Typ: Anzahl}, "total": Anzahl}
    """
    rows = _verified_of(issuer, exclude_id=exclude_id)

    if not rows:
        return None

    counts = Counter(row["document_type"] for row, _ in rows)

    # Bei Gleichstand alphabetisch — ein schwankender Hinweis wäre schlimmer
    # als ein konservativer.
    document_type = min(counts.items(), key=lambda item: (-item[1], item[0]))[0]

    return {
        "document_type": document_type,
        "counts": dict(counts),
        "total": sum(counts.values()),
    }


def type_mismatch(document_id):
    """Weicht der Typ dieses Dokuments von dem seines Ausstellers ab?

    {"issuer", "document_type", "expected_type", "total"} — oder None, wenn es
    nichts zu sagen gibt. Ein HINWEIS, keine Korrektur: die Klassifikation
    bleibt stehen, der Nutzer entscheidet.

    Gemeldet wird nur, wenn der Aussteller bisher AUSNAHMSLOS einen Typ
    geliefert hat. Der naheliegende Vergleich mit dem Mehrheitstyp erzeugte am
    geprüften Bestand ein Vielfaches an Meldungen — und dort ist jede davon
    ein Fehlalarm, weil geprüfte Dokumente den richtigen Typ tragen. Anbieter,
    die legitim mehrere Typen liefern (Vorsorge und Versicherung aus einem
    Haus), sollen still bleiben.
    """
    row = get_document(document_id)

    if row is None:
        return None

    data = _data_of(row)
    issuer = _issuer_of(data)

    if not issuer:
        return None

    memory = type_memory(issuer, exclude_id=document_id)

    if memory is None or memory["total"] < MIN_DOCUMENTS_FOR_HINT:
        return None

    if len(memory["counts"]) > 1:
        return None

    if memory["document_type"] == row["document_type"]:
        return None

    return {
        "issuer": issuer,
        "document_type": row["document_type"],
        "expected_type": memory["document_type"],
        "total": memory["total"],
    }
