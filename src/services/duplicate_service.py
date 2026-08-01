"""Inhaltliche Dubletten: derselbe Beleg, ein anderer Scan.

Der Inhalts-Hash (`find_duplicate.find_document_by_hash`) erkennt nur
bytegleiche Dateien. Wird dieselbe Rechnung ein zweites Mal eingescannt,
unterscheiden sich die Bytes — der Beleg liegt trotzdem doppelt im Bestand.
Erkennbar ist er dann nur noch an den extrahierten Werten.

Bewusst LIVE berechnet statt beim Import gespeichert: die Werte ändern sich
im Prüf-Workflow. Eine beim Import ermittelte Warnung stünde nach der ersten
Aussteller-Korrektur falsch da — und eine richtige Warnung fehlte, wenn erst
die Korrektur die Übereinstimmung herstellt.

Der Befund ist ein HINWEIS, keine Entscheidung: hier wird nichts gelöscht und
nichts übersprungen. Der Import behandelt inhaltliche Dubletten weiterhin als
normale Dokumente.

BEKANNTE GRENZE: verglichen werden `amount`, `document_date` und
`invoice_number`. Dokumenttypen, die diese Felder nicht führen — vor allem
`employment` mit `period_start`/`period_end` und `gross_amount` —, lösen die
Warnung praktisch nie aus. Am Bestand nachgemessen: von 800 textähnlichen,
nicht gemeldeten Paaren widersprechen 754 in einem Feld (verschiedene Belege
desselben Anbieters, korrekt stumm); die übrigen 46 sind fast durchweg
employment-Dokumente, bei denen alle drei Vergleichsfelder leer sind. Eine
Erweiterung um Zeitraum + Bruttobetrag wäre der nächste Schritt — sie braucht
aber einen eigenen Fehlalarm-Test, weil sich Abrechnungen desselben
Arbeitgebers stark ähneln.
"""

import json
import re

from src.core.amount_utils import normalize_amount
from src.database.find_duplicate import list_duplicate_candidates
from src.database.list_documents import get_document
from src.organizer.date_utils import normalize_date
from src.organizer.issuer_normalizer import normalize_issuer

# Felder, die den Aussteller tragen — gleiche Auflösung wie Liste und Filter
# (employment-Dokumente nennen ihn "employer").
_ISSUER_FIELDS = ("issuer", "insurer", "employer")


def _data_of(row):
    try:
        data = json.loads(row["extracted_data"])

    except Exception:
        return {}

    return data if isinstance(data, dict) else {}


def _issuer_key(data):
    """Vergleichbarer Aussteller: Alias aufgelöst, Groß-/Kleinschreibung und
    Randleerzeichen egal. Leer, wenn kein Name erkannt wurde."""
    for field in _ISSUER_FIELDS:
        value = data.get(field)

        if isinstance(value, str) and value.strip():
            return normalize_issuer(value.strip()).casefold()

    return ""


def _amount_key(data):
    """Betrag als Zahl (None, wenn keiner erkannt wurde).

    Über `normalize_amount`, damit "1.234,56" und 1234.56 aus zwei
    verschieden erkannten Scans denselben Schlüssel ergeben.
    """
    amount = normalize_amount(data.get("amount"))

    return None if amount is None else round(amount, 2)


def _date_key(data):
    """Datum in einheitlicher Schreibweise; unparsbare Werte bleiben roh
    (dann matchen nur wörtlich gleiche). Leer, wenn kein Datum da ist."""
    value = data.get("document_date")

    if not isinstance(value, str) or not value.strip():
        return ""

    return str(normalize_date(value.strip())).casefold()


def _invoice_key(data):
    """Rechnungsnummer ohne Trennzeichen ("RE-1001" == "RE 1001").

    Nur die Rechnungsnummer, bewusst NICHT die Policennummer: dieselbe Police
    steht auf jedem Dokument eines Vertrags über Jahre hinweg — als
    Dubletten-Merkmal wäre sie eine Fehlalarm-Maschine.
    """
    value = data.get("invoice_number")

    if not isinstance(value, str):
        return ""

    return re.sub(r"[^a-z0-9]", "", value.casefold())


def _match_reason(data, other):
    """Begründung, warum die beiden denselben Beleg meinen — oder None.

    Zwei Wege, beide setzen einen übereinstimmenden Aussteller voraus:
    die Rechnungsnummer identifiziert den Beleg allein, sonst braucht es
    Betrag UND Datum. Leere Werte zählen nie als Übereinstimmung — sonst
    würde ein unerkanntes Feld den halben Bestand zusammenwerfen.
    """
    issuer = _issuer_key(data)

    if not issuer or issuer != _issuer_key(other):
        return None

    invoice_number = _invoice_key(data)

    if invoice_number and invoice_number == _invoice_key(other):
        return "gleicher Aussteller und gleiche Rechnungsnummer"

    amount = _amount_key(data)
    date = _date_key(data)

    if (
        amount is not None
        and date
        and amount == _amount_key(other)
        and date == _date_key(other)
    ):
        return "gleicher Aussteller, gleicher Betrag und gleiches Datum"

    return None


def find_content_duplicates(document_id):
    """Dokumente, die inhaltlich denselben Beleg zeigen wie `document_id`.

    Liefert Plain Data, aufsteigend nach ID:
    [{"id", "filename", "document_type", "reason"}]. Leer, wenn es das
    Dokument nicht gibt oder seine Werte für einen Vergleich nicht reichen.
    """
    row = get_document(document_id)

    if row is None:
        return []

    data = _data_of(row)
    matches = []

    for candidate in list_duplicate_candidates(document_id):
        reason = _match_reason(data, _data_of(candidate))

        if reason is None:
            continue

        matches.append(
            {
                "id": candidate["id"],
                "filename": candidate["filename"],
                "document_type": candidate["document_type"],
                "reason": reason,
            }
        )

    return matches
