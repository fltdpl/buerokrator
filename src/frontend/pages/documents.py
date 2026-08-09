import html

from nicegui import ui

from src.core.document_types import DOCUMENT_TYPES, DOCUMENT_TYPE_LABELS
from src.database.export_csv import export_documents_csv
from src.database.list_documents import list_documents
from src.database.search import SNIPPET_CLOSE, SNIPPET_OPEN, search_documents
from src.database.statistics import get_verification_statistics
from src.frontend.layout import card, format_euro, page_layout
from src.frontend.theme import tag_color
from src.frontend.listing_order import set_listing_order
from src.services.document_service import (
    available_years,
    build_table_rows,
    filter_documents,
    move_documents_to_trash,
    reclassify_documents,
    revoke_documents_verification,
    set_documents_issuer,
    set_documents_subtype,
)
from src.services.form_schema import subtype_config
from src.services.tag_service import (
    add_tag_to_documents,
    list_tags,
    remove_tag_from_documents,
)

COLUMNS = [
    {"name": "id", "label": "ID", "field": "id", "sortable": True, "align": "left"},
    {"name": "status", "label": "Status", "field": "status", "sortable": True, "align": "left"},
    {"name": "year", "label": "Jahr", "field": "year", "sortable": True, "align": "left"},
    {"name": "art_label", "label": "Dokument", "field": "art_label", "sortable": True, "align": "left"},
    {"name": "category", "label": "Kategorie", "field": "category", "sortable": True, "align": "left"},
    {"name": "issuer", "label": "Aussteller", "field": "issuer", "sortable": True, "align": "left"},
    {"name": "amount", "label": "Betrag", "field": "amount", "sortable": True, "align": "right", ":sort": "(a, b, rowA, rowB) => (rowA.amount_raw ?? -1) - (rowB.amount_raw ?? -1)"},
    {"name": "created_at", "label": "Importiert", "field": "created_at", "sortable": True, "align": "left"},
]

# Nur während einer Volltextsuche eingeblendet: ohne Suchbegriff gäbe es
# nichts zu zeigen, und die Liste ist schon breit genug.
SNIPPET_COLUMN = {
    "name": "text_snippet",
    "label": "Fundstelle",
    "field": "text_snippet",
    "sortable": False,
    "align": "left",
}

# Zelle mit v-html, weil die Fundstelle die Hervorhebung als Markup trägt.
# Sicher, weil _snippet_html den Text vorher escaped — siehe dort.
_SNIPPET_CELL = """
<q-td :props="props" style="white-space: normal; max-width: 28rem;">
    <span v-html="props.row.text_snippet"></span>
</q-td>
"""


# Zelle „Dokument": Bezeichnung, darunter die Tags. Bewusst KEINE eigene
# Spalte — die Liste führt schon acht, und drei Tags je Zeile brächen sie um.
#
# `@click.stop` ist nicht kosmetisch: ohne das Stoppen löst der Klick
# zusätzlich den Zeilenklick aus und öffnet die Detailansicht, statt zu
# filtern. Das Ereignis geht über $parent an die Tabelle, wo die Seite es
# mit `table.on("tagClick", …)` abholt.
_ART_LABEL_CELL = """
<q-td :props="props" style="white-space: normal;">
    <div>{{ props.row.art_label }}</div>
    <div v-if="props.row.tags.length" class="row items-center q-gutter-xs q-mt-xs">
        <q-chip v-for="tag in props.row.tags" :key="tag.name"
                dense clickable icon="circle" class="tag-chip"
                :style="'--tag-color:' + tag.color"
                @click.stop="() => $parent.$emit('tagClick', tag.name)">
            {{ tag.name }}
        </q-chip>
    </div>
</q-td>
"""


def _snippet_html(snippet):
    """Fundstelle als sicheres HTML mit hervorgehobenem Suchbegriff.

    Der Text stammt aus fremden PDFs und darf nie als Markup gelesen werden.
    Deshalb erst alles escapen, dann die Hervorhebung an den Steuerzeichen
    setzen, die die Suche gesetzt hat — sie überstehen das Escaping
    unverändert und können im Originaltext nicht vorkommen.
    """
    if not snippet:
        return ""

    return (
        html.escape(snippet)
        .replace(SNIPPET_OPEN, "<mark>")
        .replace(SNIPPET_CLOSE, "</mark>")
    )


