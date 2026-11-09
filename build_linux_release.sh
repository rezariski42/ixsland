#!/usr/bin/env bash
# ==============================================================================
# Build paket rilis Linux: binari mandiri (tanpa Python) + installer.
# Hasil: dist/ixsland-linux-x64.tar.gz  dan  dist/install-linux.sh
# ==============================================================================

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

PYTHON="${PYTHON:-python3}"
if [ -x "$HOME/.venv-ixbuild/bin/pyinstaller" ]; then
    PYI="$HOME/.venv-ixbuild/bin/pyinstaller"
else
    PYI="$PYTHON -m PyInstaller"
fi

echo "==> [1/3] Membangun binari ixsland (PyInstaller onefile) ..."
$PYI --noconfirm --onefile --name ixsland \
     --add-data assets:assets \
     --hidden-import PyQt6.QtDBus \
     --hidden-import PyQt6.QtSvg \
     ixsland.py

echo "==> [2/3] Menyusun staging ..."
STAGE="$ROOT/build/ixsland-linux-x64"
rm -rf "$STAGE"
mkdir -p "$STAGE/assets"
cp -f dist/ixsland "$STAGE/ixsland"
cp -f assets/* "$STAGE/assets/" 2>/dev/null || true
cp -f install.sh uninstall.sh README.md run-demo.py config.example.json "$STAGE/"
chmod +x "$STAGE/ixsland" "$STAGE/install.sh" "$STAGE/uninstall.sh" "$STAGE/run-demo.py"

echo "==> [3/3] Membuat arsip ..."
mkdir -p dist
tar -C "$ROOT/build" -czf dist/ixsland-linux-x64.tar.gz ixsland-linux-x64
cp -f install-linux.sh dist/install-linux.sh
chmod +x dist/install-linux.sh

echo
echo "Hasil:"
ls -la dist/ixsland-linux-x64.tar.gz dist/install-linux.sh
echo
echo "Uji lokal :  tar -xzf dist/ixsland-linux-x64.tar.gz -C /tmp && bash /tmp/ixsland-linux-x64/install.sh"
echo "One click :  bash <(curl -fsSL https://github.com/rezariski/ixsland/releases/latest/download/install-linux.sh)"