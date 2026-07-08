# Ordnerstruktur

Archiviert wird nach Jahr und Kategorie; die Kategorienamen kommen aus
`config/settings.yaml` (`archive.category_mapping`):

archive/

- Jahr (= `tax_year` des Dokuments)
    - Rechnungen (invoice)
    - Steuern (tax)
    - Versicherungen (insurance)
    - Vorsorge (pension)
    - Bank (bank)
    - Wohnen (housing)
    - Sonstiges (unknown)

Beispiel:

archive/2026/Steuern/

archive/2026/Vorsorge/

## Begründung

Die Struktur orientiert sich an der späteren Suche
des Benutzers und nicht am Dokumententyp.

Siehe auch [[006_archive_structure]].