def _truncate(text, max_length):
    """Kürzt zu lange Zelleninhalte mit Auslassungszeichen."""
    text = text or ""

    if len(text) <= max_length:
        return text

    return text[: max_length - 1].rstrip() + "…"


def _table_rows(documents):
    rows = []

    for row in build_table_rows(documents):
        rows.append(
            {
                "id": row["id"],
                # In der Zeile mitgeführt (keine eigene Spalte): die
                # Bulk-Aktion „Unterart setzen" braucht den Typ der Auswahl.
                "document_type": row["document_type"],
                # Emoji + Text: Status auch ohne Farb-/Emoji-Darstellung lesbar.
                "status": "🟢 Geprüft" if row["verified"] else "🟡 Ungeprüft",
                "year": str(row["year"]) if row["year"] else "-",
                "art_label": _truncate(row["art_label"], 45),
                "category": DOCUMENT_TYPE_LABELS.get(
                    row["document_type"], row["document_type"]
                ),
                "issuer": _truncate(row["issuer"], 35),
                "amount": format_euro(row["amount"]) if row["amount"] is not None else "",
                "amount_raw": row["amount"],
                "created_at": row["created_at"],
                "text_snippet": _snippet_html(row["text_snippet"]),
                # Die Farb-Nummer wird erst hier zur Farbe: die Palette
                # gehört dem Theme, nicht der Dienstschicht.
                "tags": [
                    {"name": tag["name"], "color": tag_color(tag["color_index"])}
                    for tag in row["tags"]
                ],
            }
        )

    return rows


def _default_filters():
    return {
        "search": "",
        "type": "Alle",
        "subtype": "Alle",
        "status": "Alle",
        "year_range": None,
        "issuer": "",
        "filename": "",
        # Mehrere Tags gelten zusammen (UND) — Tags verengen die Suche.
        "tags": [],
    }


# Modul-global: die Filter bleiben beim Wechsel in die Detailansicht und zurück
# erhalten (überleben Navigation, setzen sich beim App-Neustart zurück). Für
# den lokalen Ein-Nutzer-Betrieb bewusst einfach gehalten.
_FILTER_STATE = _default_filters()


