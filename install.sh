#!/usr/bin/env bash
# ==============================================================================
# ixsland Dynamic Island Installer for Linux (KDE Plasma 6 Wayland / X11)
# https://github.com/rezariski42/ixsland
#
# Mode 1 (disarankan, ONE CLICK):  paket rilis sudah menyertakan binari `ixsland`
#   -> pengguna TIDAK perlu memasang Python maupun PyQt6.
# Mode 2 (dev):                    jalankan dari repo, butuh python3 + PyQt6.
# ==============================================================================

set -e

GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${CYAN}"
echo "  ██╗██╗  ██╗███████╗██╗      █████╗ ███╗   ██╗██████╗ "
echo "  ██║╚██╗██╔╝██╔════╝██║     ██╔══██╗████╗  ██║██╔══██╗"
echo "  ██║ ╚███╔╝ ███████╗██║     ███████║██╔██╗ ██║██║  ██║"
echo "  ██║ ██╔██╗ ╚════██║██║     ██╔══██║██║╚██╗██║██║  ██║"
echo "  ██║██╔╝ ██╗███████║███████╗██║  ██║██║ ╚████║██████╔╝"
echo "  ╚═╝╚═╝  ╚═╝╚══════╝╚══════╝╚═╝  ╚═╝╚═╝  ╚═══╝╚═════╝ "
echo -e "${NC}"
echo -e "${GREEN}==> Installing ixsland Dynamic Island on Linux...${NC}\n"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="$HOME/.local/share/ixsland"
SYSTEMD_USER_DIR="$HOME/.config/systemd/user"

USE_BINARY=0
if [ -f "$SCRIPT_DIR/ixsland" ] && file "$SCRIPT_DIR/ixsland" 2>/dev/null | grep -q "ELF"; then
    USE_BINARY=1
    echo -e "${GREEN}==> Paket binari terdeteksi — Python TIDAK diperlukan.${NC}\n"
fi

# 1. Dependency Check
echo -e "${CYAN}[1/4] Checking system dependencies...${NC}"
MISSING_DEPS=()

if [ "$USE_BINARY" -eq 0 ]; then
    command -v python3 >/dev/null 2>&1 || MISSING_DEPS+=("python3")
    python3 -c "import PyQt6" >/dev/null 2>&1 || MISSING_DEPS+=("python-pyqt6")
fi
command -v wpctl >/dev/null 2>&1 || MISSING_DEPS+=("pipewire")
command -v qdbus6 >/dev/null 2>&1 || MISSING_DEPS+=("qt6-tools (qdbus6)")

if [ ${#MISSING_DEPS[@]} -ne 0 ]; then
    echo -e "${YELLOW}Warning: Missing required packages: ${MISSING_DEPS[*]}${NC}"
    if command -v pacman >/dev/null 2>&1; then
        echo -e "Install on Arch/CachyOS with:"
        echo -e "  ${GREEN}sudo pacman -S pipewire wireplumber qt6-tools${NC}\n"
    elif command -v apt >/dev/null 2>&1; then
        echo -e "Install on Debian/Ubuntu with:"
        echo -e "  ${GREEN}sudo apt install pipewire wireplumber qt6-tools-dev-tools${NC}\n"
    elif command -v dnf >/dev/null 2>&1; then
        echo -e "Install on Fedora with:"
        echo -e "  ${GREEN}sudo dnf install pipewire wireplumber qt6-qttools${NC}\n"
    fi
    if [ "$USE_BINARY" -eq 0 ]; then
        echo -e "${RED}Mode sumber membutuhkan Python + PyQt6. Unduh paket rilis (binari) untuk tanpa dependensi Python.${NC}\n"
    fi
else
    echo -e "${GREEN}✓ All core dependencies found!${NC}"
fi

# 2. Deploy Files
echo -e "\n${CYAN}[2/4] Deploying application files to ${INSTALL_DIR}...${NC}"
mkdir -p "$INSTALL_DIR"

if [ "$USE_BINARY" -eq 1 ]; then
    cp -f "$SCRIPT_DIR/ixsland" "$INSTALL_DIR/ixsland"
    chmod +x "$INSTALL_DIR/ixsland"
    echo -e "${GREEN}✓ Binari ixsland terpasang (self-contained, tanpa Python)${NC}"
else
    cp -f "$SCRIPT_DIR/ixsland.py" "$INSTALL_DIR/ixsland.py"
    chmod +x "$INSTALL_DIR/ixsland.py"
    echo -e "${GREEN}✓ Sumber ixsland.py terpasang (mode dev)${NC}"
fi

# Aset (ikon, maskot, banner) — dibutuhkan kedua mode
if [ -d "$SCRIPT_DIR/assets" ]; then
    mkdir -p "$INSTALL_DIR/assets"
    cp -f "$SCRIPT_DIR/assets/"* "$INSTALL_DIR/assets/" 2>/dev/null || true
fi
cp -f "$SCRIPT_DIR/run-demo.py" "$INSTALL_DIR/run-demo.py" 2>/dev/null || true
chmod +x "$INSTALL_DIR/run-demo.py" 2>/dev/null || true

# Copy default config if none exists
if [ ! -f "$INSTALL_DIR/config.json" ]; then
    if [ -f "$SCRIPT_DIR/config.example.json" ]; then
        cp "$SCRIPT_DIR/config.example.json" "$INSTALL_DIR/config.json"
        echo -e "${GREEN}✓ Default configuration created at ${INSTALL_DIR}/config.json${NC}"
    fi
fi

# 3. Configure Systemd User Service
echo -e "\n${CYAN}[3/4] Setting up systemd user service...${NC}"
mkdir -p "$SYSTEMD_USER_DIR"

if [ "$USE_BINARY" -eq 1 ]; then
    EXEC_START="$INSTALL_DIR/ixsland"
else
    EXEC_START="$INSTALL_DIR/ixsland.py"
fi

cat <<EOF > "$SYSTEMD_USER_DIR/ixsland.service"
[Unit]
Description=ixsland Dynamic Island (Linux Native Port)
After=graphical-session.target
PartOf=graphical-session.target

[Service]
Type=simple
ExecStart=$EXEC_START
Restart=on-failure
RestartSec=3

[Install]
WantedBy=graphical-session.target
EOF

# 4. Activate Service
echo -e "\n${CYAN}[4/4] Activating ixsland service...${NC}"
systemctl --user daemon-reload
systemctl --user enable ixsland.service
# restart (bukan hanya --now) supaya versi terbaru langsung dipakai
# meski layanan lama masih berjalan saat perbaikan/pembaruan pemasangan.
systemctl --user restart ixsland.service

echo -e "\n${GREEN}======================================================${NC}"
echo -e "${GREEN}  🎉 ixsland installed and launched successfully!${NC}"
echo -e "${GREEN}======================================================${NC}"
echo -e "• Dynamic Island is now running on your ${CYAN}Primary Display${NC}."
echo -e "• Check status:   ${YELLOW}systemctl --user status ixsland.service${NC}"
echo -e "• View logs:      ${YELLOW}journalctl --user -u ixsland -f${NC}"
echo -e "• Test features:  ${YELLOW}$INSTALL_DIR/run-demo.py${NC}"
echo -e "• Settings:       klik ikon ⚙ pada island, atau jalankan:"
echo -e "                  ${YELLOW}$EXEC_START --settings${NC}"
echo -e "• Uninstall:      ${YELLOW}bash uninstall.sh${NC}"
echo -e "• Configuration:  ${YELLOW}~/.local/share/ixsland/config.json${NC}\n"