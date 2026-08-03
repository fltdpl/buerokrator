import functools
import re
from pathlib import Path

from src.core.amount_utils import normalize_amount
from src.core.document_types import (
    BANK,
    EMPLOYMENT,
    HOUSING,
    INSURANCE,
    INVOICE,
    LEGAL,
    PENSION,
    TAX,
)
from src.organizer.category_mapper import get_archive_category, get_archive_root
from src.core.logger import logger
from src.organizer.date_utils import extract_year, normalize_date, normalize_month
from src.organizer.issuer_normalizer import normalize_issuer


# Zeichen, die in EINER Pfadkomponente nichts zu suchen haben. "/" ist unter
# Linux der Separator, "\" unter Windows (das Paket ist erklärtes Ziel); die
# übrigen verbietet Windows in Dateinamen.
_FORBIDDEN_CHARS = '<>:"|?*\\/'

# Windows-Gerätenamen: eine Datei "CON.pdf" lässt sich dort nicht anlegen.
_WINDOWS_RESERVED = frozenset(
    ["CON", "PRN", "AUX", "NUL"]
    + [f"COM{i}" for i in range(1, 10)]
    + [f"LPT{i}" for i in range(1, 10)]
)

# Grenze je Pfadkomponente auf ext4 und NTFS.
_MAX_FILENAME_BYTES = 255

_FALLBACK_STEM = "dokument"


def _truncate_stem(stem: str, suffix: str) -> str:
    """Kürzt den Namensteil, bis Name + Endung ins Limit passen.

    Byteweise, nicht zeichenweise: Umlaute belegen in UTF-8 zwei Bytes, und
    das Dateisystem zählt Bytes. Geschnitten wird am Zeichen, damit kein
    halbes Multibyte-Zeichen entsteht.
    """
    budget = _MAX_FILENAME_BYTES - len(suffix.encode("utf-8"))

    while len(stem.encode("utf-8")) > budget:
        stem = stem[:-1]

    return stem


def _safe_filename(name: str) -> str:
    """Macht aus einem gebauten Namen garantiert EINE gültige Pfadkomponente.

    Zentrale Absicherung statt feldweiser Bereinigung: die Bauer setzen den
    Namen aus Modell- und Nutzerwerten zusammen (Datum, Jahr, Monat,
    Aussteller, Betreff …), und `normalize_date` reicht unparsbare Werte
    unverändert durch. Ein einziges "/" oder ".." im falschen Feld ließ die
    Archivierung sonst aus dem Archiv ausbrechen — `shutil.move` folgt dem
    Pfad, den es bekommt.

    Nach dieser Funktion gilt: kein Separator, keine unter Windows
    verbotenen Zeichen, kein führender Punkt (also kein "." oder ".." als
    Verzeichnisverweis), kein reservierter Gerätename, nie leer, nie länger
    als das Dateisystem erlaubt.
    """
    cleaned = "".join(
        "_" if char in _FORBIDDEN_CHARS or ord(char) < 32 else char for char in name
    )

    suffix = Path(cleaned).suffix
    stem = cleaned[: len(cleaned) - len(suffix)] if suffix else cleaned

    # Führende/abschließende Punkte und Leerzeichen: Windows schneidet sie
    # ohnehin ab, und ein führender Punkt macht aus dem Namen einen
    # Verzeichnisverweis bzw. eine versteckte Datei.
    stem = stem.strip(" .")
    stem = re.sub(r"_{3,}", "__", stem)

    if not stem or stem.upper() in _WINDOWS_RESERVED:
        stem = f"{_FALLBACK_STEM}_{stem}" if stem else _FALLBACK_STEM

    return _truncate_stem(stem, suffix) + suffix


def _sanitized(builder):
    """Garantiert die Zusage von _safe_filename für jeden Dateinamen-Bauer."""

    @functools.wraps(builder)
    def wrapper(*args, **kwargs):
        return _safe_filename(builder(*args, **kwargs))

    return wrapper


def get_unique_target_path(target):

    original_stem = target.stem
    suffix = target.suffix
    counter = 1

    while target.exists():
        target = target.parent / f"{original_stem}_{counter}{suffix}"

        counter += 1

    return target


def build_filename(classification, extracted_data, original_file_path):

    document_type = classification["document_type"]
    suffix = Path(original_file_path).suffix
    builders = {
        INVOICE: build_invoice_filename,
        TAX: build_tax_filename,
        INSURANCE: build_insurance_filename,
        PENSION: build_pension_filename,
        BANK: build_bank_filename,
        HOUSING: build_housing_filename,
        EMPLOYMENT: build_employment_filename,
        LEGAL: build_legal_filename,
    }

    builder = builders.get(document_type)
    if builder:
        return builder(extracted_data, suffix)

    return build_fallback_filename(extracted_data, suffix, document_type)


