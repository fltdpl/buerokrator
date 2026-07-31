from pathlib import Path

from nicegui import run, ui

from src.core.document_display import get_document_display_name
from src.core.document_types import (
    DOCUMENT_TYPES,
    DOCUMENT_TYPE_LABELS,
    INVOICE,
    normalize_document_type,
)
from src.database.document_repository import save_document
from src.database.list_documents import (
    get_document,
    get_next_unverified_id,
    list_documents,
)
from src.frontend.listing_order import adjacent_id, get_listing_order
from src.database.set_document_verified import set_document_verified
from src.database.statistics import get_verification_statistics
from src.frontend.layout import card, page_layout
from src.services.document_service import (
    move_document_to_trash,
    parse_document_row,
    reanalyze_document,
)
from src.services.duplicate_service import find_content_duplicates
from src.tax.tax_purpose import TAX_PURPOSE_LABELS
from src.tax.tax_relevance import default_tax_relevance, resolve_tax_relevance
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


def _confirm_dialog(question, confirm_label, on_confirm):
    """Rückfrage-Dialog mit Abbrechen + einer roten Bestätigung.

    Die Seite braucht drei davon (erneut prüfen, löschen, Änderungen
    verwerfen) — vorher stand der gleiche Aufbau dreimal im Seitenkörper.
    """
    with ui.dialog() as dialog, ui.card():
        ui.label(question)

        with ui.row().classes("justify-end w-full"):
            ui.button("Abbrechen", on_click=dialog.close).props("flat")
            ui.button(confirm_label, on_click=on_confirm).props("color=negative")

    return dialog


def _meta_button(label, on_click, color=None):
    """Kleiner, flacher Button in der Optik der Meta-Zeile."""
    button = ui.button(label, on_click=on_click).props(
        "flat dense no-caps" + (f" color={color}" if color else "")
    )
    # Quasar-Buttons bringen eine eigene Schriftgröße mit — die Zeile
    # soll aber durchgehend wie die Meta-Beschriftung aussehen.
    button.style("font-size: inherit;")

    return button


def _meta_row(document_id, type_label, status_text, *, downloadable, verified, actions):
    """EINE kleine Zeile unter dem Titel: links Kennzahlen und Blättern,
    rechts die Aktionen.

    Bewusst eine Zeile statt einer Button-Leiste: lange Titel brechen so
    nicht um, und die Aktionen gehören sichtbar zur ganzen Seite.
    `actions` bündelt die Rückrufe der Seite (previous, next, download,
    reanalyze, unverify, delete).
    """
    with ui.row().classes("w-full items-center gap-1 muted"):
        ui.label(f"ID {document_id} · {type_label} · {status_text} ·")

        _meta_button("←", actions["previous"]).tooltip(
            "Vorheriges Dokument (Pfeil links)"
        )
        _meta_button("→", actions["next"]).tooltip("Nächstes Dokument (Pfeil rechts)")

        ui.space()

        if downloadable:
            _meta_button("📥 Download", actions["download"])
            ui.label("·")

        _meta_button("🔄 Erneut prüfen", actions["reanalyze"]).tooltip(
            "Klassifikation + Extraktion auf dem gespeicherten Text"
            " wiederholen — überschreibt korrigierte Werte"
        )

        if verified:
            ui.label("·")
            _meta_button("↩️ Widerrufen", actions["unverify"])

        ui.label("·")
        _meta_button("🗑 Löschen", actions["delete"], color="negative")


def _source_panel(document_id, document_text):
    """Rechte Spalte: umschaltbares Panel PDF ⇄ OCR-Text.

    Persistent aufgebaut statt refreshable: das Bearbeiten der Formularfelder
    darf die PDF-Ansicht nicht neu laden (Scrollposition!).
    """
    panel_toggle = ui.toggle(["PDF", "OCR-Text"], value="PDF").props("dense")

    pdf_frame = (
        ui.element("iframe")
        .props(f'src="/pdf/{document_id}" type="application/pdf"')
        .classes("w-full")
        .style("height: 75vh; border: none;")
    )

    text_area = (
        ui.textarea(value=document_text or "Kein Dokumentinhalt gespeichert.")
        .props("readonly outlined")
        .classes("w-full")
        .style("height: 75vh;")
    )
    text_area.set_visibility(False)

    def switch_panel(event):
        pdf_frame.set_visibility(event.value == "PDF")
        text_area.set_visibility(event.value == "OCR-Text")

    panel_toggle.on_value_change(switch_panel)


