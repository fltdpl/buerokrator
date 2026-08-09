#!/usr/bin/env bash
# Baut das Linux-Release-Tarball (onedir-Bundle + Installskript + .desktop).
#
# Aufruf aus dem Repo-Root, venv aktiv:
#     bash packaging/build_linux.sh
# Ergebnis: dist/buerokrator-<version>-linux-<arch>.tar.gz
set -euo pipefail

cd "$(dirname "$0")/.."

# Version aus dem Paket lesen — eine Quelle, kein Nachziehen beim Release.
VERSION="$(python -c 'from src import __version__; print(__version__)')"
ARCH="$(uname -m)"
NAME="buerokrator-${VERSION}-linux-${ARCH}"

# Passt der Tag auf HEAD zur Version im Paket? Beim Tag v0.2.0 stand intern
# noch 0.1.0 — das Tarball hieße dann nach der FALSCHEN Version, und die
# Angabe im Dateinamen ist die einzige, die ein Nutzer sieht. Nur prüfen,
# wenn HEAD überhaupt getaggt ist: Testbuilds zwischen zwei Releases sind
# der Normalfall.
TAG="$(git describe --exact-match --tags 2>/dev/null || true)"

if [ -n "${TAG}" ] && [ "${TAG}" != "v${VERSION}" ]; then
    echo "Abbruch: HEAD ist als ${TAG} getaggt, src/__init__.py sagt ${VERSION}." >&2
    echo "Erst __version__ nachziehen (oder den Tag korrigieren), dann bauen." >&2
    exit 1
fi

pyinstaller --noconfirm packaging/buerokrator.spec

STAGE="dist/${NAME}"
rm -rf "${STAGE}"
mkdir -p "${STAGE}"
cp -r dist/buerokrator "${STAGE}/buerokrator"
cp packaging/install.sh "${STAGE}/install.sh"
cp packaging/uninstall.sh "${STAGE}/uninstall.sh"
cp packaging/buerokrator.desktop "${STAGE}/buerokrator.desktop"

# Die Version steckte bisher nur im Verzeichnisnamen — und der ist nach dem
# Entpacken beliebig verändert. Wer später fragt „welchen Stand habe ich da
# eigentlich installiert", findet es sonst nirgends.
printf '%s\n' "${VERSION}" > "${STAGE}/VERSION"
mkdir -p "${STAGE}/icons"
cp assets/buerokrator.svg assets/buerokrator-256.png assets/buerokrator-128.png assets/buerokrator-64.png "${STAGE}/icons/"
chmod +x "${STAGE}/install.sh" "${STAGE}/uninstall.sh"

tar -C dist -czf "dist/${NAME}.tar.gz" "${NAME}"
echo "Fertig: dist/${NAME}.tar.gz"
