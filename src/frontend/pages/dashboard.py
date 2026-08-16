from nicegui import ui

from src.core.document_types import (
    DOCUMENT_TYPE_LABELS,
    DOCUMENT_TYPES,
)
from src.core.size_utils import format_bytes
from src.frontend.layout import card, gekuerzt, page_layout, umzug_noetig
from src.frontend.theme import (
    ACCENTS,
    DARK_ACTIVE,
    DOCUMENT_TYPE_ICONS,
    INK_MUTED,
)
from src.services.profile_port import legacy_bestand_gefunden
from src.services.profile_service import list_profiles
from src.services.setup_service import needs_setup
from src.services.stats_service import get_dashboard_data


def _anzahl_text(anzahl):
    """`1 Dokument`, sonst `N Dokumente`.

    Die Einzahl kostet eine Zeile und fällt sofort auf, wenn sie fehlt —
    „1 Dokumente" liest sich wie ein Fehler in der Anwendung. Bei Null ist
    die Mehrzahl richtig („0 Dokumente").
    """
    return f"{anzahl} Dokument" if anzahl == 1 else f"{anzahl} Dokumente"


def _kategorie_kachel(document_type, anzahl):
    """Eine Kategorie: Sinnbild, Name, Anzahl — und der Weg in die Liste.

    Der NAME steht oben und groß, die Anzahl klein darunter: gesucht wird
    nach der Kategorie, gelesen wird die Zahl erst danach. Elf Zahlen, die
    nirgendwohin führen, wären ohnehin Dekoration statt Bedienung.

    Die NULL ist der Sonderfall: sie führt nirgendwohin und wird deshalb
    gedämpft und nicht klickbar dargestellt — klickbar sähe sie aus wie ein
    Weg und endete in einer leeren Liste.

    Alle Icons tragen denselben Akzent (siehe theme.DOCUMENT_TYPE_ICONS).
    """
    leer = not anzahl
    zusatz = "" if leer else "cursor-pointer klickbar"

    with card(f"grow {zusatz}") as kachel:
        kachel.mark(f"kachel-{document_type}")

        if not leer:
            kachel.on(
                "click",
                lambda: ui.navigate.to(f"/dokumente?typ={document_type}"),
            )

        with ui.row().classes("items-center gap-3"):
            ui.icon(DOCUMENT_TYPE_ICONS.get(document_type, "description")).classes(
                "text-3xl"
            ).style(f"color: {INK_MUTED if leer else ACCENTS['primary']}")

            with ui.column().classes("gap-1"):
                ui.label(
                    DOCUMENT_TYPE_LABELS.get(document_type, document_type)
                ).classes("text-xl font-light leading-none").style(
                    f"color: {INK_MUTED}" if leer else ""
                )
                ui.label(_anzahl_text(anzahl)).classes("text-sm").style(
                    f"color: {INK_MUTED}"
                )


def _render_active_profile():
    """Wessen Bestand hier zu sehen ist — nur bei mehreren Profilen.

    Bewusst doppelt zur Seitenleiste: die Zahlen darunter sind die eines
    bestimmten Menschen, und wer sie für seine eigenen hält, zieht falsche
    Schlüsse.
    """
    profile = list_profiles()

    if len(profile) < 2:
        return

    aktiv = next((p for p in profile if p["active"]), profile[0])

    with ui.row().classes("items-center gap-2 py-1"):
        ui.icon("person").style(f"color: {DARK_ACTIVE}")
        ui.label("Geöffnet:").classes("text-sm").style(f"color: {INK_MUTED}")
        ui.label(aktiv["name"]).classes("text-sm text-weight-bold").style(
            f"color: {DARK_ACTIVE}"
        )


@ui.page("/")
def dashboard_page():
    # Bestand aus der Zeit vor den Profilen → Umzug anbieten. VOR der
    # Setup-Prüfung: die sieht nur die (fehlende) Datenbank im Profil und
    # hielte einen gewachsenen Bestand für eine frische Installation.
    if umzug_noetig():
        return

    # Frische Instanz → Einrichtungsassistent. Prüfung VOR dem ersten
    # DB-Zugriff: der würde die (leere) DB anlegen und den Check kippen.
    if needs_setup():
        ui.navigate.to("/einrichtung")
        return

    stats = get_dashboard_data()
    counts = stats["counts_by_type"]

    with page_layout("Dashboard"):
        ui.label("Dashboard").classes("text-3xl page-title")
        # Gesamtzahl und Archivgröße in EINER Zeile: eine eigene Kachel
        # „Dokumente" stünde neben derselben Zahl im Untertitel, und die
        # Größe gehört nicht zwischen die Kategorien — sie zählt Bytes,
        # nicht Dokumente.
        ui.label(
            f"{stats['total']} Dokumente archiviert"
            f" · {format_bytes(stats['archive_size'])} im Archiv"
        ).classes("muted")

        _render_active_profile()

        # Alle elf Kategorien, feste Reihenfolge. Sortiert nach Menge
        # wanderten die Kacheln bei jedem Import — man müsste sie jedes Mal
        # neu suchen. Kein `no-wrap`: elf Kacheln müssen umbrechen dürfen.
        with ui.grid().classes(
            "grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4 w-full"
        ):
            for document_type in DOCUMENT_TYPES:
                _kategorie_kachel(document_type, counts.get(document_type, 0))

        # Aufgaben: die beiden Dinge, die tatsächlich Arbeit bedeuten —
        # Inbox importieren und ungeprüfte Dokumente durchsehen.
        with card("w-full"):
            ui.label("Aufgaben").classes("text-xl page-title")

            if stats["unverified_count"] or stats["inbox_count"]:
                with ui.row().classes("gap-4"):
                    if stats["unverified_count"]:
                        first_id = stats["first_unverified_id"]
                        ui.button(
                            f"{stats['unverified_count']} ungeprüfte Dokumente prüfen",
                            icon="fact_check",
                            on_click=lambda: ui.navigate.to(f"/dokumente/{first_id}"),
                        ).props("color=primary unelevated")

                    if stats["inbox_count"]:
                        ui.button(
                            f"{stats['inbox_count']} Datei(en) in der Inbox importieren",
                            icon="file_upload",
                            on_click=lambda: ui.navigate.to("/import"),
                        ).props("outline color=primary")

            else:
                with ui.row().classes("items-center gap-2"):
                    ui.icon("check_circle").style(f"color: {ACCENTS['success']}")
                    ui.label("Keine offenen Aufgaben — Inbox leer, alles geprüft.")

        with card("w-full"):
            ui.label("Zuletzt archiviert").classes("text-xl page-title")

            for row in stats["recent"]:
                document_id = row["id"]
                filename = row["filename"]
                document_type = row["document_type"]
                type_label = DOCUMENT_TYPE_LABELS.get(document_type, document_type)

                # Ungekürzt lief der Dateiname über den Rand der Karte
                # hinaus. `flex-nowrap` hält Typ und Name in einer Zeile,
                # `shrink-0` schützt das Typ-Label vorm Zusammenquetschen.
                # `filename` ist nullable. Ohne Ersatztext bliebe der Link
                # leer und damit unklickbar — die Zeile führte nirgendwohin.
                beschriftung = filename or f"#{document_id} (ohne Dateinamen)"

                with ui.row().classes("gap-2 items-center w-full flex-nowrap"):
                    ui.label(type_label).classes("text-sm w-32 shrink-0").style(
                        f"color: {INK_MUTED}"
                    )
                    gekuerzt(
                        ui.link(beschriftung, f"/dokumente/{document_id}"),
                        beschriftung,
                        "flex-1",
                    )
