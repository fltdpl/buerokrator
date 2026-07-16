# Entscheidung 012

## Thema

Kein Update-Check in der App (weder automatisch noch manuell ausgelöst)

## Entscheidung (16.07.2026)

Die App enthält keinerlei Update-Mechanismus. Update-Hinweise laufen
ausschließlich über den Verbreitungskanal (z. B. GitHub-Releases);
installierte Instanzen stellen nie eine Netzverbindung her.

## Begründung

- Konsequenz aus dem Grundsatz „keine Requests an Dritte": Auch ein
  Versions-Check beim Start wäre ein regelmäßiges Nach-Hause-Telefonieren
  (IP, Zeitpunkt, Versionsstand) — genau das Verhalten, das die App
  bewusst nicht hat.
- Die Alternative „manueller Check-Button" (öffnet die Releases-Seite im
  Browser) wurde verworfen: solange es keinen echten Verteilungskanal an
  Dritte gibt, ist sie totes Gewicht.

## Konsequenzen

- Veraltete Installationen bleiben still veraltet — akzeptiert für den
  aktuellen Nutzerkreis (Einzelplatz, Weitergabe im persönlichen Umfeld).
- Vor der Weitergabe an Dritte gehört das Schema-Backup-Netz dazu
  (`PRAGMA user_version` + Auto-Backup vor Migration, seit 16.07.2026
  vorhanden), damit alte Versionen fremde Datenbestände nicht gefährden.
- Wird später ein echter Verteilungskanal aufgebaut, ist der manuelle
  Check-Button (nutzerausgelöst, kein Hintergrund-Request) der
  vorgesehene Wiedereinstieg — nicht der automatische Check.