def _bulk_actions(table, on_changed):
    """Aktionen für die ausgewählten Zeilen (nur sichtbar, wenn ausgewählt).

    Braucht aus der Seite nur die Tabelle und einen Rückruf, der die
    Ergebnisliste neu aufbaut — deshalb hier auf Modulebene statt als
    Closure im Seitenkörper.
    """
    def selected_ids():
        return [row["id"] for row in table.selected]

    def delete_selected():
        deleted = move_documents_to_trash(selected_ids())
        delete_dialog.close()
        ui.notify(f"{deleted} Dokument(e) in den Papierkorb verschoben.")
        on_changed()

    def reclassify_selected(document_type):
        if not document_type:
            ui.notify("Bitte eine Kategorie wählen.")
            return

        changed = reclassify_documents(selected_ids(), document_type)
        ui.notify(
            f"{changed} Dokument(e) auf "
            f"{DOCUMENT_TYPE_LABELS.get(document_type, document_type)} gesetzt "
            "und zum erneuten Prüfen markiert."
        )
        on_changed()

    def unify_issuer(name):
        if not (name or "").strip():
            ui.notify("Bitte einen Aussteller-Namen eingeben.")
            return

        changed = set_documents_issuer(selected_ids(), name)
        ui.notify(
            f"Aussteller von {changed} Dokument(en) auf "
            f"„{name.strip()}“ vereinheitlicht."
        )
        on_changed()

    def revoke_selected():
        changed = revoke_documents_verification(selected_ids())
        ui.notify(
            f"Freigabe von {changed} Dokument(en) widerrufen — "
            "sie stehen wieder zur Prüfung an."
        )
        on_changed()

    def selected_types():
        types = {row.get("document_type") for row in table.selected}
        types.discard(None)
        return types

    def apply_tag(name, entfernen=False):
        """Ein Tag an die Auswahl hängen oder von ihr nehmen.

        Ergänzend statt ersetzend: die Auswahl trägt in der Regel schon
        Verschiedenes, und ein Stapelbefehl darf das nicht wegwischen.
        """
        try:
            if entfernen:
                geaendert = remove_tag_from_documents(selected_ids(), name)

            else:
                geaendert = add_tag_to_documents(selected_ids(), name)

        except ValueError as fehler:
            ui.notify(str(fehler), type="negative")
            return

        if entfernen:
            ui.notify(f"Tag von {geaendert} Dokument(en) entfernt.")

        else:
            ui.notify(f"Tag an {geaendert} Dokument(e) vergeben.")

        on_changed()

    def apply_subtype(subtype):
        if not subtype:
            ui.notify("Bitte eine Unterart wählen.")
            return

        changed = set_documents_subtype(selected_ids(), subtype)
        ui.notify(
            f"{changed} Dokument(e) auf Unterart gesetzt "
            "und zum erneuten Prüfen markiert."
        )
        on_changed()

    with ui.dialog() as delete_dialog, ui.card():
        confirm_label = ui.label("")

        with ui.row().classes("justify-end w-full"):
            ui.button("Abbrechen", on_click=delete_dialog.close).props("flat")
            ui.button("Ja, löschen", on_click=delete_selected).props(
                "color=negative"
            )

    def open_delete_dialog():
        confirm_label.text = (
            f"{len(table.selected)} Dokument(e) in den Papierkorb verschieben?"
        )
        delete_dialog.open()

    # Reklassifizieren: Kategorie wählen + Anwenden.
    reclassify_choice = {"value": None}

    # Unterart setzen: die Optionen richten sich nach der Kategorie der
    # Auswahl (nur sinnvoll bei einheitlichem Typ). Refresh via table.on
    # ("selection") unten.
    @ui.refreshable
    def subtype_bulk():
        types = selected_types()

        if len(types) != 1:
            ui.label(
                "Unterart: erst eine einheitliche Kategorie auswählen."
            ).classes("text-xs muted")
            return

        config = subtype_config(next(iter(types)))
        if not config:
            ui.label("Unterart: diese Kategorie hat keine Unterarten.").classes(
                "text-xs muted"
            )
            return

        options = {
            value: config["labels"].get(value, value)
            for value in config["options"]
        }
        choice = {"value": None}
        select = ui.select(
            options, label="Unterart setzen", with_input=True
        ).props("dense").classes("w-56")
        select.bind_value(choice, "value")
        ui.button(
            "Anwenden", on_click=lambda: apply_subtype(choice["value"])
        ).props("dense unelevated")

    with ui.row().classes("items-center gap-3").bind_visibility_from(
        table, "selected", backward=bool
    ):
        ui.label().bind_text_from(
            table, "selected", lambda rows: f"{len(rows)} ausgewählt"
        ).classes("muted")

        reclass_select = ui.select(
            {dtype: DOCUMENT_TYPE_LABELS.get(dtype, dtype) for dtype in DOCUMENT_TYPES},
            label="Umklassifizieren nach",
        ).props("dense").classes("w-56")
        reclass_select.bind_value(reclassify_choice, "value")
        ui.button(
            "Anwenden",
            on_click=lambda: reclassify_selected(reclassify_choice["value"]),
        ).props("dense unelevated")

        subtype_bulk()

        # Aussteller/Arbeitgeber vereinheitlichen (Kurz- vs. Langname
        # desselben Ausstellers): Prüfstatus und Datei bleiben.
        issuer_input = ui.input("Aussteller vereinheitlichen").props(
            "dense"
        ).classes("w-56")
        ui.button(
            "Anwenden",
            on_click=lambda: unify_issuer(issuer_input.value),
        ).props("dense unelevated")

        # Tag vergeben/entfernen. Ein Auswahlfeld mit Freitext: vorhandene
        # Tags stehen zur Auswahl, ein neuer Name lässt sich eintippen —
        # der Knopf ist dann die ausdrückliche Handlung, die ein Tag anlegt.
        tag_input = ui.select(
            [tag["name"] for tag in list_tags()],
            label="Tag",
            with_input=True,
            new_value_mode="add-unique",
        ).props("dense").classes("w-48").mark("tag-stapel-eingabe")

        ui.button(
            "＋ Vergeben", on_click=lambda: apply_tag(tag_input.value)
        ).props("dense unelevated").mark("tag-stapel-hinzufuegen")

        ui.button(
            "− Entfernen",
            on_click=lambda: apply_tag(tag_input.value, entfernen=True),
        ).props("flat dense").mark("tag-stapel-entfernen")

        # Kein Bestätigungsdialog: der Widerruf ist verlustfrei (Felder
        # bleiben, nur der Prüfstatus fällt) und per Prüfen umkehrbar.
        ui.button("↩ Freigabe widerrufen", on_click=revoke_selected).props(
            "flat dense"
        )

        ui.button("🗑 Auswahl löschen", on_click=open_delete_dialog).props(
            "flat dense color=negative"
        )

    # Optionen der Unterart-Auswahl an die aktuelle Selektion anpassen
    # (feuert, nachdem table.selected aktualisiert wurde).
    table.on_select(lambda event: subtype_bulk.refresh())


