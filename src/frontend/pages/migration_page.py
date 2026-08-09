"""Umzug eines Bestands aus der Zeit vor den Profilen (ADR 015).

Die Seite gibt es, weil der Fall sonst still bliebe: seit den Profilen liegen
die Daten unter `profiles/<kennung>/`, ein gewachsener Bestand aber eine Ebene
höher. Die App legt dann im Profil eine leere Datenbank an und meldet
„0 Dokumente archiviert", während das Archiv unberührt daneben liegt.

Das Kommandozeilen-Werkzeug half dabei nur denen, die den Quellcode haben —
wer aus einem Release-Paket installiert hat, besitzt weder Python noch
`tools/`. Deshalb hier, mit einem Knopf.
"""

from nicegui import run, ui

from src.frontend.layout import card, page_layout
from src.frontend.theme import ACCENTS, INK_MUTED
from src.services.profile_port import enable_profiles, legacy_bestand_gefunden


def _erklaerung():
    ui.label(
        "Deine Dokumente liegen noch in der Ablage einer älteren Version. "
        "Damit sie wieder sichtbar werden, ziehen sie einmalig in einen "
        "eigenen Ordner um — die Grundlage dafür, dass mehrere Personen "
        "getrennte Bestände haben können."
    )

    ui.label("Was dabei passiert:").classes("text-weight-bold q-mt-md")

    for zeile in (
        "Datenbank und Archiv werden **kopiert**, nicht verschoben.",
        "Danach prüft die App, ob jedes Dokument am neuen Ort wirklich "
        "liegt — erst dann schaltet sie um.",
        "Die Originale bleiben als Sicherung liegen. **Gelöscht wird "
        "nichts.**",
        "Schlägt etwas fehl, bleibt alles, wie es war.",
    ):
        with ui.row().classes("items-start gap-2 no-wrap"):
            ui.icon("check").classes("text-sm q-mt-xs").style(
                f"color: {ACCENTS['success']}"
            )
            ui.markdown(zeile)

    ui.label(
        "Der Umzug kopiert das gesamte Archiv — bei vielen Dokumenten kann "
        "das einen Moment dauern. Bitte das Fenster so lange offen lassen."
    ).classes("text-sm q-mt-md").style(f"color: {INK_MUTED}")


def _ergebnis(bericht):
    with ui.row().classes("items-center gap-2"):
        ui.icon("check_circle").classes("text-2xl").style(
            f"color: {ACCENTS['success']}"
        )
        ui.label("Der Umzug ist abgeschlossen.").classes("text-xl page-title")

    ui.label(
        f"{bericht['geprueft']} Dokument(e) geprüft, "
        f"{bericht['umgeschrieben']} Pfad(e) nachgezogen."
    )

    ui.label(f"Bestand liegt jetzt unter: {bericht['profil']}").classes(
        "text-sm"
    ).style(f"color: {INK_MUTED}")
    ui.label(f"Originale als Sicherung in: {bericht['altbestand']}").classes(
        "text-sm"
    ).style(f"color: {INK_MUTED}")

    ui.label(
        "Sieh dir ein paar Dokumente an, bevor du die Sicherung von Hand "
        "löschst."
    ).classes("q-mt-md")

    ui.button(
        "Zum Dashboard",
        icon="dashboard",
        on_click=lambda: ui.navigate.to("/"),
    ).props("color=primary unelevated no-caps")


@ui.page("/umzug")
def migration_page():
    # Direkt aufgerufen, obwohl es nichts zu tun gibt: nicht anbieten, was
    # nur schiefgehen kann.
    if not legacy_bestand_gefunden():
        ui.navigate.to("/")
        return

    with page_layout("Umzug"):
        ui.label("Bestand aus einer älteren Version").classes(
            "text-3xl page-title"
        )
        ui.label("Einmalig umziehen, dann ist alles wieder da.").classes("muted")

        ergebnis = []

        @ui.refreshable
        def bereich():
            with card("w-full"):
                if ergebnis:
                    _ergebnis(ergebnis[0])
                    return

                _erklaerung()

                async def starten():
                    knopf.disable()
                    spinner.set_visibility(True)

                    try:
                        bericht = await run.io_bound(enable_profiles)

                    except Exception as fehler:
                        spinner.set_visibility(False)
                        knopf.enable()
                        ui.notify(
                            f"Umzug abgebrochen: {fehler}",
                            type="negative",
                            multi_line=True,
                            close_button="OK",
                        )
                        return

                    ergebnis.append(bericht)
                    bereich.refresh()

                with ui.row().classes("items-center gap-3 q-mt-md"):
                    knopf = ui.button(
                        "Umzug jetzt starten",
                        icon="drive_file_move",
                        on_click=starten,
                    ).props("color=primary unelevated no-caps")

                    spinner = ui.spinner(size="lg")
                    spinner.set_visibility(False)

        bereich()
