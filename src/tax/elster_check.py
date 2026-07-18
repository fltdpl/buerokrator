"""Golden-Master-Abgleich der ELSTER-Zuordnung (framework-frei, testbar).

Vergleicht das Ergebnis von build_elster_summary mit einer lokalen
Erwartungsdatei (Werte aus der tatsächlich abgegebenen Steuererklärung).
Siehe Vertrauens-Workflow in docs/05_Steuerlogik.md: jede Differenz wird
mit Beleg-Herleitung gelistet und muss erklärt werden (App-Fehler,
fehlender Beleg oder Lücke in der damaligen Erklärung) — erst dann gilt
das Jahr als abgenommen.

Die Erwartungsdatei enthält echte Steuerdaten und ist gitignored
(tax_expected_*.yaml).
"""

from src.tax.elster_mapping import build_elster_summary

# Cent-genau: Rundungsdifferenzen unter einem halben Cent gelten als gleich.
TOLERANCE = 0.005


def compare_year(year: int, expected: dict, documents=None) -> dict:
    """Vergleicht die Anlagen-Positionen eines Jahres mit den Erwartungen.

    expected: {anlage_key: {position_key: betrag}} — nur enthaltene
    Positionen werden geprüft. Unbekannte Schlüssel sind FEHLER (ein
    Tippfehler darf nicht als „alles ok" durchgehen). Positionen mit
    App-Werten, aber ohne Erwartung, werden als „unchecked" gelistet.
    """
    summary = build_elster_summary(year, documents)

    positions_by_key = {}

    for anlage in summary["anlagen"]:
        for position in anlage["positions"]:
            positions_by_key[(anlage["key"], position["key"])] = (
                anlage,
                position,
            )

    checked = []
    errors = []

    expected = expected if isinstance(expected, dict) else {}

    for anlage_key, entries in expected.items():
        if entries is None:
            # Anlage ohne (einkommentierte) Positionen — z. B. frische
            # Vorlage: nichts zu prüfen, kein Fehler.
            continue

        if not isinstance(entries, dict):
            errors.append(
                f"Anlage '{anlage_key}': erwartet ist ein Mapping "
                "position -> Betrag."
            )
            continue

        for position_key, expected_value in entries.items():
            anlage_position = positions_by_key.get((anlage_key, position_key))

            if anlage_position is None:
                errors.append(
                    f"Unbekannte Position '{anlage_key}.{position_key}' "
                    "in der Erwartungsdatei (Tippfehler?)."
                )
                continue

            anlage, position = anlage_position

            try:
                expected_amount = float(expected_value)

            except (TypeError, ValueError):
                errors.append(
                    f"'{anlage_key}.{position_key}': Erwartungswert "
                    f"'{expected_value}' ist keine Zahl."
                )
                continue

            checked.append(
                {
                    "anlage": anlage["label"],
                    "key": f"{anlage_key}.{position_key}",
                    "label": position["label"],
                    "expected": expected_amount,
                    "actual": position["amount"],
                    "ok": abs(position["amount"] - expected_amount) < TOLERANCE,
                    "status": position["status"],
                    "documents": position["documents"],
                    "pending": position["pending"],
                    "missing_value": position["missing_value"],
                    "unclear": position["unclear"],
                }
            )

    checked_keys = {entry["key"] for entry in checked}

    # Positionen mit App-Befund, aber ohne Erwartung: ausweisen, damit die
    # Abnahme nichts übersieht (z. B. eine Position, die Taxfix nicht kannte).
    unchecked = [
        {
            "key": f"{anlage['key']}.{position['key']}",
            "label": position["label"],
            "actual": position["amount"],
            "status": position["status"],
        }
        for (anlage_key, position_key), (anlage, position) in positions_by_key.items()
        if f"{anlage_key}.{position_key}" not in checked_keys
        and position["status"] != "empty"
    ]

    return {
        "year": year,
        "checked": checked,
        "unchecked": unchecked,
        "errors": errors,
        "ok": bool(checked)
        and not errors
        and all(entry["ok"] for entry in checked),
    }


def _format_references(title, references):
    if not references:
        return []

    lines = [f"      {title}:"]

    for ref in references:
        amount = "—" if ref["amount"] is None else f"{ref['amount']:.2f} €"
        issuer = ref.get("issuer") or "?"
        lines.append(
            f"        • [{ref['id']}] {issuer} · {ref['filename']} · {amount}"
        )

    return lines


def format_report(report: dict) -> str:
    """Textreport: OK/DIFF je Position, Herleitung bei jeder Differenz."""
    lines = [f"ELSTER-Abgleich Steuerjahr {report['year']}", ""]

    for error in report["errors"]:
        lines.append(f"FEHLER: {error}")

    if report["errors"]:
        lines.append("")

    if not report["checked"]:
        lines.append("Keine Positionen geprüft — Erwartungsdatei leer?")

    current_anlage = None

    for entry in report["checked"]:
        if entry["anlage"] != current_anlage:
            current_anlage = entry["anlage"]
            lines.append(f"{current_anlage}")

        marker = "OK  " if entry["ok"] else "DIFF"
        lines.append(
            f"  {marker}  {entry['label']}: "
            f"erwartet {entry['expected']:.2f} €, "
            f"App {entry['actual']:.2f} €"
        )

        if not entry["ok"] or entry["status"] != "ready":
            lines.extend(_format_references("Belege", entry["documents"]))
            lines.extend(
                _format_references("Ungeprüft (zählen nicht)", entry["pending"])
            )
            lines.extend(
                _format_references("Geprüft ohne Wert", entry["missing_value"])
            )
            lines.extend(_format_references("Unklare Art", entry["unclear"]))

    if report["unchecked"]:
        lines.append("")
        lines.append("Ohne Erwartungswert (bitte ergänzen oder bewusst auslassen):")

        for entry in report["unchecked"]:
            lines.append(
                f"  ?    {entry['label']}: App {entry['actual']:.2f} € "
                f"[{entry['status']}]"
            )

    lines.append("")
    lines.append(
        "ERGEBNIS: ABGENOMMEN — alle geprüften Positionen stimmen."
        if report["ok"]
        else "ERGEBNIS: NICHT abgenommen — Differenzen/Fehler erklären "
        "(App-Fehler? Beleg fehlt? Damalige Erklärung unvollständig?)."
    )

    return "\n".join(lines)


def build_template(year: int, documents=None) -> str:
    """YAML-Vorlage mit allen Positions-Schlüsseln, Werte bewusst LEER.

    Die Erwartungswerte kommen aus der abgegebenen Erklärung — eine mit
    App-Werten vorbefüllte Vorlage würde den Abgleich entwerten
    (Bestätigungsfehler).
    """
    summary = build_elster_summary(year, documents)

    lines = [
        f"# Erwartete ELSTER-Werte für {year} — Quelle: abgegebene",
        "# Steuererklärung (z. B. Taxfix-PDF/Bescheid), NICHT die App.",
        "# Zeilen einkommentieren und Betrag eintragen; auskommentierte",
        "# Positionen werden nicht geprüft.",
        "# Diese Datei enthält echte Steuerdaten und bleibt lokal (gitignored).",
    ]

    for anlage in summary["anlagen"]:
        lines.append("")
        lines.append(f"{anlage['key']}:  # {anlage['label']}")

        for position in anlage["positions"]:
            lines.append(f"  # {position['label']}")
            lines.append(f"  # {position['key']}: 0.00")

    return "\n".join(lines) + "\n"