@ui.page("/dokumente")
def documents_page():
    filters = _FILTER_STATE

    all_years = available_years(list_documents())

    def filtered_documents():
        documents = (
            search_documents(filters["search"])
            if filters["search"]
            else list_documents()
        )

        year_range = filters["year_range"]
        from_year = to_year = None

        # Jahr-Filter nur anwenden, wenn der Regler nicht die volle
        # Spannweite abdeckt (volle Spannweite = kein Filter).
        if year_range and all_years:
            if year_range["min"] > all_years[0]:
                from_year = int(year_range["min"])

            if year_range["max"] < all_years[-1]:
                to_year = int(year_range["max"])

        return filter_documents(
            documents,
            document_type=None if filters["type"] == "Alle" else filters["type"],
            subtype=None if filters["subtype"] == "Alle" else filters["subtype"],
            verified=None
            if filters["status"] == "Alle"
            else filters["status"] == "Geprüft",
            from_year=from_year,
            to_year=to_year,
            issuer=filters["issuer"],
            filename=filters["filename"],
            tags=filters["tags"],
        )

    @ui.refreshable
    def results():
        documents = filtered_documents()
        rows = _table_rows(documents)

        # Reihenfolge für die Pfeiltasten-Navigation in der Detailansicht.
        set_listing_order([row["id"] for row in rows])

        with ui.row().classes("items-center gap-4 w-full"):
            ui.label(f"{len(rows)} Dokumente gefunden").classes("muted")

            ui.button(
                "📥 CSV Export",
                on_click=lambda: ui.download(
                    export_documents_csv(documents).encode("utf-8"),
                    "buerokrator_export.csv",
                ),
            ).props("flat dense")

        if not rows:
            ui.label("Keine Dokumente gefunden.")
            return

        # Die Fundstelle nur zeigen, wenn wenigstens eine Zeile eine hat:
        # bei kurzen Suchbegriffen (LIKE statt FTS) und bei Treffern rein
        # im Dateinamen bliebe die Spalte sonst durchgehend leer.
        show_snippets = any(row["text_snippet"] for row in rows)

        table = ui.table(
            columns=(COLUMNS + [SNIPPET_COLUMN]) if show_snippets else COLUMNS,
            rows=rows,
            row_key="id",
            pagination=25,
            selection="multiple",
        ).classes("w-full")

        table.add_slot("body-cell-art_label", _ART_LABEL_CELL)

        def filter_by_tag(event):
            """Klick auf ein Tag in der Liste: danach filtern.

            Ergänzend zur bestehenden Auswahl — wer zwei Tags anklickt,
            meint beide zusammen (dieselbe UND-Regel wie im Filterfeld).
            """
            name = event.args

            if name in filters["tags"]:
                return

            filters["tags"] = [*filters["tags"], name]
            filter_bar.refresh()
            results.refresh()

        table.on("tagClick", filter_by_tag)

        if show_snippets:
            table.add_slot("body-cell-text_snippet", _SNIPPET_CELL)

        # Zeilenklick öffnet das Detail; die Auswahl läuft über die Checkbox,
        # damit ein Klick nicht beides bedeutet.
        table.on(
            "rowClick",
            lambda event: ui.navigate.to(f"/dokumente/{event.args[1]['id']}"),
        )

        _bulk_actions(table, results.refresh)

    def set_filter(key, value):
        filters[key] = value
        results.refresh()

    def reset_filters():
        filters.update(_default_filters())
        filter_bar.refresh()
        results.refresh()

    @ui.refreshable
    def filter_bar():
        with ui.row().classes("items-end gap-4 w-full"):
            # debounce: eine DB-Abfrage pro Tipp-Pause statt pro Tastenanschlag.
            ui.input(
                "Volltext",
                value=filters["search"],
                on_change=lambda event: set_filter("search", event.value),
            ).props("dense clearable debounce=400").classes("w-48")

            def set_type_filter(value):
                # Kategoriewechsel: Unterart-Filter zurücksetzen (die Optionen
                # gehören zur Kategorie) und die Leiste neu aufbauen.
                filters["type"] = value
                filters["subtype"] = "Alle"
                filter_bar.refresh()
                results.refresh()

            ui.select(
                {
                    "Alle": "Alle",
                    **{
                        dtype: DOCUMENT_TYPE_LABELS.get(dtype, dtype)
                        for dtype in DOCUMENT_TYPES
                    },
                },
                value=filters["type"],
                label="Kategorie",
                on_change=lambda event: set_type_filter(event.value),
            ).props("dense").classes("w-36")

            # Unterart-Filter nur, wenn die gewählte Kategorie Unterarten hat.
            subtype_filter_config = (
                subtype_config(filters["type"]) if filters["type"] != "Alle" else None
            )

            if subtype_filter_config:
                subtype_options = {
                    "Alle": "Alle",
                    **{
                        value: subtype_filter_config["labels"].get(value, value)
                        for value in subtype_filter_config["options"]
                    },
                }
                ui.select(
                    subtype_options,
                    value=filters["subtype"],
                    label="Unterart",
                    on_change=lambda event: set_filter("subtype", event.value),
                ).props("dense").classes("w-44")

            ui.select(
                ["Alle", "Ungeprüft", "Geprüft"],
                value=filters["status"],
                label="Status",
                on_change=lambda event: set_filter("status", event.value),
            ).props("dense").classes("w-36")

            ui.input(
                "Aussteller",
                value=filters["issuer"],
                on_change=lambda event: set_filter("issuer", event.value),
            ).props("dense clearable debounce=400").classes("w-40")

            ui.input(
                "Dateiname",
                value=filters["filename"],
                on_change=lambda event: set_filter("filename", event.value),
            ).props("dense clearable debounce=400").classes("w-40")

            # Tags: nur zeigen, wenn es welche gibt. Wer sie nicht benutzt,
            # soll den Filter auch nicht sehen — Tags sind keine Pflicht.
            # Anders als der Unterart-Filter bleibt er bei „Kategorie: Alle"
            # stehen: quer über die Kategorien zu suchen IST ihr Zweck.
            alle_tags = [tag["name"] for tag in list_tags()]

            if alle_tags:
                ui.select(
                    alle_tags,
                    value=filters["tags"],
                    label="Tags",
                    multiple=True,
                    on_change=lambda event: set_filter("tags", event.value),
                ).props("dense clearable use-chips").classes("w-56").mark(
                    "tag-filter"
                ).tooltip("Mehrere Tags gelten zusammen")

            if len(all_years) > 1:
                year_range = filters["year_range"] or {
                    "min": all_years[0],
                    "max": all_years[-1],
                }
                with ui.column().classes("w-56 gap-0"):
                    ui.label("Jahre").classes("text-xs muted")
                    ui.range(
                        min=all_years[0],
                        max=all_years[-1],
                        value=year_range,
                        on_change=lambda event: set_filter("year_range", event.value),
                    ).props("label dense")

            ui.button("Filter zurücksetzen", on_click=reset_filters).props(
                "flat dense"
            )

    unverified, verified = get_verification_statistics()

    with page_layout("Dokumente"):
        ui.label("Dokumente").classes("text-3xl page-title")
        ui.label(f"🟡 {unverified} ungeprüft · 🟢 {verified} geprüft").classes("muted")

        with card("w-full"):
            filter_bar()

        with card("w-full"):
            results()