def _duplicate_hint(document_id):
    """Hinweis, wenn ein anderes Dokument denselben Beleg zeigt.

    Bewusst nur ein Hinweis mit Link: die Entscheidung, welcher Scan bleibt,
    trifft der Nutzer im Prüf-Workflow. Nichts wird automatisch gelöscht oder
    zusammengeführt.
    """
    duplicates = find_content_duplicates(document_id)

    if not duplicates:
        return

    with ui.column().classes("gap-0 w-full"):
        ui.label(
            f"⚠️ Mögliche Dublette — {len(duplicates)} anderes Dokument zeigt"
            " denselben Beleg:"
            if len(duplicates) == 1
            else f"⚠️ Mögliche Dublette — {len(duplicates)} andere Dokumente"
            " zeigen denselben Beleg:"
        ).classes("text-sm text-orange-700")

        for duplicate in duplicates:
            with ui.row().classes("items-center gap-1 text-sm"):
                ui.link(
                    f"#{duplicate['id']} {duplicate['filename']}",
                    f"/dokumente/{duplicate['id']}",
                )
                ui.label(f"({duplicate['reason']})").classes("text-xs muted")


def _render_field(field, data, missing, empty, on_tax_relevant_amount):
    """Ein Formularfeld aufbauen; liefert (Element, Ausgangswert).

    Der Ausgangswert geht in den Dirty-Check der Seite.
    """
    key = field["key"]

    if field["kind"] == "amount":
        default = _amount_input_value(data.get(key))

    else:
        default = data.get(key) or ""

    label = f"{field['label']} *" if field.get("required") else field["label"]
    element = ui.input(label, value=default).classes("w-full")

    # Leere Pflichtfelder auffällig, sonstige Lücken dezent: beides ist eine
    # Information, aber nur das eine hält das Dokument auf.
    if key in missing:
        element.props("error error-message=Pflichtfeld")

    elif key in empty:
        element.props('hint="nicht erkannt"')

    # § 35a-Beträge machen das Dokument steuerrelevant: die Checkbox wurde
    # beim Seitenaufbau (Felder noch leer) initialisiert und wird beim
    # Speichern IMMER explizit übernommen — ohne den Automatismus fiele der
    # Beleg still aus der § 35a-Summe.
    if key in ("household_services_amount", "craftsman_services_amount"):
        element.on_value_change(
            lambda event: event.value
            and event.value.strip()
            and on_tax_relevant_amount()
        )

    return element, default


