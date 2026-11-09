#!/usr/bin/env bash
# ==============================================================================
# Build paket rilis Linux: binari mandiri (tanpa Python) + installer.
# Hasil: dist/ixsland-linux-x64.tar.gz  dan  dist/install-linux.sh
#
# Optimasi ukuran:
#   - Pakai PyQt6 wheel (self-contained) via venv terpisah bila tersedia,
#     BUKAN Qt6 sistem (yang menarik libgtk3/KDE/ffmpeg + plugin tak perlu).
#   - Pangkas plugin Qt6 ke daftar minimal (wayland/xcb + input context).
#   - Hanya sertakan aset yang benar-benar dipakai runtime (icon.png).
# ==============================================================================

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

# --- Pilih Python/PyInstaller -------------------------------------------------
VENV_WHEEL="${VENV_WHEEL:-$HOME/.venv-ixwheel}"
if [ -x "$VENV_WHEEL/bin/pyinstaller" ]; then
    PYI="$VENV_WHEEL/bin/pyinstaller"
    PY="$VENV_WHEEL/bin/python"
    echo "==> Memakai PyQt6 wheel venv: $VENV_WHEEL"
elif [ -x "$HOME/.venv-ixbuild/bin/pyinstaller" ]; then
    PYI="$HOME/.venv-ixbuild/bin/pyinstaller"
    PY="$HOME/.venv-ixbuild/bin/python"
    echo "==> Memakai venv: $HOME/.venv-ixbuild"
else
    PYI="${PYI:-python3 -m PyInstaller}"
    PY="${PY:-python3}"
fi

# --- Pangkas plugin Qt6 (idempotent) -----------------------------------------
# Plugin tak terpakai menarik lib sistem besar (gtk3, glycin, ffmpeg, dll.).
# Hanya simpan yang dibutuhkan untuk Wayland + X11.
if [ -x "$PY" ]; then
    "$PY" - <<'PYEOF'
import os, shutil, sys
try:
    from PyQt6.QtCore import QLibraryInfo
except Exception:
    sys.exit(0)
plugins = QLibraryInfo.path(QLibraryInfo.LibraryPath.PluginsPath)
if not os.path.isdir(plugins):
    sys.exit(0)
keep = {
    "platforms", "platforminputcontexts",
    "wayland-shell-integration", "wayland-graphics-integration-client",
    "wayland-decoration-client", "xcbglintegrations",
}
keep_platforms = {"libqwayland.so", "libqxcb.so", "libqminimal.so", "libqoffscreen.so"}
removed = 0
for entry in os.listdir(plugins):
    full = os.path.join(plugins, entry)
    if os.path.isdir(full) and entry not in keep:
        shutil.rmtree(full, ignore_errors=True)
        removed += 1
    elif os.path.isfile(full):
        os.remove(full)
        removed += 1
pf = os.path.join(plugins, "platforms")
if os.path.isdir(pf):
    for f in os.listdir(pf):
        if f not in keep_platforms:
            os.remove(os.path.join(pf, f))
# adwaita menarik lib sistem; tidak diperlukan
adw = os.path.join(plugins, "wayland-decoration-client", "libadwaita.so")
if os.path.exists(adw):
    os.remove(adw)
print(f"[build] plugin Qt6 dipangkas: {removed} entri dibuang")
PYEOF
fi

# --- Aset minimal yang dipakai runtime ---------------------------------------
ASSET_PACK="$ROOT/build/assets_pack"
rm -rf "$ASSET_PACK"
mkdir -p "$ASSET_PACK"
cp -f assets/icon.png "$ASSET_PACK/" 2>/dev/null || true
[ -f assets/icon.ico ] && cp -f assets/icon.ico "$ASSET_PACK/" || true

echo "==> [1/3] Membangun binari ixsland (PyInstaller onefile) ..."
BUILD_DIR="$ROOT/build/pyi"
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"
$PYI --noconfirm --onefile --name ixsland \
     --distpath "$BUILD_DIR/dist" \
     --workpath "$BUILD_DIR/work" \
     --specpath "$BUILD_DIR" \
     --add-data "$ASSET_PACK:assets" \
     --hidden-import PyQt6.QtDBus \
     ixsland.py

echo "==> [2/3] Menyusun staging ..."
STAGE="$ROOT/build/ixsland-linux-x64"
rm -rf "$STAGE"
mkdir -p "$STAGE/assets"
cp -f "$BUILD_DIR/dist/ixsland" "$STAGE/ixsland"
cp -f assets/icon.png "$STAGE/assets/" 2>/dev/null || true
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
echo "One click :  bash <(curl -fsSL https://github.com/rezariski42/ixsland/releases/latest/download/install-linux.sh)"
