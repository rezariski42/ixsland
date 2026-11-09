#!/usr/bin/env bash
# ==============================================================================
# ixsland Dynamic Island — pemasang SATU KLIK (Linux)
#
# Jalankan satu baris ini di terminal:
#   bash <(curl -fsSL https://github.com/rezariski42/ixsland/releases/latest/download/install-linux.sh)
#
# Skrip ini mengunduh paket binari terbaru (tanpa Python) lalu memasangnya.
# ==============================================================================

set -euo pipefail

REPO="rezariski42/ixsland"
ASSET="ixsland-linux-x64.tar.gz"

echo "==> Memeriksa versi terbaru ixsland ..."
TAG="$(curl -fsSL "https://api.github.com/repos/${REPO}/releases/latest" \
      | grep -o '"tag_name": *"[^"]*"' | head -1 | cut -d'"' -f4)"
if [ -z "${TAG}" ]; then
    echo "Gagal membaca versi terbaru dari GitHub." >&2
    exit 1
fi
echo "==> Versi terbaru: ${TAG}"

BASE_URL="https://github.com/${REPO}/releases/download/${TAG}"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

echo "==> Mengunduh ${ASSET} ..."
curl -fL --progress-bar "${BASE_URL}/${ASSET}" -o "${TMP}/${ASSET}"

echo "==> Mengekstrak paket ..."
tar -xzf "${TMP}/${ASSET}" -C "${TMP}"

if [ ! -f "${TMP}/install.sh" ]; then
    echo "Paket rusak: install.sh tidak ditemukan." >&2
    exit 1
fi

echo "==> Menjalankan pemasangan ${TAG} ..."
bash "${TMP}/install.sh"

echo
echo "Selesai. Dynamic Island kini berjalan di layar utama Anda."