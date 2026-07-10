# 011 — Eigenes Theme statt Web-Fonts und Fremd-Assets

Status: angenommen

## Kontext

Die Oberfläche sollte an Creative Tims „Paper Dashboard" angelehnt werden:
linke Seitenleiste, karten-basierter Inhalt, dünne Überschriften, farbige
Akzente. Heller Inhaltsbereich, dunkle Seitenleiste.

## Entscheidung

- Das Aussehen wird als eigenes Stylesheet in `src/frontend/theme.py`
  nachgebaut, nicht als Portierung des Bootstrap-3-Templates. NiceGUI
  rendert Quasar-Komponenten; ein fremdes CSS-Framework daneben würde beide
  Kaskaden gegeneinander laufen lassen.
- **Keine Web-Fonts.** Die Vorlage lädt die Schrift „Muli" von Google Fonts.
  Bei einem Archiv, dessen Kernversprechen „alles bleibt lokal" ist, wäre das
  bei jedem Seitenaufruf ein Request an einen Dritten — mit der IP des
  Nutzers, für Typografie. Stattdessen der System-Font-Stack; Icons kommen
  aus den in NiceGUI gebündelten Material Icons und werden lokal ausgeliefert.
- Alle Farben und das CSS liegen zentral in `theme.py`. Seitenmodule setzen
  keine Farbwerte, sondern nutzen die Klassen `page-title`, `muted`, `brand`
  und den `card()`-Kontextmanager aus `layout.py`.

## Konsequenzen

- Die Anmutung ist nicht pixelgleich zur Vorlage (Muli ist schmaler als die
  Systemschriften), der Charakter bleibt.
- Ein Farbwechsel ist eine Änderung an einer Datei.
- Kontrast muss beim Ändern der Palette geprüft werden: helle Pastelltöne
  taugen als Fläche, nicht als Schrift- oder Iconfarbe (deshalb
  `ACCENT_A_INK` neben `ACCENT_A`).

Ersetzt nichts; ergänzt [[010_nicegui]].
