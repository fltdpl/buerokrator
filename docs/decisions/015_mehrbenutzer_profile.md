# Entscheidung 015

**Status: Schritte 1–2 gebaut (08.08.2026), Schritte 3–5 offen.** Die
Entscheidungen stehen, der Umsetzungsplan am Ende ist die Bauanleitung.

## Thema

Mehrere Personen eines Haushalts an einer Installation — getrennte
Dokumentenbestände mit einem Profilumschalter in der App

## Entscheidung (08.08.2026)

Ein Haushalt kann mehrere **Profile** anlegen. Jedes Profil hat seinen eigenen
Datenbestand: Datenbank, Archiv, Inbox, Exporte, Papierkorb, Backups und
Aussteller-Aliase. **Gemeinsam bleiben die Einstellungen** — und alles
Weitere, was zur Installation gehört (Log, Setup-Marker, UI-Speicher).

Sechs Festlegungen:

1. **Getrennte Bestände statt Personenspalte.** Kein gemeinsamer Datentopf mit
   einem Feld „Person".
2. **Einstellungen im Basisverzeichnis, Daten im Profil.**
3. **Profilordner tragen eine feste Kennung** (`profiles/1/`), der
   **Anzeigename ist frei änderbar** und steht nur in einer Datei.
4. **Die Profil-Oberfläche erscheint erst ab dem zweiten Profil.** Nach einer
   frischen Installation verhält sich die App exakt wie bisher — kein
   Umschalter, keine Namensanzeige, keine Profildatei.
5. **Der Wechsel ist gesperrt, solange ein Hintergrund-Job läuft.**
6. **Ein Profil entfernen heißt: aus der Liste nehmen.** Nie Dateien löschen.

## Begründung

### Warum getrennte Bestände und keine Personenspalte

Die Alternative wäre ein gemeinsamer Bestand mit einer Spalte `person`. Sie
scheitert an der Steuerschicht: `build_tax_summary` aggregiert über *alle*
Dokumente eines Archivjahres, und `tools/tax_check` vergleicht gegen *eine*
Erklärung. Unverheiratete Paare werden in Deutschland immer getrennt
veranlagt — es gibt also keinen Fall, in dem zwei Bestände zusammen eine
richtige Summe ergäben.

Bei einer Personenspalte müsste jede steuerliche Abfrage korrekt filtern, und
**eine einzige vergessene Stelle addiert zwei Einkommen zu einer Zahl, die es
nirgends gibt — ohne Fehlermeldung.** Das trifft genau das Kernversprechen der
App. Zur Größenordnung: 32 Abfragestellen auf `documents` in 16 Modulen.
Getrennte Bestände machen diesen Fehler baulich unmöglich.

Zweiter Grund: zieht eine Person aus, ist ihr Bestand ein Verzeichnis. Aus
einem gemeinsamen Datentopf müsste man ihn herausoperieren.

### Warum das billig ist

Alle Pfade der App hängen an `get_app_home()`, und nur **sieben Module** rufen
es auf. Die Funktion ist ausdrücklich **ohne Cache** gebaut, damit sie einem
`chdir` folgt (`app_home.py:20-21`). Ein Profilwechsel ist deshalb kein Umbau,
sondern ein anderer Rückgabewert.

### Warum die Einstellungen gemeinsam bleiben

In `config/settings.yaml` steht nichts Personengebundenes: Pfade, Datenbank,
Backup-Ziel, OCR-Sprache und Tesseract-Pfad, Ollama-Modell, Log-Stufe,
unterstützte Dateitypen, Dokumenttypen, Archiv-Kategorien. Zwei Kopien davon
wären zwei Wahrheiten für **eine** Installation: Tesseract zieht um und muss
zweimal nachgetragen werden; ein Moduswechsel beim Modell wirkt nur für eine
Person; eine neue Dokumentkategorie fehlt der anderen.

Personengebunden sind nur die Aussteller-Aliase und die
`tax_expected_<jahr>.yaml` — und beide liegen bei den Daten, nicht in den
Einstellungen.

**Der entscheidende Mechanismus ist schon da:** die Pfade in `settings.yaml`
sind relativ und werden beim Laden gegen das App-Home absolutiert
(`config.py:55-61`, `app_home.resolve_path`). Eine gemeinsame Konfiguration
mit `archive: ./archive` ergibt damit von selbst je Profil ein eigenes Archiv.
Es braucht dafür **keine** Sonderlogik.

