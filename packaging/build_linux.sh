#!/usr/bin/env bash
# Baut das Linux-Release-Tarball (onedir-Bundle + Installskript + .desktop).
#
# Aufruf aus dem Repo-Root, venv aktiv:
#     bash packaging/build_linux.sh
# Ergebnis: dist/buerokrator-<version>-linux-<arch>.tar.gz
set -euo pipefail

cd "$(dirname "$0")/.."

VERSION="0.1.0"
ARCH="$(uname -m)"
NAME="buerokrator-${VERSION}-linux-${ARCH}"

pyinstaller --noconfirm packaging/buerokrator.spec

STAGE="dist/${NAME}"
rm -rf "${STAGE}"
mkdir -p "${STAGE}"
cp -r dist/buerokrator "${STAGE}/buerokrator"
cp packaging/install.sh "${STAGE}/install.sh"
cp packaging/buerokrator.desktop "${STAGE}/buerokrator.desktop"
mkdir -p "${STAGE}/icons"
cp assets/buerokrator.svg assets/buerokrator-256.png assets/buerokrator-128.png assets/buerokrator-64.png "${STAGE}/icons/"
chmod +x "${STAGE}/install.sh"

tar -C dist -czf "dist/${NAME}.tar.gz" "${NAME}"
echo "Fertig: dist/${NAME}.tar.gz"
