"""Datenschutzpruefung am fertigen Release-Paket.

    python -m tools.scan_tarball                       # neuestes dist/*.tar.gz
    python -m tools.scan_tarball <paket>.tar.gz        # bestimmtes Paket
    python -m tools.scan_tarball --db <pfad> <paket>   # anderer Bestand

Release-Pakete buendeln `src/classifier/prompts/*` mit — ein Echtname dort
landet in JEDEM veroeffentlichten Binary (so geschehen in 0.1.0 und 0.2.0).
`tests/test_keine_echtdaten.py` prueft nur den Quellstand und kennt zudem
keine Namen: eine Sperrliste echter Namen waere selbst ein Leck. Deshalb
vergleicht dieses Werkzeug gegen die FELDWERTE DES BESTANDS — die liegen
lokal, muessen nirgends aufgeschrieben werden und sind genau das, was nicht
ins Paket gehoert.

Exitcode 1, sobald etwas gefunden wurde. Bewusst ohne Ausnahmeliste: eine
Datei mit „bekannt und harmlos" muesste die Echtwerte enthalten und waere
das Leck, das sie verhindern soll. Jeder Befund wird von Hand eingeordnet.

⚠️ **Gemeldet wird nur maskiert.** Ein Werkzeug, das Echtdaten sucht und sie
beim Melden preisgibt, ist schlimmer als keines — beim Handlauf fuer 0.3.1
ist genau das passiert (das Ziffernmuster war in einem f-string doppelt
escaped, eine echte Rechnungsnummer stand im Klartext in der Ausgabe). Die
Maskierung ist deshalb gepinnt (`tests/test_scan_tarball.py`).

⚠️ **Gegen den INSTALLIERTEN Bestand pruefen, nicht gegen den im Repo.** Der
Aufruf laeuft aus dem Repo (sonst faende Python `tools/` nicht), und dort
greift der Entwickler-Modus: ohne Zutun stuende der kleinere Repo-Bestand
als Vergleich da und die Pruefung waere schwaecher, ohne es zu sagen.
Deshalb `--db` setzen (oder `BUEROKRATOR_HOME`); ohne `--db` warnt das
Werkzeug von selbst:

    python -m tools.scan_tarball \\
        --db ~/.local/share/buerokrator/profiles/1/database/buerokrator.db
"""

import argparse
import io
import json
import re
import sqlite3
import sys
import tarfile
import zipfile
from pathlib import Path

# Felder, deren Werte einen Menschen oder Vertrag identifizieren. `subject`
# steht bewusst NICHT darin: Betreffzeilen sind Freitext und erzeugen fast
# nur Fehlalarme; wer sie mitpruefen will, nimmt den Dateinamen (er traegt
# den Betreff ohnehin).
HEIKLE_FELDER = (
    "issuer",
    "employer",
    "insurer",
    "product_name",
    "invoice_number",
    "policy_number",
    "contract_number",
    "customer_number",
    "tax_id",
    "iban",
)

# Kuerzere Werte sind Gattungsbegriffe ("AG", "Miete") und erzeugen nur
# Rauschen. Dateinamen sind laenger und bekommen eine eigene Schwelle.
MIN_LAENGE = 6
MIN_LAENGE_DATEINAME = 11

# Mitgelieferte CA-Sammlung: enthaelt echte Konzernnamen (Telekom, Amazon),
# die mit Ausstellernamen kollidieren. Fremdcode, kein eigener Inhalt — wird
# uebersprungen und im Bericht ALS uebersprungen ausgewiesen.
FREMDCODE = ("/certifi/", "cacert.pem")

_ZIFFER = re.compile(r"\d")
_BUCHSTABE = re.compile(r"[^\W\d_]", re.UNICODE)


def maskiere(wert: str) -> str:
    """Ziffern zu N, Buchstaben zu x — Laenge und Satzzeichen bleiben.

    Die Form genuegt, um einen Wert wiederzuerkennen, und verraet ihn nicht.
    `[^\\W\\d_]` statt `[A-Za-z]`, weil eine ASCII-Klasse Umlaute stehen
    liesse und deutsche Namen damit oft noch zu erraten waeren.
    """
    return _BUCHSTABE.sub("x", _ZIFFER.sub("N", wert))


