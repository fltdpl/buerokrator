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
    add_tag_to_documents as _add_tag_to_documents,
    delete_tag as _delete_tag,
    document_ids_with_all_tags as _document_ids_with_all_tags,
    get_tag,
    key_belongs_to_other_tag,
    list_tags as _list_tags,
    merge_tags as _merge_tags,
    rename_tag as _rename_tag,
    set_tag_color as _set_tag_color,
    remove_tag_from_documents as _remove_tag_from_documents,
    set_document_tags as _set_document_tags,
    tags_by_documents as _tags_by_documents,
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


def add_tag_to_documents(document_ids, eingabe):
    """Ein Tag an die ausgewählten Dokumente hängen (Stapelvergabe).

    Ergänzend: vorhandene Tags der Dokumente bleiben. Ein noch unbekanntes
    Tag entsteht dabei — der Knopf in der Liste IST die ausdrückliche
    Handlung, die es sonst in der Detailansicht braucht.
    """
    name = normalize_tag_name(eingabe)

    return _add_tag_to_documents(list(document_ids), name, tag_key(name))


def remove_tag_from_documents(document_ids, eingabe):
    """Ein Tag von den ausgewählten Dokumenten nehmen.

    Unbekannte Tags sind kein Fehler: die Auswahl kann Dokumente enthalten,
    die es nie getragen haben.
    """
    name = normalize_tag_name(eingabe)

    return _remove_tag_from_documents(list(document_ids), tag_key(name))


def rename_tag(tag_id, neuer_name):
    """Benennt ein Tag um.

    Eine reine Änderung der Schreibweise ist ausdrücklich erlaubt („knie-op"
    → „Knie-OP"): der Schlüssel bleibt derselbe, es entsteht kein Konflikt.
    Trägt dagegen ein ANDERES Tag den Schlüssel schon, wäre die Umbenennung
    in Wahrheit ein Zusammenführen — und das soll man ausdrücklich wollen,
    nicht versehentlich auslösen.
    """
    name = normalize_tag_name(neuer_name)
    key = tag_key(name)

    if get_tag(tag_id) is None:
        raise ValueError("Dieses Tag gibt es nicht mehr.")

    if key_belongs_to_other_tag(key, tag_id):
        raise ValueError(
            f"„{name}“ gibt es schon. Zum Vereinigen die beiden Tags "
            "zusammenführen."
        )

    _rename_tag(tag_id, name, key)


def merge_tags(quelle_id, ziel_id):
    """Führt zwei Tags zusammen; gibt die Zahl der umgezogenen Dokumente."""
    if quelle_id == ziel_id:
        raise ValueError("Ein Tag lässt sich nicht mit sich selbst zusammenführen.")

    if get_tag(quelle_id) is None or get_tag(ziel_id) is None:
        raise ValueError("Eines der beiden Tags gibt es nicht mehr.")

    return _merge_tags(quelle_id, ziel_id)


def delete_tag(tag_id):
    """Entfernt ein Tag samt Zuordnungen; gibt deren Zahl zurück."""
    if get_tag(tag_id) is None:
        raise ValueError("Dieses Tag gibt es nicht mehr.")

    return _delete_tag(tag_id)


def set_tag_color(tag_id, color_index, farbanzahl=None):
    """Farb-Nummer setzen.

    `farbanzahl` reicht die Oberfläche durch (Länge der Palette) — die
    Dienstschicht kennt die Palette nicht, prüft aber, dass die Nummer im
    zulässigen Bereich liegt.
    """
    try:
        nummer = int(color_index)

    except (TypeError, ValueError) as fehler:
        raise ValueError("Ungültige Farbe.") from fehler

    if nummer < 0 or (farbanzahl is not None and nummer >= farbanzahl):
        raise ValueError("Ungültige Farbe.")

    if get_tag(tag_id) is None:
        raise ValueError("Dieses Tag gibt es nicht mehr.")

    _set_tag_color(tag_id, nummer)


def tags_by_documents(document_ids):
    """{document_id: [Tag, …]} für viele Dokumente in einer Abfrage."""
    return _tags_by_documents(document_ids)


def document_ids_with_all_tags(namen):
    """IDs der Dokumente, die ALLE genannten Tags tragen."""
    return _document_ids_with_all_tags(
        [tag_key(name) for name in namen if str(name or "").strip()]
    )


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
