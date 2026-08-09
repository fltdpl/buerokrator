"""Tags: Normalisierung und Vergabe (framework-frei).

Tags sind **flach** — ein Wert, keine Systematik. Der erste Entwurf sah
Namensräume vor (`koerper:knie`); er wurde verworfen, weil er ein Problem
löst, das erst bei Hunderten von Tags entsteht, dafür aber schon vor dem
ERSTEN Tag eine Ordnung verlangt. Gruppieren lässt sich später immer noch,
ohne dass sich ändert, wie man ein Tag schreibt.

Sie sind die einzige Dimension, die QUER durch die Kategorien läuft — eine
Behandlung umfasst Befund (health), Rechnung (invoice) und Krankmeldung
(health/attest). Deshalb hängen sie NICHT an `extracted_data` und laufen an
der Feld-Whitelist vorbei: dort steht, was IM Dokument steht, ein Tag ist,
was der Nutzer ÜBER das Dokument sagt.

Der teuerste Fehler eines Tag-Systems ist die Dublette. Zwei Formen jedes
Namens lösen das, ohne die Anzeige zu verunstalten: `name` ist die
Schreibweise, wie sie eingegeben wurde, `key` der Vergleichswert
(casefold). „Knie-OP" bleibt „Knie-OP", trifft aber „knie-op".
"""

import re

from src.database.tags import (
    list_tags as _list_tags,
    set_document_tags as _set_document_tags,
    tags_for_document as _tags_for_document,
)

MAX_NAME_LENGTH = 60


def normalize_tag_name(text):
    """Anzeigename in kanonischer Form; wirft ValueError bei Unbrauchbarem.

    Bewusst nachsichtig: getrimmt und innenliegender Leerraum
    zusammengefasst, sonst unverändert. Groß-/Kleinschreibung bleibt — sie
    ist Anzeige, nicht Bedeutung (dafür ist `tag_key` da).
    """
    name = re.sub(r"\s+", " ", str(text or "").strip())

    if not name:
        raise ValueError("Ein Tag braucht einen Namen.")

    if len(name) > MAX_NAME_LENGTH:
        raise ValueError(
            f"Der Name ist zu lang (höchstens {MAX_NAME_LENGTH} Zeichen)."
        )

    if not any(zeichen.isalnum() for zeichen in name):
        raise ValueError("Ein Tag braucht mindestens einen Buchstaben oder eine Ziffer.")

    return name


def tag_key(name):
    """Vergleichswert eines Namens — hierüber ist ein Tag eindeutig.

    `casefold` statt `lower`: es faltet auch „ß"/„ss" und die Umlaute
    zuverlässig, und genau daran scheitert SQLites COLLATE NOCASE.
    """
    return re.sub(r"\s+", " ", str(name or "").strip()).casefold()


def tags_for_document(document_id):
    return _tags_for_document(document_id)


def list_tags():
    return _list_tags()


def set_document_tags(document_id, namen):
    """Setzt die Tags eines Dokuments; `namen` sind freie Eingabeformen.

    Dubletten innerhalb eines Aufrufs fallen zusammen — „Auto", „auto" und
    „AUTO" sind dasselbe Tag; die erste Nennung gibt die Schreibweise vor.
    """
    eintraege = []
    gesehen = set()

    for eingabe in namen:
        name = normalize_tag_name(eingabe)
        key = tag_key(name)

        if key in gesehen:
            continue

        gesehen.add(key)
        eintraege.append((name, key))

    _set_document_tags(document_id, eintraege)


def add_to_selection(auswahl, eingabe):
    """Eingabe zur Auswahl hinzufügen; gibt die neue Auswahl zurück.

    Die Detailansicht hält den Stand als Liste von Anzeigenamen und
    schreibt ihn erst beim Speichern. Dass „Knie-OP" und „knie-op" dasselbe
    Tag sind, darf sie nicht selbst wissen müssen.
    """
    name = normalize_tag_name(eingabe)
    key = tag_key(name)

    if any(tag_key(vorhanden) == key for vorhanden in auswahl):
        raise ValueError(f"„{name}“ ist an diesem Dokument schon vergeben.")

    return [*auswahl, name]


def remove_from_selection(auswahl, name):
    """Einen Eintrag aus der Auswahl nehmen — unabhängig von der Schreibweise."""
    key = tag_key(name)

    return [vorhanden for vorhanden in auswahl if tag_key(vorhanden) != key]


def is_selected(auswahl, name):
    key = tag_key(name)

    return any(tag_key(vorhanden) == key for vorhanden in auswahl)
