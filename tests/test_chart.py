"""SVG-Liniendiagramm (frontend/chart.py). Alle Zahlen erfunden."""

from src.frontend.chart import line_chart_svg


def series(values, label="Brutto", color="#0081a7"):
    return {"label": label, "color": color, "values": values}


def test_empty_series_yields_empty_string():
    assert line_chart_svg([series({})]) == ""
    assert line_chart_svg([]) == ""


def test_line_markers_labels_and_tooltip():
    svg = line_chart_svg(
        [series({2022: 28000.0, 2023: 31000.0, 2024: 33500.0})]
    )

    assert svg.startswith("<svg")
    assert "<polyline" in svg
    assert svg.count("<circle") == 3
    # Tooltip mit Jahr, Serienname und Euro-Betrag.
    assert "<title>2023 · Brutto: 31.000,00 €</title>" in svg
    # Direktbeschriftung am Linienende und Jahre an der X-Achse.
    assert ">Brutto</text>" in svg
    assert ">2022</text>" in svg


def test_gap_year_breaks_the_line():
    # 2023 fehlt: kein stilles Interpolieren über das Lückenjahr.
    svg = line_chart_svg(
        [series({2021: 1000.0, 2022: 1200.0, 2024: 1400.0, 2025: 1500.0})]
    )

    # Zwei getrennte Linienzüge statt einer durchgezogenen Linie.
    assert svg.count("<polyline") == 2


def test_short_label_wins_at_the_line_end():
    svg = line_chart_svg(
        [
            {
                "label": "rechnerisches Netto",
                "short": "Netto",
                "color": "#008300",
                "values": {2022: 1.0, 2023: 2.0},
            }
        ]
    )

    assert ">Netto</text>" in svg
    assert ">rechnerisches Netto</text>" not in svg


def test_single_year_renders_marker_without_line():
    svg = line_chart_svg([series({2024: 30000.0})])

    assert "<polyline" not in svg
    assert svg.count("<circle") == 1


def test_series_color_is_used_for_line_not_for_text():
    svg = line_chart_svg(
        [series({2022: 1.0, 2023: 2.0}, color="#0081a7")]
    )

    assert 'stroke="#0081a7"' in svg
    # Beschriftung bleibt in Textfarbe (nie in Serienfarbe).
    assert 'fill="#0081a7">Brutto' not in svg
