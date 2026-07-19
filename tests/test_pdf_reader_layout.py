"""Layouttreue Zeilen-Rekonstruktion aus positionierten Zeichen."""

from src.ocr.pdf_reader import lines_from_chars


def char(x, ch, y=0.0, width=5.0, height=10.0):
    return (x, y, x + width, y + height, ch)


def test_words_and_columns_on_one_line():
    chars = [
        char(0, "A"),
        char(5.2, "b"),          # Kerning-Lücke: kein Leerzeichen
        char(14, "c"),           # Wortlücke (0.4 * Höhe): Leerzeichen
        char(60, "X"),           # Spaltensprung (> 2 * Höhe): Doppel-Leerzeichen
    ]

    assert lines_from_chars(chars) == ["Ab c  X"]


def test_digits_are_not_torn_apart():
    # Schmale Ziffern-Glyphen erzeugen scheinbar große Lücken — innerhalb
    # von Zahlen gilt die höhere Schwelle.
    chars = [
        char(0, "7", width=2.0),
        char(7, "4", width=2.0),   # Lücke 5 pt = 0.5 * Höhe: KEIN Leerzeichen
        char(19, "0", width=2.0),  # Lücke 10 pt = 1.0 * Höhe: Leerzeichen (Cent-Spalte)
        char(24, "9", width=2.0),
    ]

    assert lines_from_chars(chars) == ["74 09"]


def test_lines_ordered_top_to_bottom_and_sorted_by_x():
    chars = [
        char(0, "u", y=-20),
        char(10, "b"),
        char(0, "o"),
    ]

    assert lines_from_chars(chars) == ["o b", "u"]


def test_slight_baseline_wobble_stays_one_line():
    chars = [
        char(0, "a", y=0.0),
        char(10, "b", y=1.5),  # innerhalb der Toleranz
    ]

    assert lines_from_chars(chars) == ["a b"]
