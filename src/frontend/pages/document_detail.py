from pathlib import Path

from nicegui import ui

from src.core.document_display import get_document_display_name
from src.core.document_types import (
    DOCUMENT_TYPES,
    DOCUMENT_TYPE_LABELS,
    normalize_document_type,
)
from src.database.document_repository import save_document
from src.database.list_documents import get_document, get_next_unverified_id
from src.database.set_document_verified import set_document_verified
from src.database.statistics import get_verification_statistics
from src.frontend.layout import card, page_layout
from src.services.document_service import (
    move_document_to_trash,
    parse_document_row,
)
from src.tax.tax_relevance import resolve_tax_relevance
from src.services.form_schema import (
    empty_fields,
    form_fields,
    is_known_subtype,
    merge_form_values,
    missing_required_fields,
    subtype_config,
)


def _amount_input_value(amount):
    if amount is None or amount == "":
        return ""

    return str(amount)


@ui.page("/dokumente/{document_id}")
def document_detail_page(document_id: int):
    row = get_document(document_id)

    if row is None:
        with page_layout("Dokument"):
            ui.label("Dokument nicht gefunden.").classes("text-red-600")
            ui.link("Zur Übersicht", "/dokumente")

        return

    document = parse_document_row(row)
    data = document["data"]

    state = {
        "document_type": normalize_document_type(document["document_type"]),
        "subtype": data.get("document_subtype", ""),
    }
    inputs = {}

    # Effektive Steuerrelevanz: gespeicherter Wert, sonst der aus Typ/Subtyp
    # abgeleitete Default. Die Checkbox unten überstimmt ihn beim Speichern.
    initial_tax_relevant = resolve_tax_relevance(
        state["document_type"], data, document["tax_relevant"]
    )

    def goto_next_or_list():
        next_id = get_next_unverified_id(exclude_id=document_id)

        if next_id is not None:
            ui.navigate.to(f"/dokumente/{next_id}")

        else:
            ui.navigate.to("/dokumente")

    def save(verify=False):
        # Ein Weg für alles: Freigeben speichert IMMER den Formularstand.
        values = {key: element.value for key, element in inputs.items()}
        updated = merge_form_values(
            state["document_type"],
            data,
            values,
            subtype=state["subtype"] or None,
        )

        save_document(
            document_id=document_id,
            archive_path=document["archive_path"],
            document_type=state["document_type"],
            extracted_data=updated,
            notes=notes_area.value,
            tax_relevant=tax_relevant_checkbox.value,
        )

        if verify:
            set_document_verified(document_id, 1)
            goto_next_or_list()

        else:
            # Neu laden: Umbenennung/Whitelist sollen sichtbar werden.
            ui.navigate.to(f"/dokumente/{document_id}")

    def unverify():
        set_document_verified(document_id, 0)
        ui.navigate.to(f"/dokumente/{document_id}")

    def delete():
        move_document_to_trash(document_id)
        ui.navigate.to("/dokumente")

    with ui.dialog() as delete_dialog, ui.card():
        ui.label("Dokument wirklich in den Papierkorb verschieben?")

        with ui.row().classes("justify-end w-full"):
            ui.button("Abbrechen", on_click=delete_dialog.close).props("flat")
            ui.button("Ja, löschen", on_click=delete).props("color=negative")

    def handle_key(event):
        if not event.action.keydown or event.action.repeat:
            return

        if event.key.escape:
            ui.navigate.to("/dokumente")

        elif event.key.enter and event.modifiers.ctrl:
            save(verify=True)

    # ignore=[]: die Shortcuts sollen auch beim Tippen in Feldern greifen
    # (Strg+Enter und Escape kollidieren nicht mit Texteingabe).
    ui.keyboard(on_key=handle_key, ignore=[])

    @ui.refreshable
    def form_area():
        inputs.clear()

        ui.select(
            {dtype: DOCUMENT_TYPE_LABELS.get(dtype, dtype) for dtype in DOCUMENT_TYPES},
            value=state["document_type"],
            label="Dokumenttyp",
            on_change=lambda event: change_type(event.value),
        ).classes("w-full")

        sub_config = subtype_config(state["document_type"])

        if sub_config:
            options = dict.fromkeys(
                [state["subtype"], *sub_config["options"]]
                if state["subtype"]
                else sub_config["options"]
            )
            labels = {
                value: sub_config["labels"].get(value, value) for value in options
            }

            ui.select(
                labels,
                value=state["subtype"] or sub_config["options"][0],
                label="Unterart",
                on_change=lambda event: change_subtype(event.value),
            ).classes("w-full")

            if state["subtype"] and not is_known_subtype(
                state["document_type"], state["subtype"]
            ):
                ui.label(
                    "Unbekannte Unterart — bestehende Felder bleiben unverändert."
                ).classes("text-xs muted")

        subtype = state["subtype"] or None
        missing = set(missing_required_fields(state["document_type"], data, subtype))
        empty = set(empty_fields(state["document_type"], data, subtype))

        if missing:
            ui.label(
                f"⚠️ {len(missing)} Pflichtfeld(er) leer — bitte aus dem Dokument"
                " ergänzen."
            ).classes("text-sm text-orange-700")

        for field in form_fields(state["document_type"], subtype):
            key = field["key"]

            if field["kind"] == "amount":
                default = _amount_input_value(data.get(key))

            else:
                default = data.get(key) or ""

            label = f"{field['label']} *" if field.get("required") else field["label"]
            element = ui.input(label, value=default).classes("w-full")

            # Leere Pflichtfelder auffällig, sonstige Lücken dezent: beides
            # ist eine Information, aber nur das eine hält das Dokument auf.
            if key in missing:
                element.props("error error-message=Pflichtfeld")

            elif key in empty:
                element.props('hint="nicht erkannt"')

            inputs[key] = element

    def change_type(document_type):
        state["document_type"] = document_type
        sub_config = subtype_config(document_type)
        current = data.get("document_subtype", "")

        # Beim Typwechsel den Bestandssubtyp behalten, falls der neue Typ
        # Subtypen kennt; sonst zurücksetzen.
        state["subtype"] = current if sub_config else ""

        if sub_config and not current:
            state["subtype"] = sub_config["options"][0]

        form_area.refresh()

    def change_subtype(subtype):
        state["subtype"] = subtype
        form_area.refresh()

    # ------------------------------------------------------------------
    # Seitenaufbau
    # ------------------------------------------------------------------

    display_name = get_document_display_name(document["document_type"], data)
    status_text = "🟢 Geprüft" if document["verified"] else "🟡 Ungeprüft"
    type_label = DOCUMENT_TYPE_LABELS.get(
        document["document_type"], document["document_type"]
    )
    unverified_count = get_verification_statistics()[0]

    with page_layout(display_name):
        with ui.row().classes("items-center justify-between w-full"):
            with ui.column().classes("gap-0"):
                ui.label(display_name).classes("text-3xl page-title")
                ui.label(f"{type_label} · {status_text}").classes("muted")

            with ui.row().classes("gap-2"):
                if Path(document["archive_path"]).exists():
                    ui.button(
                        "📥 Download",
                        on_click=lambda: ui.download(document["archive_path"]),
                    ).props("flat")

                if document["verified"]:
                    ui.button("↩️ Widerrufen", on_click=unverify).props("flat")

                ui.button("🗑 Löschen", on_click=delete_dialog.open).props(
                    "flat color=negative"
                )

        with ui.row().classes("w-full gap-6 flex-nowrap items-start"):
            # Links: Formular + Aktionen + Notizen
            with card("w-1/2 gap-3"):
                form_area()

                tax_relevant_checkbox = ui.checkbox(
                    "Steuerrelevant",
                    value=initial_tax_relevant,
                )
                ui.label(
                    "Vorbelegt aus Art/Unterart — bei Bedarf ändern "
                    "(z. B. absetzbare Rechnung)."
                ).classes("text-xs muted")

                with ui.row().classes("gap-2 w-full"):
                    ui.button("💾 Speichern", on_click=lambda: save(verify=False))

                    ui.button(
                        "✅ Speichern & Freigeben",
                        on_click=lambda: save(verify=True),
                    ).props("color=primary")

                progress_hint = (
                    f"Noch {unverified_count} ungeprüft"
                    if document["verified"]
                    else f"Noch {unverified_count} ungeprüft (inkl. diesem)"
                )
                ui.label(
                    f"{progress_hint} · Strg+Enter = Speichern & Freigeben · "
                    "Esc = zurück zur Liste"
                ).classes("text-xs muted")

                notes_area = ui.textarea(
                    "📝 Notizen",
                    value=document["notes"] or "",
                ).classes("w-full")

            # Rechts: umschaltbares Panel PDF ⇄ OCR-Text (persistent, lädt
            # beim Bearbeiten der Felder nicht neu).
            with card("w-1/2 gap-2"):
                panel_toggle = ui.toggle(
                    ["PDF", "OCR-Text"],
                    value="PDF",
                ).props("dense")

                pdf_frame = ui.element("iframe").props(
                    f'src="/pdf/{document_id}" type="application/pdf"'
                ).classes("w-full").style("height: 75vh; border: none;")

                text_area = (
                    ui.textarea(value=document["document_text"] or "Kein Dokumentinhalt gespeichert.")
                    .props("readonly outlined")
                    .classes("w-full")
                    .style("height: 75vh;")
                )
                text_area.set_visibility(False)

                def switch_panel(event):
                    pdf_frame.set_visibility(event.value == "PDF")
                    text_area.set_visibility(event.value == "OCR-Text")

                panel_toggle.on_value_change(switch_panel)
