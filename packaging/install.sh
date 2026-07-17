#!/usr/bin/env bash
# Installiert Buerokrator für den aktuellen Benutzer (kein root nötig):
#   Programm  → ~/.local/opt/buerokrator
#   Starter   → ~/.local/bin/buerokrator
#   Menüeintrag → ~/.local/share/applications/buerokrator.desktop
# Nutzerdaten liegen getrennt davon in ~/.local/share/buerokrator (App-Home)
# und bleiben bei Updates/Deinstallation erhalten.
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

# Icon für den Menüeintrag (hicolor-Theme, skalierbar + Raster-Fallbacks)
if [ -d icons ]; then
    mkdir -p "${ICONS}/scalable/apps" "${ICONS}/256x256/apps" "${ICONS}/128x128/apps" "${ICONS}/64x64/apps"
    cp icons/buerokrator.svg "${ICONS}/scalable/apps/buerokrator.svg"
    cp icons/buerokrator-256.png "${ICONS}/256x256/apps/buerokrator.png"
    cp icons/buerokrator-128.png "${ICONS}/128x128/apps/buerokrator.png"
    cp icons/buerokrator-64.png "${ICONS}/64x64/apps/buerokrator.png"
    command -v gtk-update-icon-cache >/dev/null 2>&1 && gtk-update-icon-cache -q "${ICONS}" || true
fi

sed "s|@EXEC@|${OPT}/buerokrator|" buerokrator.desktop > "${APPS}/buerokrator.desktop"

if ! command -v tesseract >/dev/null 2>&1; then
    echo "Hinweis: Tesseract OCR fehlt (z. B. 'sudo apt install tesseract-ocr tesseract-ocr-deu')."
fi
if ! command -v ollama >/dev/null 2>&1; then
    echo "Hinweis: Ollama fehlt (https://ollama.com/download) — optional, aber ohne läuft die automatische Analyse nicht."
fi

echo "Fertig. Start über das Anwendungsmenü oder: ${BIN}/buerokrator"
echo "(Falls ~/.local/bin nicht im PATH ist, den vollen Pfad verwenden.)"
