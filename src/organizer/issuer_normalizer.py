"""Aussteller-Aliase: Schreibweisen auf einen kanonischen Namen vereinheitlichen.

Die Zuordnung liegt NICHT im Code, sondern in einer nutzerpflegbaren Datei
im App-Home (`config/aussteller_aliase.yaml`) — Anbieternamen sind
Nutzerdaten und gehören nicht ins (öffentliche) Repository. Ohne Datei
passiert nichts; gepflegt wird sie im Einstellungs-Tab „Aliase" (Editor
mit Validierung, `ensure_aliases_file()` legt die kommentierte Vorlage an)
oder extern im Texteditor.

Format der Datei (kanonischer Name → Liste der Schreibweisen; ein
Stern am Ende matcht als Präfix):

    Musterkasse:
      - Musterkasse Lebensversicherungsverein a. G.
      - "Musterkasse *"

Angewendet wird die Zuordnung an zwei Stellen: beim Dateinamen-Bau
(filename_builder) und auf die gespeicherten Namensfelder jeder Analyse
(document_extractor → `apply_issuer_aliases`), damit neue Importe direkt
den kanonischen Namen tragen. Bestandsdokumente vereinheitlicht weiterhin
die Bulk-Aktion „Aussteller vereinheitlichen".
"""

import yaml

from src.core.app_home import get_app_home
from src.core.logger import logger

# Felder, die einen Aussteller-/Anbieternamen tragen können.
NAME_FIELDS = ("issuer", "employer", "insurer")

_TEMPLATE = """\
# Aussteller-Aliase — vereinheitlicht Schreibweisen desselben Ausstellers.
#
# Aufbau: kanonischer Name, darunter die Schreibweisen, die beim Import
# (Dateiname UND gespeicherter Aussteller) darauf abgebildet werden.
# Ein Stern am Ende matcht als Präfix. Änderungen wirken ohne Neustart.
#
# Beispiel (entfernen und eigene Einträge anlegen):
#
# Musterkasse:
#   - Musterkasse Lebensversicherungsverein a. G.
#   - "Musterkasse *"
# Musterbank AG:
#   - MB Musterbank Aktiengesellschaft
#
# Diese Datei enthält persönliche Anbieternamen und bleibt lokal
# (im Entwickler-Modus gitignored).
"""

# Cache je (Pfad, mtime, Größe): Nutzer-Änderungen wirken ohne Neustart,
# aber ein Stapel-Import parst die Datei nicht pro Dokument neu.
_cache = {"key": None, "value": ({}, ())}


def aliases_path():
    return get_app_home() / "config" / "aussteller_aliase.yaml"


def ensure_aliases_file():
    """Legt die kommentierte Vorlage an, falls die Datei fehlt."""
    path = aliases_path()

    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(_TEMPLATE, encoding="utf-8")

    return path


def parse_aliases_text(text):
    """Parst den Dateiinhalt: (exakte Zuordnung, Präfix-Zuordnungen).

    Wirft ValueError mit verständlicher Meldung — auch der Editor in den
    Einstellungen validiert hierüber, bevor er speichert.
    """
    try:
        parsed = yaml.safe_load(text) or {}

    except yaml.YAMLError as error:
        raise ValueError(f"kein gültiges YAML: {error}") from error

    if not isinstance(parsed, dict):
        raise ValueError(
            "erwartet ist ein Mapping: kanonischer Name -> Liste der "
            "Schreibweisen"
        )

    exact = {}
    prefixes = []

    for canonical, aliases in parsed.items():
        if aliases is None:
            continue

        if isinstance(aliases, str):
            aliases = [aliases]

        if not isinstance(aliases, list):
            raise ValueError(
                f"'{canonical}': erwartet ist eine Liste von Schreibweisen"
            )

        for alias in aliases:
            alias = str(alias).strip()

            if alias.endswith("*"):
                prefixes.append((alias[:-1].rstrip(), str(canonical)))

            elif alias:
                exact[alias] = str(canonical)

    return exact, tuple(prefixes)


def load_aliases():
    """Liest die Alias-Datei: (exakte Zuordnung, Präfix-Zuordnungen).

    Fehlende oder kaputte Datei ergibt leere Zuordnungen — ein Import darf
    an einem YAML-Tippfehler nie scheitern (Warnung im Log genügt).
    """
    path = aliases_path()

    try:
        stat = path.stat()

    except OSError:
        return {}, ()

    key = (str(path), stat.st_mtime_ns, stat.st_size)

    if _cache["key"] == key:
        return _cache["value"]

    try:
        value = parse_aliases_text(path.read_text(encoding="utf-8"))

    except Exception as error:
        logger.warning(f"Aussteller-Aliase unlesbar ({path}): {error}")
        return {}, ()

    _cache["key"] = key
    _cache["value"] = value

    return _cache["value"]


def normalize_issuer(issuer):
    """Kanonischer Name laut Alias-Datei; unbekannte Namen unverändert."""
    if not isinstance(issuer, str):
        return issuer

    exact, prefixes = load_aliases()

    if issuer in exact:
        return exact[issuer]

    for prefix, canonical in prefixes:
        if prefix and issuer.startswith(prefix):
            return canonical

    return issuer


def apply_issuer_aliases(data):
    """Normalisiert die Namensfelder eines Extraktionsergebnisses."""
    if not isinstance(data, dict):
        return data

    for field in NAME_FIELDS:
        value = data.get(field)

        if isinstance(value, str):
            normalized = normalize_issuer(value)

            if normalized != value:
                data[field] = normalized

    return data
