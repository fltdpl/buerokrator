#!/usr/bin/env bash
# Entfernt Buerokrator aus dem Benutzerkonto — das Gegenstück zu install.sh:
#   Programm    ~/.local/opt/buerokrator
#   Starter     ~/.local/bin/buerokrator      (nur der eigene Symlink)
#   Menüeintrag ~/.local/share/applications/buerokrator.desktop
#   Symbole     ~/.local/share/icons/hicolor/*/apps/buerokrator.{svg,png}
#
# **Nutzerdaten bleiben.** Sie liegen getrennt vom Programm im App-Home und
# werden hier NIE gelöscht — mit --daten-verschieben höchstens nach
# ~/buerokrator-daten-<datum> beiseitegeräumt. Ein Rückbau bleibt damit
# umkehrbar; wer die Daten wirklich los sein will, löscht den Ordner selbst.
#
#   ./uninstall.sh                      fragt nach, entfernt nur das Programm
#   ./uninstall.sh --ja                 ohne Rückfrage
#   ./uninstall.sh --daten-verschieben  räumt zusätzlich die Daten beiseite
set -euo pipefail

# Aufräumen der Selbstkopie (siehe unten) — muss vor dem Umzug stehen.
if [ -n "${BUEROKRATOR_UNINSTALL_KOPIE:-}" ]; then
    trap 'rm -f "${BUEROKRATOR_UNINSTALL_KOPIE}"' EXIT
fi

: "${HOME:?HOME ist nicht gesetzt — ohne Heimatverzeichnis wird hier nichts gelöscht.}"

OPT="${HOME}/.local/opt/buerokrator"
BIN="${HOME}/.local/bin"
APPS="${HOME}/.local/share/applications"
ICONS="${HOME}/.local/share/icons/hicolor"

# Die Programmpfade spiegeln install.sh und stehen deshalb fest unter
# ~/.local. Die DATEN sucht die App dagegen über XDG_DATA_HOME
# (src/core/app_home.py) — hier bewusst anders aufgelöst, sonst meldet das
# Skript einen Ort, an dem gar nichts liegt.
DATEN="${XDG_DATA_HOME:-${HOME}/.local/share}/buerokrator"