def _render_type_selects(state, on_type_change, on_subtype_change):
    """Auswahl von Dokumenttyp und (falls der Typ welche kennt) Unterart."""
    ui.select(
        {dtype: DOCUMENT_TYPE_LABELS.get(dtype, dtype) for dtype in DOCUMENT_TYPES},
        value=state["document_type"],
        label="Dokumenttyp",
        on_change=lambda event: on_type_change(event.value),
    ).classes("w-full")

    sub_config = subtype_config(state["document_type"])

    if not sub_config:
        return

    options = dict.fromkeys(
        [state["subtype"], *sub_config["options"]]
        if state["subtype"]
        else sub_config["options"]
    )
    labels = {value: sub_config["labels"].get(value, value) for value in options}

    ui.select(
        labels,
        value=state["subtype"] or sub_config["options"][0],
        label="Unterart",
        on_change=lambda event: on_subtype_change(event.value),
    ).classes("w-full")

    if state["subtype"] and not is_known_subtype(
        state["document_type"], state["subtype"]
    ):
        ui.label(
            "Unbekannte Unterart — bestehende Felder bleiben unverändert."
        ).classes("text-xs muted")


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
    # Ausgangswerte für den Dirty-Check: Formularfelder beim Aufbau (siehe
    # form_area) plus Typ/Subtyp beim Seitenaufruf.
    initial_values = {}
    original_meta = {
        "document_type": state["document_type"],
        "subtype": state["subtype"] or "",
    }

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
            # Zweck nur zusammen mit Steuerrelevanz: ein unsichtbar
            # gewordener Zweck darf die Anlagen-Summen nicht still befüllen.
            tax_purpose=(
                tax_purpose_select.value or None
                if tax_purpose_select is not None and tax_relevant_checkbox.value
                else None
            ),
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

    def navigate_adjacent(step):
        """Blättert in der Listenreihenfolge (Fallback: Standardreihenfolge)."""
        order = get_listing_order()
        if document_id not in order:
            order = [row["id"] for row in list_documents()]

        target = adjacent_id(order, document_id, step)
        if target is not None:
            ui.navigate.to(f"/dokumente/{target}")

        else:
            ui.notify("Kein weiteres Dokument in dieser Richtung.")

    def delete():
        move_document_to_trash(document_id)
        ui.navigate.to("/dokumente")

    async def reanalyze():
        # LLM-Lauf dauert — io_bound hält die Event-Loop (und damit alle
        # anderen Seiten) am Leben.
        reanalyze_dialog.close()
        ui.notify("Erneute Analyse läuft — das kann einen Moment dauern …")
        result = await run.io_bound(reanalyze_document, document_id)

        if result["ok"]:
            ui.navigate.to(f"/dokumente/{document_id}")

        else:
            ui.notify(
                f"Analyse fehlgeschlagen: {result['error']}", color="negative"
            )

    reanalyze_dialog = _confirm_dialog(
        "Achtung: Alle korrigierten Werte werden durch eine neue"
        " automatische Analyse überschrieben und die Freigabe wird"
        " widerrufen. Fortfahren?",
        "Ja, erneut prüfen",
        reanalyze,
    )

    delete_dialog = _confirm_dialog(
        "Dokument wirklich in den Papierkorb verschieben?",
        "Ja, löschen",
        delete,
    )

    # ------------------------------------------------------------------
    # Dirty-Check: Navigation verwirft Änderungen nicht mehr kommentarlos.
    # ------------------------------------------------------------------

    def is_dirty():
        if state["document_type"] != original_meta["document_type"]:
            return True

        if (state["subtype"] or "") != original_meta["subtype"]:
            return True

        if notes_area.value != (document["notes"] or ""):
            return True

        if bool(tax_relevant_checkbox.value) != initial_tax_relevant:
            return True

        if tax_purpose_select is not None and (tax_purpose_select.value or "") != (
            document["tax_purpose"] or ""
        ):
            return True

        return any(
            element.value != initial_values.get(key)
            for key, element in inputs.items()
        )

    pending_leave = {"action": None}

    def discard_and_leave():
        leave_dialog.close()

        if pending_leave["action"]:
            pending_leave["action"]()

    leave_dialog = _confirm_dialog(
        "Ungespeicherte Änderungen gehen verloren — fortfahren?",
        "Verwerfen & weiter",
        discard_and_leave,
    )

    def guarded(action):
        """Führt eine Navigation aus; bei ungespeicherten Änderungen erst
        nach Rückfrage."""
        if not is_dirty():
            action()
            return

        pending_leave["action"] = action
        leave_dialog.open()

    def handle_key(event):
        if not event.action.keydown or event.action.repeat:
            return

        if event.key.enter and event.modifiers.ctrl:
            save(verify=True)

    # ignore=[]: Strg+Enter soll auch beim Tippen in Feldern greifen
    # (kollidiert nicht mit Texteingabe).
    ui.keyboard(on_key=handle_key, ignore=[])

    def handle_navigation_keys(event):
        if not event.action.keydown or event.action.repeat:
            return

        if event.key.escape:
            guarded(lambda: ui.navigate.to("/dokumente"))

        elif event.key.arrow_right:
            guarded(lambda: navigate_adjacent(1))

        elif event.key.arrow_left:
            guarded(lambda: navigate_adjacent(-1))

    # Eigene Tastatur mit Standard-ignore (input/textarea/…): Escape und
    # Pfeiltasten navigieren nur, wenn der Fokus NICHT in einem Eingabefeld
    # ist — mitten im Tippen wäre das Datenverlust (Review P3). Zusätzlich
    # fragt guarded() bei ungespeicherten Änderungen nach.
    ui.keyboard(on_key=handle_navigation_keys)

    @ui.refreshable
    def form_area():
        inputs.clear()
        initial_values.clear()

        _render_type_selects(state, change_type, change_subtype)

        subtype = state["subtype"] or None
        missing = set(missing_required_fields(state["document_type"], data, subtype))
        empty = set(empty_fields(state["document_type"], data, subtype))

        if missing:
            ui.label(
                f"⚠️ {len(missing)} Pflichtfeld(er) leer — bitte aus dem Dokument"
                " ergänzen."
            ).classes("text-sm text-orange-700")

        for field in form_fields(state["document_type"], subtype):
            element, default = _render_field(
                field,
                data,
                missing,
                empty,
                lambda: tax_relevant_checkbox.set_value(True),
            )

            inputs[field["key"]] = element
            initial_values[field["key"]] = default

    def refresh_tax_relevance_default():
        # Nach Typ-/Subtypwechsel gilt ein anderer Steuerrelevanz-Default
        # (Review P3) — die Checkbox folgt ihm; der Nutzer kann weiterhin
        # umschalten, bevor er speichert.
        tax_relevant_checkbox.value = default_tax_relevance(
            state["document_type"],
            {**data, "document_subtype": state["subtype"] or None},
        )

    def change_type(document_type):
        state["document_type"] = document_type
        sub_config = subtype_config(document_type)
        current = data.get("document_subtype", "")

        # Beim Typwechsel den Bestandssubtyp behalten, falls der neue Typ
        # Subtypen kennt; sonst zurücksetzen.
        state["subtype"] = current if sub_config else ""

        if sub_config and not current:
            state["subtype"] = sub_config["options"][0]

        refresh_tax_relevance_default()
        form_area.refresh()

    def change_subtype(subtype):
        state["subtype"] = subtype
        refresh_tax_relevance_default()
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
        # Kopf: Titel, darunter EINE Meta-/Aktionszeile (klein): links
        # ID · Typ · Status · ←/→, rechts die Aktionen — lange Titel brechen
        # so nicht mehr um und die Aktionen gehören sichtbar zur ganzen Seite.
        with ui.column().classes("gap-0 w-full"):
            ui.label(display_name).classes("text-3xl page-title")

            _meta_row(
                document_id,
                type_label,
                status_text,
                downloadable=Path(document["archive_path"]).exists(),
                verified=document["verified"],
                actions={
                    "previous": lambda: guarded(lambda: navigate_adjacent(-1)),
                    "next": lambda: guarded(lambda: navigate_adjacent(1)),
                    "download": lambda: ui.download(document["archive_path"]),
                    "reanalyze": reanalyze_dialog.open,
                    "unverify": unverify,
                    "delete": delete_dialog.open,
                },
            )

        with ui.row().classes("w-full gap-6 flex-nowrap items-start"):
            # Links: Formular + Aktionen + Notizen
            with card("w-1/2 gap-3"):
                # Vor dem Formular: wer gleich freigeben will, soll vorher
                # wissen, dass derselbe Beleg schon im Bestand liegt.
                _duplicate_hint(document_id)

                form_area()

                tax_relevant_checkbox = ui.checkbox(
                    "Steuerrelevant",
                    value=initial_tax_relevant,
                )
                ui.label(
                    "Vorbelegt aus Art/Unterart — bei Bedarf ändern "
                    "(z. B. absetzbare Rechnung)."
                ).classes("text-xs muted")

                # Steuerlicher Zweck: kennzeichnet Rechnungs-Belege für die
                # Belegsummen-Positionen der Steuer-Seite (Anlage N / agB).
                # Nur bei Rechnungen (andere Typen haben eigene Steuerwege)
                # und nur sichtbar, wenn das Dokument steuerrelevant ist.
                tax_purpose_select = None

                if state["document_type"] == INVOICE:
                    with ui.column().classes("gap-0").bind_visibility_from(
                        tax_relevant_checkbox, "value"
                    ):
                        tax_purpose_select = ui.select(
                            {"": "—", **TAX_PURPOSE_LABELS},
                            label="Steuerlicher Zweck (Beleg)",
                            value=document["tax_purpose"] or "",
                        ).props("dense").classes("w-64")
                        ui.label(
                            "Der Betrag fließt als Belegsumme in die "
                            "gewählte Anlage ein."
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
                    "Esc = zurück zur Liste · ←/→ = vorheriges/nächstes Dokument"
                ).classes("text-xs muted")

                notes_area = ui.textarea(
                    "📝 Notizen",
                    value=document["notes"] or "",
                ).classes("w-full")

            # Rechts: Quelle des Dokuments (PDF oder OCR-Text).
            with card("w-1/2 gap-2"):
                _source_panel(document_id, document["document_text"])
