# Ordnerstruktur und Dateinamen

## Archiv

Das Archiv liegt im Verzeichnis der jeweiligen Person
(`profiles/<kennung>/archive/`, siehe
[ADR 015](decisions/015_mehrbenutzer_profile.md)) — auch dann, wenn es nur
eine gibt. Darunter wird nach Jahr und Kategorie archiviert; die
Kategorienamen kommen aus `config/settings.yaml`
(`archive.category_mapping`), das sich alle Personen teilen:

archive/

- Jahr (= `tax_year` des Dokuments)
    - Rechnungen (invoice)
    - Steuern (tax)
    - Versicherungen (insurance)
    - Vorsorge (pension)
    - Bank (bank)
    - Wohnen (housing)
    - Arbeit (employment)
    - Recht (legal)
    - Ausbildung (education)
    - Gesundheit (health)
    - Sonstiges (unknown)

Beispiel:

archive/2026/Steuern/

archive/2026/Vorsorge/

### Begründung

Die Struktur orientiert sich an der späteren Suche
des Benutzers und nicht am Dokumententyp.

Siehe auch [006 Archivstruktur](decisions/006_archive_structure.md).

## Dateinamen

Datum am Anfang, möglichst vollständig; der Aufbau ist **typabhängig**
(`src/organizer/filename_builder.py`):

- Rechnung: `2026-03-11_Musterversand_RE-123_42EUR.pdf`
- Lohnsteuerbescheinigung:
  `2021-01-01_bis_2021-06-30_Arbeitgeber_Lohnsteuerbescheinigung.pdf`
  (mit Bescheinigungszeitraum; ohne: `2024-12_…`)
- Gehaltsabrechnung:
  `2021-01-01_bis_2021-01-31_Arbeitgeber_Gehaltsabrechnung.pdf`
  (Abrechnungszeitraum; Altbestand: `2024-03_…`)
- Typen ohne eigenen Bauer (`unknown`, künftige Typen):
  `2026-03-11_Musterversand_unknown.pdf` über
  `build_fallback_filename` — Datum, Aussteller, Betreff, wobei der
  Typname als Betreff eintritt, wenn keiner erkannt wurde. Vorher hieß
  jedes dieser Dokumente nur nach seinem Typ, also durchweg `unknown.pdf`;
  unterscheidbar waren sie erst über den Kollisionszähler von
  `get_unique_target_path`.

Alle vom Modell gelieferten Werte laufen durch str-Coercion
(`_text_value`), Aussteller zusätzlich durch `normalize_issuer` (die
Aussteller-Aliase, siehe [Architektur](01_Architektur.md)).

**Die Pfadsicherheit sitzt zentral in `_safe_filename`**, angewendet per
`@_sanitized` auf jedem `build_*_filename`. Zusage: der fertige Name ist
garantiert EINE Pfadkomponente — keine Separatoren, keine unter Windows
verbotenen Zeichen, kein führender Punkt, kein Gerätename, nie leer,
maximal 255 Bytes. Feldweise Bereinigung reichte nicht: `document_date`,
`tax_year` und `month` liefen daran vorbei, und `normalize_date` gibt
unparsbare Werte roh zurück — ein `/` darin ließ das Verschieben aus dem
Archiv ausbrechen.

`normalize_date` versteht `DD.MM.YYYY`, zweistellige Jahre, ISO und
ausgeschriebene deutsche Monate über eine eigene Monatstabelle (kein
locale-`%B`: die Locale des Zielsystems ist nicht steuerbar).
**`DD/MM/YYYY` fehlt bewusst** — `01/03/2024` ist zwischen deutschem und
US-Format mehrdeutig, und ein still falsch geratenes Datum wäre schlimmer
als ein unschöner Dateiname.