def sammle_bestandswerte(db_path) -> dict:
    """Feldwerte des Bestands, die nie in ein Paket gehoeren.

    Streng read-only: der Bestand ist Ground Truth der Qualitaetsmessung,
    und ein Pruefwerkzeug fasst ihn nicht an.
    """
    conn = sqlite3.connect(f"file:{Path(db_path)}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row

    try:
        zeilen = conn.execute(
            "SELECT filename, extracted_data FROM documents"
        ).fetchall()

    finally:
        conn.close()

    werte: dict = {}

    def merke(wert, feld, mindestlaenge):
        wert = (wert or "").strip()

        if len(wert) < mindestlaenge:
            return

        eintrag = werte.setdefault(wert, {"felder": set(), "dokumente": 0})
        eintrag["felder"].add(feld)
        eintrag["dokumente"] += 1

    for zeile in zeilen:
        try:
            daten = json.loads(zeile["extracted_data"] or "{}")

        except (ValueError, TypeError):
            daten = {}

        if not isinstance(daten, dict):
            daten = {}

        for feld in HEIKLE_FELDER:
            merke(str(daten.get(feld) or ""), feld, MIN_LAENGE)

        # Der Dateiname traegt Datum, Aussteller und Betreff — er ist der
        # Wert, der beim Historien-Scan schon einmal uebersehen wurde.
        merke(zeile["filename"], "filename", MIN_LAENGE_DATEINAME)

    return werte


def _paketdateien(tarball):
    """(Name, Bytes) jeder Datei im Paket — inklusive der in Zip-Archiven.

    Roh ueber die Bytes, ohne Endungsliste: ein Echtname kann genauso in
    einer kompilierten Datei stehen wie in einem Prompt. `base_library.zip`
    liegt im Paket, und deflate versteckt den Klartext vor jedem Byte-Scan —
    deshalb die Rekursion.

    Nicht erreichbar bleibt Python-Code im PYZ-Archiv INNERHALB der
    ausfuehrbaren Datei (zlib je Eintrag). Den deckt der Quellstand ab
    (`/datenschutz-check`, `tests/test_keine_echtdaten.py`).
    """
    with tarfile.open(tarball) as tf:
        for mitglied in tf:
            if not mitglied.isfile():
                continue

            if any(teil in mitglied.name for teil in FREMDCODE):
                yield mitglied.name, None
                continue

            datei = tf.extractfile(mitglied)

            if datei is None:
                continue

            inhalt = datei.read()

            yield mitglied.name, inhalt

            if not mitglied.name.endswith((".zip", ".whl", ".egg")):
                continue

            try:
                with zipfile.ZipFile(io.BytesIO(inhalt)) as zf:
                    for eintrag in zf.infolist():
                        if eintrag.is_dir():
                            continue

                        yield f"{mitglied.name}::{eintrag.filename}", zf.read(eintrag)

            except (zipfile.BadZipFile, OSError, RuntimeError):
                # Kein lesbares Archiv — die rohen Bytes sind oben schon
                # geprueft, mehr ist hier nicht zu holen.
                continue


def pruefe_tarball(tarball, werte):
    """Sucht jeden Bestandswert im Paket. Gibt (Treffer, geprueft, uebersprungen).

    Der Klartextwert verlaesst diese Funktion NICHT — der Treffer traegt nur
    die maskierte Form. Damit kann keine spaetere Ausgabe ihn versehentlich
    zeigen (die Form absichern, nicht die Absicht).
    """
    kodiert = [(wert, wert.encode("utf-8"), eigenschaften) for wert, eigenschaften in werte.items()]
    fundorte: dict = {}
    geprueft = 0
    uebersprungen = 0

    for name, inhalt in _paketdateien(tarball):
        if inhalt is None:
            uebersprungen += 1
            continue

        geprueft += 1

        for wert, roh, _ in kodiert:
            if roh in inhalt:
                fundorte.setdefault(wert, []).append(name)

    treffer = []

    for wert, roh, eigenschaften in kodiert:
        orte = fundorte.get(wert)

        if not orte:
            continue

        treffer.append(
            {
                "maskiert": maskiere(wert),
                "laenge": len(wert),
                "woerter": len(wert.split()),
                "hat_ziffern": bool(_ZIFFER.search(wert)),
                "felder": sorted(eigenschaften["felder"]),
                "dokumente": eigenschaften["dokumente"],
                "fundorte": orte,
            }
        )

    # Der auffaelligste zuerst: wenige Dokumente = eher ein privater Wert,
    # viele = eher Gattungsbegriff, der legitim im Erkennungsvokabular steht.
    treffer.sort(key=lambda t: (t["dokumente"], -t["laenge"]))

    return treffer, geprueft, uebersprungen


def bericht_zeilen(treffer, geprueft, uebersprungen):
    zeilen = [
        f"Dateien im Paket geprueft: {geprueft}",
        f"Uebersprungen (Fremdcode):  {uebersprungen}",
        "",
    ]

    if not treffer:
        zeilen.append("KEIN Treffer.")

        return zeilen

    zeilen.append(f"{len(treffer)} Bestandswert(e) im Paket gefunden:")
    zeilen.append("")

    for eintrag in treffer:
        zeilen.append(
            f"  {eintrag['maskiert']}"
            f"   Felder={','.join(eintrag['felder'])}"
            f" Dokumente={eintrag['dokumente']}"
            f" Woerter={eintrag['woerter']}"
            f" Ziffern={'ja' if eintrag['hat_ziffern'] else 'nein'}"
        )

        for ort in eintrag["fundorte"][:6]:
            zeilen.append(f"      {ort}")

        if len(eintrag["fundorte"]) > 6:
            zeilen.append(f"      … und {len(eintrag['fundorte']) - 6} weitere")

        zeilen.append("")

    zeilen.append(
        "Jeden Befund von Hand einordnen: ein Wert in VIELEN Dokumenten ist"
    )
    zeilen.append(
        "meist Erkennungsvokabular im Prompt, einer in wenigen eher privat."
    )

    return zeilen


def _neuestes_paket():
    pakete = sorted(
        Path("dist").glob("*.tar.gz"), key=lambda p: p.stat().st_mtime, reverse=True
    )

    if not pakete:
        raise SystemExit("Kein Paket in dist/ gefunden — Pfad angeben.")

    return pakete[0]


def _standard_datenbank():
    from src.core.config import load_config

    return Path(load_config()["database"]["path"])


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Release-Paket gegen die Feldwerte des Bestands pruefen."
    )
    parser.add_argument("tarball", nargs="?", help="Paket (Standard: neuestes dist/*.tar.gz)")
    parser.add_argument("--db", help="Datenbank des Bestands (Standard: aus der Config)")

    args = parser.parse_args(argv)

    tarball = Path(args.tarball) if args.tarball else _neuestes_paket()
    db_path = Path(args.db) if args.db else _standard_datenbank()

    if not tarball.exists():
        print(f"Paket nicht gefunden: {tarball}")

        return 2

    if not db_path.exists():
        print(f"Datenbank nicht gefunden: {db_path}")

        return 2

    print(f"Paket:      {tarball}")
    print(f"Bestand:    {db_path}")

    if not args.db and (Path.cwd() / "config" / "settings.yaml").exists():
        print(
            "\n⚠️  Entwickler-Modus: geprueft wird gegen den Bestand im Repo.\n"
            "    Der ist kleiner als der echte — mit BUEROKRATOR_HOME oder\n"
            "    --db gegen die Installation pruefen, sonst ist die Pruefung\n"
            "    schwaecher, ohne es zu sagen."
        )

    werte = sammle_bestandswerte(db_path)
    print(f"Bestandswerte geprueft: {len(werte)}\n")

    treffer, geprueft, uebersprungen = pruefe_tarball(tarball, werte)

    for zeile in bericht_zeilen(treffer, geprueft, uebersprungen):
        print(zeile)

    return 1 if treffer else 0


if __name__ == "__main__":
    sys.exit(main())