def rename_document(
    current_path,
    document_type,
    extracted_data,
):

    current_path = Path(current_path)

    if not current_path.exists():
        return current_path

    category = get_archive_category(document_type)

    # Jahr aus den (ggf. geänderten) Dokumentdaten ableiten, konsistent zu
    # archive_document. Vorher wurde das Jahr aus dem alten Pfad übernommen,
    # sodass umklassifizierte Dokumente im falschen Jahr-Ordner landeten.
    year = extract_year(extracted_data)

    target_folder = get_archive_root() / year / category

    target_folder.mkdir(
        parents=True,
        exist_ok=True,
    )

    classification = {
        "document_type": document_type,
    }

    new_filename = build_filename(
        classification,
        extracted_data,
        current_path.name,
    )

    target = target_folder / new_filename

    target = get_unique_target_path(target)

    logger.info(f"Umbenennen: {current_path} -> {target}")
    if current_path.resolve() == target.resolve():
        return current_path

    if not current_path.exists():
        raise FileNotFoundError(f"Datei nicht gefunden: {current_path}")

    current_path.rename(target)

    return target


def _text_value(value, default):
    """LLM-Werte defensiv zu Text machen.

    Modelle liefern gelegentlich Zahlen oder null, wo ein String erwartet
    wird — ohne Coercion crasht der Dateinamen-Bau an `.replace()`.
    """
    if value is None:
        return default

    text = str(value).strip()

    return text or default


def _clean_name(value, default):
    # Formatierung: Leerzeichen zu Unterstrichen. Die Pfadsicherheit liegt
    # NICHT hier, sondern zentral in _safe_filename — feldweise Bereinigung
    # hatte genau die Felder übersehen, die kein _clean_name durchliefen.
    return _text_value(value, default).replace(" ", "_").replace("/", "_")


def _issuer_name(value, default):
    """Aussteller normalisieren und pfadsicher machen (str-Coercion zuerst)."""
    return _clean_name(normalize_issuer(_text_value(value, default)), default)


@_sanitized
def build_fallback_filename(extracted_data, suffix, document_type):
    """Name für Typen ohne eigenen Bauer — vor allem `unknown`.

    Vorher hieß jedes solche Dokument nach seinem Typ, also durchweg
    `unknown.pdf`: in der Dateiliste nicht auseinanderzuhalten, und der
    Kollisionszähler von `get_unique_target_path` machte daraus `unknown_1`,
    `unknown_2` — Nummern statt Inhalt.

    Dieselbe Form wie bei `legal`, dem allgemeinsten der gebauten Typen:
    Datum, Aussteller, Betreff. Der Typname tritt als Betreff ein, wenn keiner
    erkannt wurde — er ist dann die einzige Aussage, die die Klassifikation
    überhaupt getroffen hat.
    """
    document_date = normalize_date(
        _text_value(extracted_data.get("document_date"), "unknown_date")
    )

    issuer = _issuer_name(extracted_data.get("issuer"), "unknown_issuer")

    subject = _clean_name(extracted_data.get("subject"), document_type)

    return f"{document_date}_{issuer}_{subject}{suffix}"


@_sanitized
def build_invoice_filename(extracted_data, suffix):

    document_date = normalize_date(
        _text_value(extracted_data.get("document_date"), "unknown_date")
    )

    issuer = _issuer_name(extracted_data.get("issuer"), "unknown_issuer")

    invoice_number = _text_value(
        extracted_data.get("invoice_number"), "unknown_invoice"
    ).replace("/", "-")

    amount = normalize_amount(extracted_data.get("amount"))

    if amount is not None:
        return f"{document_date}_{issuer}_{invoice_number}_{amount:.0f}EUR{suffix}"

    return f"{document_date}_{issuer}{suffix}"


@_sanitized
def build_tax_filename(extracted_data, suffix):

    tax_year = extracted_data.get("tax_year") or "unknown_year"
    subtype = (extracted_data.get("document_subtype") or "").lower()

    if subtype == "einkommensbescheinigung":
        # Finanzamt-Bescheinigung: jährlich, Aussteller = Finanzamt.
        issuer = _clean_name(extracted_data.get("issuer"), "Finanzamt")
        return f"{tax_year}-12_{issuer}_Einkommensbescheinigung{suffix}"

    # Standard/Default: Meldebescheinigung / Informationsschreiben.
    issuer = _clean_name(extracted_data.get("issuer"), "unknown_issuer")
    return f"{tax_year}_{issuer}_Bescheinigung{suffix}"


def _period_prefix(extracted_data):
    """Datumsteil aus dem Zeitraum (von–bis) oder None.

    Beide Daten -> "YYYY-MM-DD_bis_YYYY-MM-DD", nur Start -> "YYYY-MM-DD".
    Nach dem Startdatum sortierbar; unterscheidet Teilzeiträume.
    """
    start = extracted_data.get("period_start")
    end = extracted_data.get("period_end")

    if start and end:
        return f"{normalize_date(start)}_bis_{normalize_date(end)}"
    if start:
        return normalize_date(start)

    return None


