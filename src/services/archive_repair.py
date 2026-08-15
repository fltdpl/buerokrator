"""Archivpfade wieder an das aktuelle Archiv binden.

Seit Schema v7 steht `archive_path` relativ zum App-Home und übersteht einen
Ortswechsel von selbst. Diese Fläche bleibt trotzdem nötig: für Bestände aus
älteren Fassungen, die noch absolute Pfade tragen, und für alles, was der
Umzug nicht heilt — eine Sicherung, deren Dateien anders liegen als zur
Sicherungszeit. Zeigt eine Zeile ins Leere, meldet die Detailansicht
"PDF-Datei nicht gefunden", während alle übrigen Werte richtig aussehen.

**Repariert wird in die Speicherform**, also relativ (siehe `_speicherform`).
Ein absolut zurückgeschriebener Pfad nähme dem Bestand genau die
Eigenschaft, die ihn den nächsten Ortswechsel überleben lässt.

Die Bindung läuft über die **Struktur unterhalb des Archivs**, nicht über
den alten Präfix: `archive_document` legt jede Datei als
`<archiv>/<jahr>/<kategorie>/<datei>` ab, also genügen die letzten drei
Segmente, um dieselbe Datei am neuen Ort zu finden. Das funktioniert auch
dann, wenn der Archivordner anders heißt als zur Sicherungszeit.

**Geraten wird nie.** Findet sich die Datei am neuen Ort nicht, bleibt die
Zeile unverändert und wird als ungelöst gemeldet — ein geratener Pfad wäre
schlimmer als der alte, weil die Zeile heil aussähe und doch ins Leere
zeigte. Aus demselben Grund brechen Kollisionen ab: zwei Dokumente, die auf
dieselbe Datei zeigen, wären ein stiller Verlust.

Verwandt, aber getrennt: `profile_port._rewrite_archive_paths` setzt beim
Umzug ein BEKANNTES Präfix um. Hier ist der alte Ort unbekannt.
"""

import os
import sqlite3
from datetime import datetime
from pathlib import Path

from src.core.app_home import get_app_home
from src.core.logger import logger

# <archiv>/<jahr>/<kategorie>/<datei> — siehe document_processor.archive_document.
ARCHIV_TIEFE = 3


def _kandidat(pfad, archiv):
    """Wo dieselbe Datei im aktuellen Archiv läge — None, wenn unbestimmbar."""
    teile = Path(pfad).parts[-ARCHIV_TIEFE:]

    if len(teile) < ARCHIV_TIEFE:
        return None

    # Pfadsicherheit wie beim Dateinamenbau: nichts, was aus dem Archiv
    # hinausführt. Die Segmente stammen aus der Datenbank, nicht aus der
    # Verzeichnisstruktur.
    if any(teil in ("..", "/", "") for teil in teile):
        return None

    return archiv.joinpath(*teile)


def _aufgeloest(pfad, basis):
    """Der gespeicherte Wert als absoluter Pfad — relativ gilt gegen die Basis.

    Dieselbe Auflösung wie `app_home.resolve_archive_path`, nur gegen die
    übergebene Basis statt gegen das globale App-Home.
    """
    gespeichert = Path(pfad)

    if gespeichert.is_absolute():
        return gespeichert

    return basis / gespeichert


def _neuer_pfad(pfad, archiv, basis):
    """Der Pfad, unter dem die Datei tatsächlich liegt — None, wenn nirgends.

    Zuerst das aktuelle Archiv: es ist die verlässliche Bindung. Erst danach
    der gespeicherte Wert, gegen die Basis aufgelöst.
    """
    kandidat = _kandidat(pfad, archiv)

    if kandidat is not None and kandidat.exists():
        return kandidat

    gespeichert = _aufgeloest(pfad, basis)

    if gespeichert.exists():
        return gespeichert

    return None


def _speicherform(pfad, basis):
    """Wie der Pfad in der Spalte stehen soll: relativ zur Basis, sonst absolut.

    Dieselbe Regel wie `app_home.store_archive_path`, aber gegen die
    ÜBERGEBENE Basis — dieses Modul arbeitet bewusst an einer beliebigen
    Datenbankdatei (Trockenlauf, Wiederherstellung, fremdes Profil) und darf
    nicht am globalen App-Home hängen.

    Ohne das schriebe jede Reparatur die Pfade wieder absolut und nähme dem
    Bestand genau die Eigenschaft, die ihn den nächsten Ortswechsel
    überleben lässt.
    """
    try:
        return str(Path(pfad).relative_to(basis))

    except ValueError:
        return str(pfad)


