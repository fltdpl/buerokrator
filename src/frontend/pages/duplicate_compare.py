"""Gegenüberstellung zweier Dokumente, die als Dublette gemeldet wurden.

Die Warnung auf der Detailseite sagt, dass zwei Belege gleich aussehen — die
Entscheidung, ob sie es SIND, fiel bisher am Papierstapel: der Link führte auf
die andere Seite, und verglichen wurde aus dem Gedächtnis. Hier stehen beide
Belege nebeneinander, darüber ihre Werte.

Gelöscht wird auch hier nichts von selbst; der Papierkorb-Knopf fragt nach und
verschiebt nur nach `trash/` (wie überall, siehe `move_document_to_trash`).
"""

from nicegui import ui

from src.database.list_documents import get_document
from src.frontend.layout import gekuerzt, page_layout, umzug_noetig
from src.frontend.pages.document_detail import QUELLE_HOEHE, _confirm_dialog
from src.frontend.theme import INK_MUTED, WARNING
from src.services.document_service import move_document_to_trash
from src.services.duplicate_service import compare_documents, find_content_duplicates

_STATUS_FARBE = {
    "abweichend": WARNING,
    "fehlt": INK_MUTED,
    "gleich": INK_MUTED,
}


def _grund(document_id, other_id):
    """Warum das Paar gemeldet wurde — oder None, wenn es das nicht (mehr) ist.

    Die Seite ist auch über die Adresszeile erreichbar, und nach einer
    Korrektur kann die Meldung entfallen sein. Das gehört dann dazugesagt,
    statt eine Warnung vorzutäuschen, die es nicht mehr gibt.
    """
    for treffer in find_content_duplicates(document_id):
        if treffer["id"] == other_id:
            return treffer["reason"]

    return None


def _werte_tabelle(zeilen, links_label, rechts_label):
    """Feld, beide Werte, Bewertung — die Zeile, an der es sich entscheidet."""
    with ui.grid(columns="140px 1fr 1fr 110px").classes("w-full gap-x-4 gap-y-1"):
        for kopf in ("Feld", links_label, rechts_label, ""):
            ui.label(kopf).classes("text-xs").style(f"color: {INK_MUTED}")

        for zeile in zeilen:
            ui.label(zeile["label"]).classes("text-sm").style(f"color: {INK_MUTED}")
            ui.label(zeile["links"] or "—").classes("text-sm break-all")
            ui.label(zeile["rechts"] or "—").classes("text-sm break-all")
            ui.label(zeile["status"]).classes("text-xs").style(
                f"color: {_STATUS_FARBE[zeile['status']]}"
            )


def _beleg_spalte(row, gegenstueck_id, titel):
    """Eine Seite der Gegenüberstellung: Kopfzeile, PDF, Papierkorb-Knopf."""
    document_id = row["id"]

    def loeschen():
        move_document_to_trash(document_id)
        ui.navigate.to(f"/dokumente/{gegenstueck_id}")

    dialog = _confirm_dialog(
        f"#{document_id} wirklich in den Papierkorb verschieben?",
        "Ja, löschen",
        loeschen,
    )

    with ui.column().classes("flex-1 min-w-0 gap-2"):
        with ui.row().classes("w-full items-baseline gap-2 flex-nowrap"):
            ui.link(f"#{document_id}", f"/dokumente/{document_id}").classes("text-sm")
            ui.label(titel).classes("text-xs").style(f"color: {INK_MUTED}")

        gekuerzt(
            ui.label(row["filename"]).classes("text-xs w-full"),
            row["filename"],
        )

        ui.element("iframe").props(
            f'src="/pdf/{document_id}" type="application/pdf"'
        ).classes("w-full").style(f"height: {QUELLE_HOEHE}; border: none;")

        ui.button(
            "In den Papierkorb", on_click=dialog.open
        ).props("flat dense color=negative").classes("text-xs self-start")


@ui.page("/dokumente/{document_id}/vergleich/{other_id}")
def duplicate_compare_page(document_id: int, other_id: int):
    if umzug_noetig():
        return

    links = get_document(document_id)
    rechts = get_document(other_id)

    if links is None or rechts is None:
        with page_layout("Gegenüberstellung"):
            ui.label("Eines der beiden Dokumente gibt es nicht (mehr).").classes(
                "text-red-600"
            )
            ui.link("Zur Übersicht", "/dokumente")

        return

    grund = _grund(document_id, other_id)

    with page_layout("Gegenüberstellung"):
        ui.label("Gegenüberstellung").classes("text-xl page-title")

        if grund:
            ui.label(f"Gemeldet, weil: {grund}").classes("text-sm").style(
                f"color: {WARNING}"
            )
        else:
            ui.label(
                "Diese beiden werden derzeit NICHT als Dublette gemeldet —"
                " die Werte widersprechen sich zu stark oder wurden korrigiert."
            ).classes("text-sm").style(f"color: {INK_MUTED}")

        _werte_tabelle(
            compare_documents(document_id, other_id),
            f"#{document_id}",
            f"#{other_id}",
        )

        with ui.row().classes("w-full gap-4 flex-nowrap items-start"):
            _beleg_spalte(links, other_id, "dieses Dokument")
            _beleg_spalte(rechts, document_id, "der gemeldete Treffer")

        ui.link("Zurück zum Dokument", f"/dokumente/{document_id}").classes("text-sm")