@_sanitized
def build_employment_filename(extracted_data, suffix):

    subtype = (extracted_data.get("document_subtype") or "").lower()
    tax_year = extracted_data.get("tax_year") or "unknown_year"
    period_prefix = _period_prefix(extracted_data)

    if subtype == "gehaltsabrechnung":
        employer = _clean_name(extracted_data.get("employer"), "unknown_employer")

        if period_prefix:
            return f"{period_prefix}_{employer}_Gehaltsabrechnung{suffix}"

        # Fallback (Altbestand ohne Zeitraum): Jahr-Monat wie bisher.
        month = normalize_month(extracted_data.get("month"))
        return f"{tax_year}-{month}_{employer}_Gehaltsabrechnung{suffix}"

    if subtype == "lohnsteuerbescheinigung":
        employer = _clean_name(extracted_data.get("employer"), "unknown_employer")

        # Mit Dienstverhältnis-Zeitraum: unterscheidet Teilzeiträume eines
        # Jahres (verhindert Namenskollision mehrerer Bescheinigungen).
        if period_prefix:
            return f"{period_prefix}_{employer}_Lohnsteuerbescheinigung{suffix}"

        # Fallback: jährlich, Datum als YYYY-MM, ohne Monat auf Jahresende.
        month = normalize_month(extracted_data.get("month"))
        if month == "00":
            month = "12"
        return f"{tax_year}-{month}_{employer}_Lohnsteuerbescheinigung{suffix}"

    if subtype == "sv_meldung":
        # SV-Meldung (§ 25 DEÜV): Meldezeitraum + Arbeitgeber + Betreff.
        issuer = _issuer_name(extracted_data.get("issuer"), "unknown_issuer")
        subject = _clean_name(extracted_data.get("subject"), "SV-Meldung")
        prefix = period_prefix or normalize_date(
            _text_value(extracted_data.get("document_date"), "unknown_date")
        )
        return f"{prefix}_{issuer}_{subject}{suffix}"

    # Arbeitsvertrag / Kündigung / Zeugnis / Sonstiges: Datum + Aussteller +
    # Betreff (Freitext).
    document_date = normalize_date(
        _text_value(extracted_data.get("document_date"), "unknown_date")
    )
    issuer = _issuer_name(extracted_data.get("issuer"), "unknown_issuer")
    subject = _clean_name(extracted_data.get("subject"), subtype or "Arbeit")

    return f"{document_date}_{issuer}_{subject}{suffix}"


@_sanitized
def build_insurance_filename(extracted_data, suffix):

    document_date = normalize_date(
        _text_value(extracted_data.get("document_date"), "unknown_date")
    )
    issuer = _issuer_name(
        extracted_data.get("issuer") or extracted_data.get("insurer"),
        "unknown_issuer",
    )

    insurance_type = _clean_name(
        extracted_data.get("insurance_type"), "unknown_insurance"
    )
    policy_number = (
        _text_value(extracted_data.get("policy_number"), "unknown_policy")
        .replace(" ", "-")
        .replace("/", "-")
        .replace(".", "-")
    )

    return f"{document_date}_{issuer}_{insurance_type}_{policy_number}{suffix}"


@_sanitized
def build_pension_filename(
    extracted_data,
    suffix,
):

    document_date = normalize_date(
        _text_value(extracted_data.get("document_date"), "unknown_date")
    )

    issuer = _issuer_name(extracted_data.get("issuer"), "unknown_issuer")

    document_subtype = _clean_name(
        extracted_data.get("document_subtype"), "unknown"
    )

    policy_number = (
        _text_value(extracted_data.get("policy_number"), "unknown_policy")
        .replace(" ", "-")
        .replace("/", "-")
        .replace(".", "-")
    )

    return f"{document_date}_{issuer}_{document_subtype}_{policy_number}{suffix}"


@_sanitized
def build_bank_filename(
    extracted_data,
    suffix,
):

    document_date = normalize_date(
        _text_value(extracted_data.get("document_date"), "unknown_date")
    )

    issuer = _issuer_name(
        extracted_data.get("issuer") or extracted_data.get("bank"),
        "unknown_bank",
    )

    document_subtype = _clean_name(
        extracted_data.get("document_subtype"), "Kontoauszug"
    )

    return f"{document_date}_{issuer}_{document_subtype}{suffix}"


@_sanitized
def build_housing_filename(
    extracted_data,
    suffix,
):

    document_date = normalize_date(
        _text_value(extracted_data.get("document_date"), "unknown_date")
    )

    issuer = _issuer_name(
        extracted_data.get("issuer") or extracted_data.get("landlord"),
        "unknown_housing",
    )

    document_subtype = _clean_name(
        extracted_data.get("document_subtype"), "Wohnen"
    )

    return f"{document_date}_{issuer}_{document_subtype}{suffix}"


@_sanitized
def build_legal_filename(
    extracted_data,
    suffix,
):

    document_date = normalize_date(
        _text_value(extracted_data.get("document_date"), "unknown_date")
    )

    issuer = _issuer_name(extracted_data.get("issuer"), "unknown_issuer")

    subject = _clean_name(extracted_data.get("subject"), "Recht")

    return f"{document_date}_{issuer}_{subject}{suffix}"