def _lies_pfade(db_path):
    conn = sqlite3.connect(db_path)

    try:
        return conn.execute(
            "SELECT id, archive_path FROM documents ORDER BY id"
        ).fetchall()

    except sqlite3.Error as error:
        raise RuntimeError(
            f"{db_path} enthält keine lesbare Tabelle 'documents': {error}"
        ) from error

    finally:
        conn.close()


def _plane(db_path, archiv, basis):
    """Was zu tun wäre — ohne zu schreiben. Trockenlauf und Reparatur teilen ihn."""
    archiv = Path(archiv)
    basis = Path(basis) if basis is not None else get_app_home()

    bericht = {
        "gesamt": 0,
        "in_ordnung": 0,
        "ohne_pfad": 0,
        "ungeloest": 0,
        "ungeloeste_ids": [],
        "kollisionen": 0,
    }
    aenderungen = {}

    for document_id, pfad in _lies_pfade(db_path):
        bericht["gesamt"] += 1

        if not pfad:
            bericht["ohne_pfad"] += 1
            continue

        neu = _neuer_pfad(pfad, archiv, basis)

        if neu is None:
            bericht["ungeloest"] += 1
            bericht["ungeloeste_ids"].append(document_id)
            continue

        # Zeigt der gespeicherte Wert schon auf genau diese Datei, ist die
        # Zeile heil — gleich ob absolut oder relativ notiert. Nur die
        # SCHREIBFORM zu vergleichen wäre falsch: ein Bestand aus einer
        # älteren Fassung (durchweg absolute Pfade) fiele dann komplett als
        # "repariert" an, obwohl keine einzige Datei verloren ist. Die
        # Umstellung auf die Speicherform erledigt die Migration beim Start.
        if _aufgeloest(pfad, basis) == neu:
            bericht["in_ordnung"] += 1
            continue

        aenderungen[document_id] = _speicherform(neu, basis)

    # Kollisionen fliegen komplett raus: welche der beiden Zeilen die Datei
    # meint, ist von hier aus nicht entscheidbar.
    belegt = {}

    for document_id, ziel in aenderungen.items():
        belegt.setdefault(ziel, []).append(document_id)

    for ziel, ids in belegt.items():
        if len(ids) > 1:
            bericht["kollisionen"] += len(ids)

            for document_id in ids:
                del aenderungen[document_id]

    return bericht, aenderungen


def pruefe_archivpfade(db_path, archiv, basis=None):
    """Trockenlauf: meldet, wie viele Zeilen reparierbar sind."""
    bericht, aenderungen = _plane(db_path, archiv, basis)
    bericht["reparierbar"] = len(aenderungen)

    return bericht


def _sichere(db_path):
    """Kopie neben die Datenbank, wie vor einer Migration."""
    db_path = Path(db_path)
    ziel = db_path.with_name(
        f"pre_pfadreparatur_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
    )

    quelle = sqlite3.connect(db_path)

    try:
        sicherung = sqlite3.connect(ziel)

        try:
            quelle.backup(sicherung)

        finally:
            sicherung.close()

    finally:
        quelle.close()

    # Wie die Haupt-DB: OCR-Volltexte, nur für den Besitzer lesbar.
    try:
        os.chmod(ziel, 0o600)

    except OSError:
        pass

    return ziel


def repariere_archivpfade(db_path, archiv, basis=None, sichern=True):
    """Bindet auffindbare Dateien neu an; gibt einen Bericht zurück.

    `sichern=False` nur dort, wo der alte Stand ohnehin schon beiseiteliegt
    (Wiederherstellung) — sonst entstünde eine zweite Kopie derselben
    Datenbank.
    """
    bericht, aenderungen = _plane(db_path, archiv, basis)
    bericht["repariert"] = len(aenderungen)
    bericht["sicherung"] = None

    if not aenderungen:
        return bericht

    if sichern:
        bericht["sicherung"] = str(_sichere(db_path))

    conn = sqlite3.connect(db_path)

    try:
        conn.executemany(
            "UPDATE documents SET archive_path = ? WHERE id = ?",
            [(ziel, document_id) for document_id, ziel in aenderungen.items()],
        )
        conn.commit()

    finally:
        conn.close()

    logger.info(
        "Archivpfade repariert: %s neu gebunden, %s ungelöst, %s Kollisionen",
        bericht["repariert"],
        bericht["ungeloest"],
        bericht["kollisionen"],
    )

    return bericht


def _konfigurierte_orte():
    from src.core.config import load_config

    config = load_config()

    return config["database"]["path"], config["paths"]["archive"]


def run_check():
    """Trockenlauf anhand der Konfiguration (App und CLI)."""
    db_path, archiv = _konfigurierte_orte()

    return pruefe_archivpfade(db_path, archiv)


def run_repair():
    """Reparatur anhand der Konfiguration (App und CLI)."""
    db_path, archiv = _konfigurierte_orte()

    return repariere_archivpfade(db_path, archiv)
