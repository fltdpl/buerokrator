#!/usr/bin/env bash
# Installiert Buerokrator für den aktuellen Benutzer (kein root nötig):
#   Programm  → ~/.local/opt/buerokrator
#   Starter   → ~/.local/bin/buerokrator
#   Menüeintrag → ~/.local/share/applications/buerokrator.desktop
# Nutzerdaten liegen getrennt davon in ~/.local/share/buerokrator (App-Home)
# und bleiben bei Updates/Deinstallation erhalten.
# Deinstallation: ~/.local/opt/buerokrator/uninstall.sh
set -euo pipefail

cd "$(dirname "$0")"

OPT="${HOME}/.local/opt/buerokrator"
BIN="${HOME}/.local/bin"
APPS="${HOME}/.local/share/applications"
ICONS="${HOME}/.local/share/icons/hicolor"

echo "Installiere nach ${OPT} …"
rm -rf "${OPT}"
mkdir -p "${OPT}" "${BIN}" "${APPS}"
cp -r buerokrator/. "${OPT}/"

ln -sf "${OPT}/buerokrator" "${BIN}/buerokrator"

# Der Deinstaller wandert mit in die Installation: das entpackte Tarball wird
# üblicherweise gelöscht, und dann gäbe es keinen Weg zurück mehr.
cp uninstall.sh "${OPT}/uninstall.sh"
chmod +x "${OPT}/uninstall.sh"

# Aus demselben Grund die Versionsangabe: nach dem Löschen des entpackten
# Verzeichnisses ließe sich sonst nirgends mehr ablesen, welcher Stand
# installiert ist.
if [ -f VERSION ]; then
    cp VERSION "${OPT}/VERSION"
fi

# Icon für den Menüeintrag. Der Menüeintrag bekommt einen ABSOLUTEN
# Icon-Pfad ins Installationsverzeichnis — der Theme-Lookup über
# ~/.local/share/icons zeigte je nach Desktop nur ein generisches Symbol
# (kein index.theme/Icon-Cache im Nutzer-hicolor). Die hicolor-Kopien
# bleiben als Zusatz für Umgebungen, die nach Namen auflösen.
ICON_REF="buerokrator"
if [ -d icons ]; then
    mkdir -p "${OPT}/icons"
    cp icons/buerokrator.svg icons/buerokrator-*.png "${OPT}/icons/"
    ICON_REF="${OPT}/icons/buerokrator-256.png"

    mkdir -p "${ICONS}/scalable/apps" "${ICONS}/256x256/apps" "${ICONS}/128x128/apps" "${ICONS}/64x64/apps"
    cp icons/buerokrator.svg "${ICONS}/scalable/apps/buerokrator.svg"
    cp icons/buerokrator-256.png "${ICONS}/256x256/apps/buerokrator.png"
    cp icons/buerokrator-128.png "${ICONS}/128x128/apps/buerokrator.png"
    cp icons/buerokrator-64.png "${ICONS}/64x64/apps/buerokrator.png"
    command -v gtk-update-icon-cache >/dev/null 2>&1 && gtk-update-icon-cache -q "${ICONS}" || true
fi

sed -e "s|@EXEC@|${OPT}/buerokrator|" -e "s|@ICON@|${ICON_REF}|" \
    buerokrator.desktop > "${APPS}/buerokrator.desktop"
command -v update-desktop-database >/dev/null 2>&1 && update-desktop-database -q "${APPS}" || true

if ! command -v tesseract >/dev/null 2>&1; then
    echo "Hinweis: Tesseract OCR fehlt (z. B. 'sudo apt install tesseract-ocr tesseract-ocr-deu')."
fi
if ! command -v ollama >/dev/null 2>&1; then
    echo "Hinweis: Ollama fehlt (https://ollama.com/download) — optional, aber ohne läuft die automatische Analyse nicht."
fi

echo "Fertig. Start über das Anwendungsmenü oder: ${BIN}/buerokrator"
echo "(Falls ~/.local/bin nicht im PATH ist, den vollen Pfad verwenden.)"
echo "Deinstallation später: ${OPT}/uninstall.sh (Nutzerdaten bleiben erhalten)"
