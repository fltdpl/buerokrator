"""Liniendiagramm als Inline-SVG — ohne Chart-Bibliothek.

Bewusste Entscheidung: für einfache Jahresreihen keine neue Abhängigkeit
(NiceGUI bündelt selbst keine Chart-Bibliothek; ui.echart bräuchte ein
Zusatzpaket). Der Bau ist eine reine Funktion Daten → SVG-String und damit
ohne Browser testbar. Farben kommen aus theme.py.

Gestaltungsregeln (dataviz-Checkliste): dünne Linien (2px), Marker mit
Tooltip (<title>), zurückhaltendes Gitter, EINE Y-Achse ab 0,
Direktbeschriftung am Linienende in Textfarbe (nie in Serienfarbe),
Lückenjahre unterbrechen die Linie statt zu interpolieren.
"""

from src.frontend.theme import CHART_GRID, INK_MUTED


def _euro(value, cents=True):
    pattern = f"{value:,.2f}" if cents else f"{value:,.0f}"
    return pattern.replace(",", "X").replace(".", ",").replace("X", ".")


def _nice_step(raw):
    """Runde Schrittweite (1/2/2,5/5 × 10^k) für ~4 Y-Achsen-Ticks."""
    if raw <= 0:
        return 1.0

    magnitude = 10 ** len(str(int(raw))) / 10

    for factor in (1, 2, 2.5, 5, 10):
        if factor * magnitude >= raw:
            return factor * magnitude

    return 10 * magnitude


def line_chart_svg(series, *, width=760, height=340):
    """SVG-Liniendiagramm über Jahre.

    series: Liste von {"label": str, "color": str, "values": {jahr: wert}};
    optional "short" als kurze Direktbeschriftung am Linienende (sonst
    label). X-Positionen sind linear in der Jahreszahl — ein fehlendes
    Kalenderjahr unterbricht die Linie, statt still zu interpolieren.
    """
    years = sorted({year for s in series for year in s["values"]})

    if not years:
        return ""

    top, right, bottom, left = 14, 120, 30, 78
    plot_w = width - left - right
    plot_h = height - top - bottom

    max_value = max(
        (value for s in series for value in s["values"].values()), default=0.0
    )
    step = _nice_step(max(max_value, 1.0) / 4)
    y_max = step * max(1, -(-max(max_value, 1.0) // step))  # aufrunden

    def x_pos(year):
        if years[-1] == years[0]:
            return left + plot_w / 2

        return left + plot_w * (year - years[0]) / (years[-1] - years[0])

    def y_pos(value):
        return top + plot_h * (1 - value / y_max)

    parts = [
        f'<svg viewBox="0 0 {width} {height}" role="img" '
        f'style="width:100%;max-width:{width}px;height:auto" '
        f'font-size="12">'
    ]

    # Y-Gitter + Beschriftung (Euro ohne Cent, rechtsbündig vor der Linie).
    tick = 0.0

    while tick <= y_max:
        y = y_pos(tick)
        parts.append(
            f'<line x1="{left}" y1="{y:.1f}" x2="{width - right}" '
            f'y2="{y:.1f}" stroke="{CHART_GRID}" stroke-width="1"/>'
        )
        parts.append(
            f'<text x="{left - 8}" y="{y + 4:.1f}" text-anchor="end" '
            f'fill="{INK_MUTED}">{_euro(tick, cents=False)} €</text>'
        )
        tick += step

    # X-Beschriftung: jedes Datenjahr.
    for year in years:
        parts.append(
            f'<text x="{x_pos(year):.1f}" y="{height - 8}" '
            f'text-anchor="middle" fill="{INK_MUTED}">{year}</text>'
        )

    # Linien: lückenlose Kalenderjahr-Läufe je Serie; ein fehlendes Jahr
    # unterbricht die Linie (keine stille Interpolation über die Lücke).
    end_labels = []

    for s in series:
        segments = []
        current = []

        for year in sorted(s["values"]):
            if current and year != current[-1] + 1:
                segments.append(current)
                current = []

            current.append(year)

        if current:
            segments.append(current)

        for segment in segments:
            if len(segment) > 1:
                points = " ".join(
                    f"{x_pos(year):.1f},{y_pos(s['values'][year]):.1f}"
                    for year in segment
                )
                parts.append(
                    f'<polyline points="{points}" fill="none" '
                    f'stroke="{s["color"]}" stroke-width="2" '
                    'stroke-linejoin="round"/>'
                )

        for year in s["values"]:
            value = s["values"][year]
            parts.append(
                f'<circle cx="{x_pos(year):.1f}" cy="{y_pos(value):.1f}" '
                f'r="4" fill="{s["color"]}" stroke="#ffffff" '
                'stroke-width="1.5">'
                f"<title>{year} · {s['label']}: {_euro(value)} €</title>"
                "</circle>"
            )

        last_year = max(s["values"])
        end_labels.append(
            [
                y_pos(s["values"][last_year]),
                x_pos(last_year),
                s.get("short") or s["label"],
            ]
        )

    # Direktbeschriftung am Linienende — in Textfarbe, nicht in Serienfarbe;
    # bei nahen Endpunkten vertikal auseinandergeschoben.
    end_labels.sort()

    for index, label in enumerate(end_labels):
        if index and label[0] - end_labels[index - 1][0] < 15:
            label[0] = end_labels[index - 1][0] + 15

    for y, x, text in end_labels:
        parts.append(
            f'<text x="{x + 10:.1f}" y="{y + 4:.1f}" '
            f'fill="{INK_MUTED}">{text}</text>'
        )

    parts.append("</svg>")

    return "".join(parts)