# Bash liest sein Skript während der Ausführung nach. Der ausgelieferte
# Deinstaller liegt in genau dem Verzeichnis, das er löscht — ohne diesen
# Umzug bricht der Lauf mittendrin ab und lässt eine halbe Installation
# zurück.
SELBST="$(cd "$(dirname "$0")" && pwd)/$(basename "$0")"
case "${SELBST}" in
    "${OPT}"/*)
        KOPIE="$(mktemp -t buerokrator-uninstall.XXXXXX)"
        cat "${SELBST}" > "${KOPIE}"
        export BUEROKRATOR_UNINSTALL_KOPIE="${KOPIE}"
        exec bash "${KOPIE}" "$@"
        ;;
esac

hilfe() {
    cat <<'ENDE'
Deinstalliert Buerokrator für den aktuellen Benutzer (kein root nötig).

  uninstall.sh [OPTIONEN]

  -j, --ja               nicht nachfragen
      --daten-verschieben  Nutzerdaten nach ~/buerokrator-daten-<datum>
                         verschieben statt liegenzulassen (nie löschen)
  -h, --hilfe            diese Übersicht

Entfernt wird nur das Programm. Die Dokumente, die Datenbank und die
Einstellungen bleiben unberührt, damit eine erneute Installation sie
wiederfindet.
ENDE
}

JA=0
DATEN_VERSCHIEBEN=0

while [ $# -gt 0 ]; do
    case "$1" in
        -j|--ja|-y|--yes) JA=1 ;;
        --daten-verschieben) DATEN_VERSCHIEBEN=1 ;;
        -h|--hilfe|--help) hilfe; exit 0 ;;
        *)
            echo "Unbekannte Option: $1" >&2
            echo "Aufruf: uninstall.sh [--ja] [--daten-verschieben] [--hilfe]" >&2
            exit 2
            ;;
    esac
    shift
done

# --- Was ist überhaupt da? ---------------------------------------------

ZIELE=()
HINWEISE=()

if [ -e "${OPT}" ]; then
    ZIELE+=("${OPT}")
fi

# ~/.local/bin ist ein geteiltes Verzeichnis. Entfernt wird nur der Symlink,
# den install.sh angelegt hat — eine gleichnamige Datei von jemand anderem
# bleibt stehen.
STARTER="${BIN}/buerokrator"

if [ -L "${STARTER}" ]; then
    if [ "$(readlink "${STARTER}")" = "${OPT}/buerokrator" ]; then
        ZIELE+=("${STARTER}")
    else
        HINWEISE+=("${STARTER} zeigt woanders hin und bleibt unangetastet.")
    fi
elif [ -e "${STARTER}" ]; then
    HINWEISE+=("${STARTER} ist kein Symlink dieser Installation und bleibt liegen.")
fi

if [ -e "${APPS}/buerokrator.desktop" ]; then
    ZIELE+=("${APPS}/buerokrator.desktop")
fi

for ICON in "${ICONS}/scalable/apps/buerokrator.svg" \
            "${ICONS}/256x256/apps/buerokrator.png" \
            "${ICONS}/128x128/apps/buerokrator.png" \
            "${ICONS}/64x64/apps/buerokrator.png"; do
    if [ -e "${ICON}" ]; then
        ZIELE+=("${ICON}")
    fi
done

if [ "${#ZIELE[@]}" -eq 0 ]; then
    echo "Keine Installation gefunden — es wurde nichts entfernt."
    for HINWEIS in ${HINWEISE+"${HINWEISE[@]}"}; do
        echo "Hinweis: ${HINWEIS}"
    done
    if [ -d "${DATEN}" ]; then
        echo "Ihre Daten liegen weiterhin in ${DATEN}."
    fi
    exit 0
fi

# --- Ankündigen und bestätigen lassen ----------------------------------

echo "Es wird entfernt:"
for ZIEL in "${ZIELE[@]}"; do
    echo "  ${ZIEL}"
done

for HINWEIS in ${HINWEISE+"${HINWEISE[@]}"}; do
    echo "Hinweis: ${HINWEIS}"
done

if [ -d "${DATEN}" ] && [ "${DATEN_VERSCHIEBEN}" -eq 0 ]; then
    echo "Es bleibt erhalten:"
    echo "  ${DATEN} (Dokumente, Datenbank, Einstellungen)"
fi

if [ "${JA}" -eq 0 ]; then
    printf 'Fortfahren? [j/N] '
    # Eine leere oder abgebrochene Antwort gilt als Nein — bei einem
    # unbeaufsichtigten Lauf soll nichts verschwinden.
    ANTWORT=""
    read -r ANTWORT || ANTWORT=""

    case "${ANTWORT}" in
        j|J|ja|Ja|JA|y|Y|yes|Yes) ;;
        *) echo "Abgebrochen — es wurde nichts entfernt."; exit 0 ;;
    esac
fi

# --- Entfernen ----------------------------------------------------------

for ZIEL in "${ZIELE[@]}"; do
    rm -rf "${ZIEL}"
done

# Ohne das bleibt ein toter Menüeintrag stehen, bis der Desktop von sich aus
# neu einliest. Beide Werkzeuge sind optional und dürfen fehlschlagen.
if [ -d "${APPS}" ] && command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database -q "${APPS}" 2>/dev/null || true
fi

if [ -d "${ICONS}" ] && command -v gtk-update-icon-cache >/dev/null 2>&1; then
    gtk-update-icon-cache -q -f "${ICONS}" 2>/dev/null || true
fi

echo "Programm entfernt."

# --- Nutzerdaten --------------------------------------------------------

if [ "${DATEN_VERSCHIEBEN}" -eq 1 ]; then
    if [ -n "${BUEROKRATOR_HOME:-}" ]; then
        # Dann bestimmt nicht das Standardverzeichnis, wo die Daten liegen.
        # Lieber gar nichts anfassen als den falschen Ordner verschieben.
        echo "BUEROKRATOR_HOME ist gesetzt (${BUEROKRATOR_HOME}) — die Daten liegen"
        echo "möglicherweise dort statt in ${DATEN}. Es wurde nichts verschoben."
    elif [ -d "${DATEN}" ]; then
        ZIEL_DATEN="${HOME}/buerokrator-daten-$(date +%Y-%m-%d)"
        LAUF=2
        while [ -e "${ZIEL_DATEN}" ]; do
            ZIEL_DATEN="${HOME}/buerokrator-daten-$(date +%Y-%m-%d)-${LAUF}"
            LAUF=$((LAUF + 1))
        done

        mv "${DATEN}" "${ZIEL_DATEN}"
        echo "Daten verschoben nach: ${ZIEL_DATEN}"
        echo "Sie wurden NICHT gelöscht — das bleibt Ihnen überlassen."
    else
        echo "Keine Nutzerdaten in ${DATEN} gefunden."
    fi
fi

if [ -d "${DATEN}" ]; then
    echo "Ihre Dokumente und Einstellungen bleiben in ${DATEN}."
    echo "Eine erneute Installation findet sie dort wieder."
fi