⚠️ **Kehrseite:** trägt jemand einen *absoluten* Pfad in die Einstellungen ein
(`resolve_path` lässt absolute Pfade bewusst stehen), teilen sich alle Profile
dieses Verzeichnis — die Trennung ist dann still aufgehoben. Die
Einstellungsseite muss davor warnen, sobald mehr als ein Profil existiert.

### Warum Kennung und Anzeigename getrennt sind

Wäre der Name der Ordnername, würde jedes Umbenennen den ganzen Bestand
verschieben — und, weil `archive_path` absolut in der Datenbank steht, eine
vollständige Pfadmigration auslösen. Für einen Tippfehler.

Mit fester Kennung ist Umbenennen das Ändern einer Zeichenkette. Nebeneffekt:
Umlaute, Leerzeichen und doppelte Namen sind unproblematisch.

## Verworfen

- **Zwei getrennte Instanzen** (je eigenes `BUEROKRATOR_HOME`, zwei
  Startverknüpfungen). Funktioniert fast heute schon, scheitert aber an
  `PORT = 8081` in `main.py:39`: die Zweitstart-Erkennung fände den belegten
  Port und würde **die Instanz der anderen Person öffnen**. Vor allem ist es
  nicht aus der App heraus steuerbar — genau das war die Anforderung.
- **Gemeinsamer Bestand mit Personenspalte** — siehe oben.
- **Haushaltsserver mit Konten im LAN.** `/pdf/{id}` hat bewusst keine
  Zugriffsprüfung (`main.py:57-59`); Konten würden das Sicherheitsmodell der
  App umbauen. Bei einem geteilten Login ohne Gegenwert.
- **Die Abkürzung ohne Migration** (erste Person bleibt liegen, nur weitere
  Profile bekommen ein Unterverzeichnis). Spart den teuersten Schritt, erzeugt
  aber eine dauerhafte Asymmetrie: ausgerechnet der erste Bestand wäre beim
  Auszug nicht als Verzeichnis mitzunehmen.
- **Ein dritter Wert „gemeinsam"** für Haushaltsdokumente. Die gemeinsame
  Mitte ist klein und wird **doppelt importiert**, einmal je Profil; bei einer
  Kopie wird das Häkchen „steuerrelevant" entfernt. Das Feld `tax_relevant`
  existiert dafür bereits samt Checkbox im Prüfformular
  (`document_detail.py:335`). Jedes Dokument hat damit genau einen Eigentümer.

## Aufbau

Vorher (unverändert, solange es nur ein Profil gibt):

    <basis>/
      config/settings.yaml
      config/aussteller_aliase.yaml
      database/  archive/  inbox/  trash/  backups/  logs/

Nachher:

    <basis>/
      config/settings.yaml        ← gemeinsam
      profiles.yaml               ← Liste + aktives Profil (neu)
      logs/  .setup_done  .nicegui
      profiles/
        1/
          profile.yaml            ← nur der Anzeigename (neu)
          config/aussteller_aliase.yaml
          database/  archive/  inbox/  exports/  trash/  backups/
        2/
          …

**Zur Installation, nicht zum Bestand** gehören außer den Einstellungen auch
Log, Setup-Marker und NiceGUI-Speicher. Log und UI-Speicher werden beim
**Import** des Moduls ausgewertet und könnten einem Profilwechsel im
laufenden Prozess ohnehin nicht folgen — ein gemeinsames Log ist ehrlicher
als eines, das nach dem Umschalten in den falschen Bestand schreibt. Der
Setup-Marker gehört dorthin, weil der Assistent Ollama und Tesseract prüft:
das zweite Profil soll ihn nicht erneut sehen.

`<basis>` ist das, was `get_app_home()` heute liefert — also
`BUEROKRATOR_HOME`, der Repo-Ordner im Entwicklermodus oder das
Benutzer-Datenverzeichnis.

## Umsetzungsschritte

### 1. Profilebene unter `app_home` (ohne Oberfläche) — **gebaut**

- Die heutige Auflösung heißt jetzt `get_base_home()` und ist unverändert.
  (Im Plan hieß sie `get_config_home()` — der Name war zu eng, sie trägt
  auch Log, Setup-Marker und UI-Speicher.)
- `get_app_home()` liefert die Basis, **solange keine `profiles.yaml`
  existiert** — sonst `<basis>/profiles/<aktiv>`.
