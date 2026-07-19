"""Text aus PDFs mit eingebettetem Text — layouttreu rekonstruiert.

pypdf lieferte den Text in der Druck-Reihenfolge des Content-Streams. Bei
Formularen (z. B. der elektronischen Lohnsteuerbescheinigung) stehen dort
erst alle Beschriftungen und dann — losgelöst — alle Werte: kein Parser und
kein LLM kann die Beträge den Zeilen zuordnen. Stattdessen lesen wir die
Zeichen mit ihren Positionen (pypdfium2), clustern sie nach Y zu visuellen
Zeilen und sortieren nach X — Beschriftung und Wert stehen wieder zusammen.

Spaltensprünge werden als DOPPEL-Leerzeichen markiert, damit Regelparser
Label- und Wertespalte trennen können.
"""

import pypdfium2 as pdfium

from src.core.logger import logger

# Ein Zeichen gehört zur aktuellen Zeile, wenn sich sein vertikaler Bereich
# ausreichend mit dem der Zeile überlappt. Absichtlich Überlappung statt
# Mittelpunkt-Abstand: Glyph-Boxen sind unterschiedlich hoch („M" vs. „e",
# Unterlängen wie „g"), die Mittelpunkte einer Zeile streuen deshalb stark.
_MIN_OVERLAP_RATIO = 0.5

# Horizontale Lücken relativ zur Zeichenhöhe: ab _SPACE_RATIO ein
# Leerzeichen, ab _COLUMN_RATIO ein Spaltensprung (Doppel-Leerzeichen).
# Ziffern/Punkt/Komma haben schmale Glyph-Boxen und dadurch scheinbar
# große Lücken — innerhalb von Zahlen gilt die höhere Schwelle, damit
# Beträge nicht auseinandergerissen werden.
_SPACE_RATIO = 0.34
_DIGIT_SPACE_RATIO = 0.9
_COLUMN_RATIO = 2.0


def _is_number_char(char):
    return char.isdigit() or char in ".,"


def lines_from_chars(chars):
    """Visuelle Zeilen aus positionierten Zeichen.

    chars: Iterable von (left, bottom, right, top, zeichen) in
    PDF-Koordinaten (Y wächst nach oben). Liefert die Zeilen von oben nach
    unten, innerhalb der Zeile von links nach rechts.
    """
    items = sorted(chars, key=lambda c: (-(c[1] + c[3]) / 2, c[0]))

    raw_lines = []
    current = []
    # Referenzbox der Zeile als laufender MITTELWERT der Zeichenboxen —
    # bewusst keine wachsende Hülle: die würde bei eng gesetzten
    # Formular-Doppelzeilen die nächste Zeile „einfangen" (Verkettung).
    line_bottom = line_top = None

    for left, bottom, right, top, char in items:
        height = max(top - bottom, 1.0)

        if current:
            overlap = min(line_top, top) - max(line_bottom, bottom)

        if current and overlap > _MIN_OVERLAP_RATIO * min(
            height, max(line_top - line_bottom, 1.0)
        ):
            current.append((left, bottom, right, top, char))
            count = len(current)
            line_bottom += (bottom - line_bottom) / count
            line_top += (top - line_top) / count

        else:
            if current:
                raw_lines.append(current)

            current = [(left, bottom, right, top, char)]
            line_bottom, line_top = bottom, top

    if current:
        raw_lines.append(current)

    lines = []

    for raw in raw_lines:
        raw.sort(key=lambda c: c[0])
        text = ""
        previous_right = None
        previous_char = ""

        for left, bottom, right, top, char in raw:
            height = max(top - bottom, 1.0)

            if previous_right is not None:
                gap = left - previous_right
                in_number = _is_number_char(previous_char) and _is_number_char(char)
                space_ratio = _DIGIT_SPACE_RATIO if in_number else _SPACE_RATIO

                if gap > _COLUMN_RATIO * height:
                    text += "  "

                elif gap > space_ratio * height:
                    text += " "

            text += char
            previous_right = right
            previous_char = char

        if text.strip():
            lines.append(text.rstrip())

    return lines


def _page_chars(textpage):
    for index in range(textpage.count_chars()):
        char = textpage.get_text_range(index, 1)

        if not char or not char.strip():
            continue

        left, bottom, right, top = textpage.get_charbox(index)
        yield (left, bottom, right, top, char)


def has_text(pdf_path):
    pdf = pdfium.PdfDocument(pdf_path)

    try:
        for page in pdf:
            textpage = page.get_textpage()
            count = textpage.count_chars()

            if count and textpage.get_text_range(0, count).strip():
                return True

    finally:
        pdf.close()

    return False


def extract_text(pdf_path):
    logger.info(f"PDF wird gelesen: {pdf_path}")

    pdf = pdfium.PdfDocument(pdf_path)
    text = ""

    try:
        for page in pdf:
            lines = lines_from_chars(_page_chars(page.get_textpage()))
            text += "\n".join(lines) + "\n"

    finally:
        pdf.close()

    logger.info(f"Textextraktion abgeschlossen: {pdf_path}")

    return text