- Auf `get_base_home()` umgestellt: `config.config_path()`, `logger.LOG_DIR`,
  `setup_service.setup_marker_path()` und der NiceGUI-Speicherpfad in
  `main.py`. Der Rest bleibt auf `get_app_home()` und wird dadurch
  automatisch profilbezogen — auch `resolve_path`, und damit Datenbank,
  Archiv, Inbox, Exporte, Papierkorb, Backups und die Alias-Datei.

⚠️ **Zwischenspeicher.** `get_app_home()` läuft bei jeder Pfadauflösung; eine
YAML-Datei jedes Mal zu parsen wäre im Stapelimport nicht vertretbar.
Zwischengespeichert wird der Dateiinhalt, **geschlüsselt nach
Basisverzeichnis** (sonst brechen die Tests, die per `chdir` das Home
wechseln) und gegen Zeitstempel **und** Größe geprüft. Zusätzlich verwirft
`reset_profile_cache()` ausdrücklich — manche Dateisysteme führen die Zeit
nur sekundengenau, und beim Umschalten aus der App darf nichts hängen
bleiben.

⚠️ **Eine unbrauchbare `profiles.yaml` ist ein harter Fehler**, kein stiller
Rückfall auf die Basis. Nach der Migration liegt dort kein Bestand mehr — ein
Rückfall würde eine leere Installation vortäuschen und neue Importe am
Bestand vorbeischreiben. Eine **fehlende** Datei bleibt dagegen der
Normalfall („keine Profile"). Die Kennung muss `[A-Za-z0-9_-]+` erfüllen, sie
wird zu einem Pfadsegment.

**Diese Stufe ändert ohne `profiles.yaml` nichts** — nachgewiesen durch die
unveränderte Testsuite und einen eigenen Test dafür.

### 2. Migration „zweite Person hinzufügen" — **gebaut**

`services/profile_service.enable_profiles()`, framework-frei. Der teuerste
Schritt, weil **`archive_path` absolut in der Datenbank steht** (am Bestand
geprüft). Ein Ordnerumzug allein hinterlässt eine Datenbank, die auf nicht
mehr vorhandene Dateien zeigt.

Reihenfolge, bewusst abbruchsicher:

1. Beide Profilverzeichnisse samt `profile.yaml` anlegen.
2. Inhalte **kopieren**, nicht verschieben — die Datenpfade aus der Config
   plus `trash/` und die Alias-Datei.
3. In der **Kopie** der Datenbank jeden `archive_path` umschreiben
   (Präfixtausch).
4. **Gegenprobe:** gleiche Zeilenzahl wie vorher, und für jede Zeile existiert
   die Datei unter dem neuen Pfad. Schlägt sie fehl: das halbe
   Profilverzeichnis entfernen und mit Klartextmeldung abbrechen. Bis hierher
   wurden die Originale nur **gelesen**.
5. Erst jetzt `profiles.yaml` schreiben — **das ist die Umschaltstelle.**
   Bricht der Vorgang vorher ab, läuft die App unverändert auf der alten
   Struktur weiter.
6. Die Originale **nicht löschen**, sondern nach `<basis>/vor-profilen/`
   verschieben — im Geist der Regel „Löschen verschiebt nach `trash/`, nie
   `unlink`". Der Nutzer entfernt sie selbst, wenn alles läuft.

Vier Festlegungen, die beim Bauen dazukamen:

- ⚠️ **Die Datenbank wird über `sqlite3.Connection.backup()` kopiert**, nie
  als Datei. Im WAL-Modus stehen committete Transaktionen in der `-wal`, bis
  ein Checkpoint läuft — und der läuft nicht, solange eine zweite Verbindung
  offen ist. Eine Dateikopie verlöre still die zuletzt importierten
  Dokumente. Derselbe Fehler steckte schon einmal im Backup; ein Test hält
  ihn jetzt auch hier fest.
- **SQLite-Seitendateien** (`-wal`, `-shm`, `-journal`) wandern beim
  Beiseiteräumen mit, und ein leer gewordenes Elternverzeichnis wird
  abgeräumt. Sonst bliebe am alten Ort ein Rest liegen, den die App
  versehentlich neu befüllen könnte, und der Altbestand wäre unvollständig.
- **Ein absoluter Datenpfad in den Einstellungen verhindert den Umzug**
  (Klartextmeldung, kein Teilumzug). Er läge für alle Profile im selben
  Verzeichnis — die Trennung wäre von Anfang an aufgehoben. Geprüft wird die
  **rohe** Config, weil `load_config()` bereits absolutiert hat.
- **Kein zusätzliches Backup.** Der Plan sah eines vor; es wäre reiner
  Ballast: der Umzug kopiert und löscht nie, die Originale liegen am Ende
  vollständig in `vor-profilen/`. Das ist eine stärkere Zusage als eine
  ZIP-Datei — und verdoppelt den Platzbedarf nicht ein drittes Mal.

Nicht Teil dieses Schritts: der Knopf, der das auslöst (Schritt 4).

### 3. Sperre während Hintergrund-Jobs

- `import_job.is_running()` existiert bereits (`import_job.py:25`) und ist
  serverweit, nicht an einen Browser-Tab gebunden.
- Die Sperre fragt nicht „läuft ein Import", sondern **„läuft ein
  Hintergrund-Job"** — eine kleine Funktion, in die später Backup oder
  Neuanalyse eingehängt werden können.
- Sie greift an **zwei** Stellen: am Umschalter in der Kopfzeile *und* in den
  Einstellungen. Sonst legt man während des Imports ein Profil an und schaltet
  über die Hintertür um.
- Statt einer nackten Fehlermeldung den Fortschritt zeigen („Import läuft —
  12 von 30").

Nicht wasserdicht, sondern angemessen: eine Abfrage beim Klick schließt das
Zeitfenster praktisch. Wasserdicht wäre, den laufenden Import beim Start an
sein Profil zu binden statt den Pfad je Dokument neu aufzulösen — das kostet
Eingriffe quer durch die Datenbankschicht und bleibt die Reserve.

### 4. Oberfläche

- **Kopfzeile:** `page_layout` (`layout.py:71`) ist die einzige Stelle, die
  den Kopf baut. Dort Anzeigename **und** Umschalter — damit auf jeder Seite
  sichtbar, nicht nur auf dem Dashboard.
- **Dashboard:** zusätzlich prominent. Die Dopplung ist Absicht; der teuerste
  Bedienfehler dieses Features ist ein Stapel im falschen Bestand.
- **Import-Seite:** Anzeigename neben den Import-Knopf.
- **Einstellungen:** neuer Tab „Profile" neben „Aliase" — anlegen, umbenennen,
  aus der Liste nehmen. Die Seite ist bereits in Tabs organisiert
  (`settings.py:29-35`).
- **Beim Start** das zuletzt aktive Profil. Fehlt dessen Verzeichnis, auf das
  erste zurückfallen und das sagen, statt mit einem Fehler zu starten.
- **Nach dem Wechsel** auf die Startseite navigieren, damit modulglobaler
  Seitenzustand (z. B. der Suchfilter der Dokumentenliste) neu aufgebaut wird.
- Vorbelegte Namen **„Benutzer 1"**, **„Benutzer 2"** — die App ist
  durchgängig deutsch beschriftet.

### 5. Dokumentation

`02_Datenmodell` (Verzeichnisaufbau), `05_Ordnerstruktur` (Profilebene über
dem Archiv), `07_Betrieb` (Backup und Migration je Profil), `CHANGELOG`.

## Testgrundsätze

- **Ohne `profiles.yaml` ändert sich nichts** — der wichtigste Test, weil die
  gesamte bestehende Suite und der Entwicklermodus daran hängen.
- Auflösung mit Profildatei: Einstellungen aus der Basis, Daten aus dem Profil.
- Migration auf einer temporären Struktur mit erfundenen Dokumenten: Pfade
  umgeschrieben, Gegenprobe greift, Abbruch vor `profiles.yaml` lässt die alte
  Struktur intakt.
- Umschalten wird verweigert, während ein Hintergrund-Job läuft.
- Umbenennen rührt das Dateisystem nicht an.
- Absoluter Pfad in den gemeinsamen Einstellungen erzeugt eine Warnung.

## Nicht in dieser Fassung

- **Prüfung der gemeinsamen Mitte** („liegt in beiden Beständen und ist
  zweimal steuerrelevant"). Billig nachrüstbar, weil der Doppelimport
  byte-identische Dateien erzeugt und `content_hash` ein SHA-256 über den
  Dateiinhalt mit eigenem Index ist (`file_hash.py:16`,
  `init_database.py:91`) — ein Mengenvergleich zweier Hash-Spalten, lesend.
- **Profil exportieren** (Verzeichnis plus minimale Konfiguration als
  eigenständiges App-Home). Erst beim Auszug relevant; mit gemeinsamen
  Einstellungen braucht der Export einen Schritt mehr — das ist der
  bewusst in Kauf genommene Preis von Festlegung 2.
- **Gleichzeitige Nutzung** durch zwei Personen. Ein Profil ist ein Modus des
  Prozesses, kein Konto.
