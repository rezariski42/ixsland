<div align="center">

# 🏝️ ixsland — Dynamic Island (Linux/Windows)

**A blazing-fast, buttery-smooth Dynamic Island crafted natively for Linux and Windows 10/11 (64-bit).**  
*Zero Electron bloat. Pure 60 FPS PyQt6 native magic.*

<br/>

<img src="./assets/hero_banner.png" width="92%" alt="ixsland Dynamic Island Promo" />

<br/>

<p align="center">
  <b>Semua tautan di bawah selalu menunjuk ke versi TERBARU (latest):</b>
</p>

<p align="center">
  <a href="https://github.com/rezariski/ixsland/releases/latest/download/install-linux.sh">
    <img src="https://img.shields.io/badge/Install-Linux%20One%20Click%20(shell)-00E5FF?style=for-the-badge&logo=linux&logoColor=white&labelColor=0E1017" alt="Install Linux one click" />
  </a>
  &nbsp;
  <a href="https://github.com/rezariski/ixsland/releases/latest/download/ixsland-linux-x64.tar.gz">
    <img src="https://img.shields.io/badge/Direct%20Download-Linux%20BIN%20(tanpa%20Python)-00E5FF?style=for-the-badge&logo=linux&logoColor=white&labelColor=0E1017" alt="Direct Download Linux binary" />
  </a>
  &nbsp;
  <a href="https://github.com/rezariski/ixsland/releases/latest/download/Setup.exe">
    <img src="https://img.shields.io/badge/Direct%20Download-Windows%20Setup.exe-0078D4?style=for-the-badge&logo=windows&logoColor=white&labelColor=0E1017" alt="Direct Download Windows Setup.exe" />
  </a>
</p>

<p align="center">
  <a href="https://github.com/rezariski/ixsland/releases/latest">
    <img src="https://img.shields.io/github/v/release/rezariski/ixsland?style=for-the-badge&color=FFD700&labelColor=0E1017&label=Release" alt="Latest Release" />
  </a>
  <img src="https://img.shields.io/badge/Linux-Wayland%20%7C%20X11-00E5FF?style=for-the-badge&logo=linux&logoColor=white&labelColor=0E1017" />
  <img src="https://img.shields.io/badge/Windows-10%20%7C%2011%20(64--bit)-0078D4?style=for-the-badge&logo=windows&logoColor=white&labelColor=0E1017" />
  <img src="https://img.shields.io/badge/Engine-PyQt6%20%7C%20Python%203-3776AB?style=for-the-badge&logo=python&logoColor=white&labelColor=0E1017" />
  <img src="https://img.shields.io/badge/Audio-PipeWire%20%2F%20CoreAudio-FF6B6B?style=for-the-badge&logo=speaker&logoColor=white&labelColor=0E1017" />
  <img src="https://img.shields.io/badge/License-GPL--3.0-00E676?style=for-the-badge&labelColor=0E1017" />
</p>

<p align="center">
  <a href="#-direct-downloads-tautan-unduh-langsung"><code>[ 📥 DIRECT DOWNLOAD ]</code></a> &nbsp;•&nbsp;
  <a href="#-1-linux-edition"><code>[ 🐧 LINUX GUIDE ]</code></a> &nbsp;•&nbsp;
  <a href="#-2-windows-edition-windows-10--11-64-bit"><code>[ 🪟 WINDOWS GUIDE ]</code></a> &nbsp;•&nbsp;
  <a href="#-interactive-demo-showcase-linux--windows"><code>[ 🧪 DEMO SHOWCASE ]</code></a> &nbsp;•&nbsp;
  <a href="#-feature-walkthrough"><code>[ ✨ FEATURES ]</code></a> &nbsp;•&nbsp;
  <a href="#-treat-me-a-coffee"><code>[ ☕ DONATE ]</code></a>
</p>

</div>

---

## 📥 Direct Downloads (Tautan Unduh Langsung)

Semua tautan memakai URL `releases/latest/download/...`, sehingga **selalu mengunduh versi terbaru** tanpa perlu membuka halaman rilis:

| Sistem Operasi | Cara | Tanpa Python? | Tautan |
|---|---|---|---|
| 🐧 **Linux** | Satu baris di terminal | ✅ | [⬇️ **Install Linux (one click)**](https://github.com/rezariski/ixsland/releases/latest/download/install-linux.sh) |
| 🐧 **Linux** | Unduh paket binari | ✅ | [⬇️ **ixsland-linux-x64.tar.gz**](https://github.com/rezariski/ixsland/releases/latest/download/ixsland-linux-x64.tar.gz) |
| 🪟 **Windows** | Unduh lalu jalankan Setup | ✅ | [⬇️ **Setup.exe (wizard Next/Next)**](https://github.com/rezariski/ixsland/releases/latest/download/Setup.exe) |

> **Linux — satu baris (pemasangan instan):**
> ```bash
> bash <(curl -fsSL https://github.com/rezariski/ixsland/releases/latest/download/install-linux.sh)
> ```
>
> **Windows — satu klik:** unduh `Setup.exe`, jalankan, lalu **Berikutnya → Berikutnya → Selesai**.
> Wizard mendukung pemilihan folder tujuan, **Pasang / Perbaiki (Repair) / Copot Pemasangan**, serta terdaftar
> di *Pengaturan → Aplikasi → Aplikasi terinstal* Windows (Ubah / Copot).

---

## 📦 Dua Pilihan Platform: Linux & Windows (Linux/Windows)

`ixsland` hadir secara native untuk dua ekosistem sistem operasi utama dengan arsitektur yang dirancang khusus:
1. **Linux (Wayland / X11)**: Integrasi murni PipeWire `wpctl`, D-Bus MPRIS, KDE Plasma 6 KWin / Wayland layer.
2. **Windows (Windows 10 & Windows 11 64-bit)**: Integrasi Windows CoreAudio API, WinRT GSMTC Media Control, Low-Level Hardware Hooks, dan Standalone Installer `Setup.exe`.

---

## 🐧 1. Linux Edition

Pemasangan pada Linux membutuhkan waktu kurang dari 30 detik. Island muncul otomatis di **layar utama** dan
bisa dipindah ke layar mana pun lewat **Pengaturan → Tampilan → Layar Target**.

### Opsi A: Pemasangan Satu Klik — TANPA Python (Disarankan)

Paket rilis sudah berupa binari mandiri (Python + PyQt6 sudah dibundel di dalamnya):

```bash
bash <(curl -fsSL https://github.com/rezariski/ixsland/releases/latest/download/install-linux.sh)
```

Atau unduh manual lalu pasang:

```bash
curl -LO https://github.com/rezariski/ixsland/releases/latest/download/ixsland-linux-x64.tar.gz
tar -xzf ixsland-linux-x64.tar.gz
cd ixsland-linux-x64
./install.sh
```

Installer memasang binari ke `~/.local/share/ixsland/ixsland`, mendaftarkan unit systemd user,
membuat entri autostart, dan langsung menyalakan Dynamic Island.

### Opsi B: Menjalankan dari Kode Sumber (Developer)

Hanya untuk pengembang — butuh Python 3.10+ dan PyQt6:

```bash
# Arch Linux / CachyOS / Manjaro
sudo pacman -S python python-pyqt6 pipewire wireplumber qt6-declarative

# Ubuntu / Debian
sudo apt update && sudo apt install python3 python3-pyqt6 pipewire wireplumber

# Fedora
sudo dnf install python3 python3-pyqt6 pipewire wireplumber

git clone https://github.com/rezariski/ixsland.git
cd ixsland
chmod +x install.sh
./install.sh
```

Catatan: `wpctl` (PipeWire) dan `qdbus6` tetap dibutuhkan untuk kontrol volume/OSD dan penempatan jendela KWin.

### Manajemen Layanan (Linux)

```bash
systemctl --user status ixsland.service   # Cek status
systemctl --user restart ixsland.service  # Restart
journalctl --user -u ixsland -f           # Live log
./uninstall.sh                            # Hapus instalasi
```

---

## 🪟 2. Windows Edition (Windows 10 & 11 64-bit)

Mendukung penuh arsitektur **Windows 10 (64-bit, 1903+)** dan **Windows 11 (64-bit)**.

<div align="center">
  <img src="./assets/windows10_demo.png" width="88%" alt="ixsland Dynamic Island on Windows 10" />
  <p><em>Tangkapan layar ixsland aktif di desktop Windows 10 Pro 64-bit dengan pemutar musik tersinkronisasi.</em></p>
</div>

### Opsi A: Standalone Setup Installer (Paling Praktis, Tanpa Perlu Python)

1. Unduh **[`Setup.exe`](https://github.com/rezariski/ixsland/releases/latest/download/Setup.exe)** lalu jalankan.
2. Ikuti wizard gaya umum — cukup **Berikutnya → Berikutnya → Selesai**:
   - **Halaman sambutan** — info versi dan langkah pemasangan.
   - **Pilih lokasi pemasangan** (default: `C:\ixsland`, bisa diubah lewat *Jelajahi...*).
   - **Opsi pemasangan** — pilih tindakan:
     - `Pasang / Perbarui` — instalasi baru atau perbarui ke versi terbaru.
     - `Perbaiki (Repair)` — pasang ulang berkas tanpa menghapus pengaturan.
     - `Copot Pemasangan (Uninstall)` — hapus ixsland dari komputer.
     - Checkbox: pintasan Desktop, pintasan Menu Mulai, mulai otomatis saat Windows Startup.
   - **Proses** — progress bar + log pemasangan.
   - **Selesai** — opsi langsung menjalankan ixsland.
3. Island muncul di **layar utama**. Pengaturan bisa dibuka lewat ikon ⚙ pada island.
4. Terdaftar di **Pengaturan Windows → Aplikasi → Aplikasi terinstal** (Ubah = jalankan kembali wizard, Copot = mode uninstall).
   Mode sunyi tersedia: `Setup.exe --uninstall -q`.

### Opsi B: Menjalankan dari Kode Sumber (Developer)
Pastikan Anda menggunakan Python 3.10+ (64-bit):
```cmd
cd windows
pip install PyQt6 pycaw comtypes winsdk
python ixsland_win.py
```

---

## 🧪 Interactive Demo Showcase (Linux & Windows)

Ingin melihat simulasi seluruh modul animasi, HUD, dan notifikasi beraksi secara berurutan? Gunakan showcase runner bawaan:

### Pada Linux:
```bash
python3 ~/.local/share/ixsland/run-demo.py
```

### Pada Windows 10 / Windows 11:
- **Cara Instan (Tanpa Python)**: Klik ganda file **`windows/run-demo.bat`** atau jalankan via PowerShell:
  ```powershell
  powershell -ExecutionPolicy Bypass -File .\windows\run-demo.ps1
  ```
- **Via Python**:
  ```cmd
  python windows/run_demo.py
  ```

---

## 🚀 Feature Walkthrough

### 01. 🤖 Interactive OLED Mascot with Gaze Physics
<div align="center">
  <img src="./assets/01_mascot.png" width="85%" alt="OLED Mascot Feature" />
</div>

- **Mathematical Gaze Tracking**: Pupil mata robot mengikuti koordinat kursor mouse Anda secara real-time dengan pantulan 3D parallax.
- **Natural Blink & Blush Joy**: Berkedip alami setiap 3.8s dan tersenyum malu-senang (`^  ^`) dengan rona pipi pink saat kursor didekatkan.
- **Smart Idle Sleep Engine**: Jika kursor tidak bergerak selama 22 detik, maskot tertidur pulas dengan animasi `zZ`.

---

### 02. 🎵 Real-Time Media Hub & Live Seekbar
<div align="center">
  <img src="./assets/02_media_hub.png" width="85%" alt="Interactive Media Hub Feature" />
</div>

- **Sinkronisasi Dua Arah**: Membaca cover album, judul lagu, musisi, dan status putar dari Spotify, Chrome, Edge, Firefox via MPRIS (Linux) atau GSMTC (Windows).
- **Click-to-Seek Scrubbing**: Progress bar durasi berjalan detik demi detik. Klik di posisi mana saja untuk lompat ke detik yang diinginkan.
- **Equalizer Spektrum 120 BPM**: Batang frekuensi equalizer menari dinamis mengikuti ritme audio.

---

### 03. 🧲 Smart Auto-Collapse & Top Notch Docking
- **Penciutan Otomatis**: Saat mouse menjauh dari area island, Dynamic Island secara halus melipat kembali ke ukuran semula.
- **Top Notch Mode**: Opsi mengecilkan tampilan menjadi notch tipis di pucuk layar monitor untuk area kerja yang lebih bersih.
- **120ms Debounce Shield**: Pergerakan kursor yang melintas cepat tidak akan memicu kedipan yang tidak disengaja.

---

### 04. 🔊 Fluid Volume OSD & 150% Overboost Warning
<div align="center">
  <img src="./assets/03_volume_osd.png" width="85%" alt="Volume OSD Feature" />
</div>

- **Animasi Sangat Halus**: Perubahan level volume meluncur dengan kurva easing `OutCubic`.
- **Indikator Api Overboost**: Saat volume melebihi 100% (hingga batas boost 150%), aksen bar berubah menjadi jingga membara dengan ikon api `🔥`.

---

### 05. 🔠 Shift Lock & Caps Lock Persistent HUD
- **Indikator Aktif Menetap**: Saat Caps Lock / Shift Lock aktif, label kuning `CAPS LOCK ON` tetap menyala konsisten selama mengetik tanpa flicker atau kolaps prematur.
- **Transisi Halus Saat Nonaktif**: Saat dimatikan, indikator bertransisi elastis ke warna abu-abu `CAPS LOCK OFF` selama 1.5 detik lalu melipat otomatis kembali ke jam/media.
- **Deteksi Hardware Instan**: Membaca status register keyboard langsung pada event key release (`WM_KEYUP`).

---

### 06. 🕌 Offline Astronomical Prayer Time Engine & Smart Alerts
<div align="center">
  <img src="./assets/04_prayer_alert.png" width="85%" alt="Prayer Times and Alerts Feature" />
</div>

- **Matematika Astronomi 100% Offline**: Menghitung jadwal sholat (Subuh, Dzuhur, Ashar, Maghrib, Isya) secara lokal berdasarkan deklinasi matahari tanpa ketergantungan API pihak ketiga.
- **Auto-Pause Music Player**: Otomatis menghentikan pemutaran musik saat adzan berkumandang.
- **Desktop Chat Alerts**: Spanduk notifikasi elegan untuk pesan chat masuk (WhatsApp, Telegram, Discord).

---

## ⚙️ Configuration

Berkas konfigurasi tersimpan pada:
- **Linux**: `~/.local/share/ixsland/config.json`
- **Windows**: `C:\ixsland\config.json` (atau di folder aplikasi)

```json
{
  "target_screen": "primary",
  "top_margin": 16,
  "offset_x": 0,
  "pos_locked": false,
  "scale": 1.0,
  "bg_opacity": 98,
  "latitude": -6.2088,
  "longitude": 106.8456,
  "timezone": 7.0,
  "city": "Jakarta (WIB)",
  "pause_music_on_adzan": true,
  "enable_mascot": true,
  "autostart": true,
  "check_updates": true
}
```

| Opsi | Tipe | Penjelasan |
|---|---|---|
| `target_screen` | `string` | `"primary"` (monitor utama — **default**), atau nama layar terdeteksi (`"HDMI-A-1"`, `"DP-1"`, `"\\.\DISPLAY2"`). |
| `top_margin` | `integer` | Jarak pixel dari tepi atas layar (Linux default `16`, Windows `12`). |
| `offset_x` | `integer` | Geseran horizontal relatif terhadap titik tengah layar. |
| `pos_locked` | `boolean` | `true` = kunci posisi (drag dimatikan), `false` = bisa digeser. |
| `scale` | `float` | Skala ukuran island (`0.5`–`1.5`). |
| `bg_opacity` | `integer` | Kegelapan latar island dalam persen. |
| `latitude` / `longitude` | `float` | Titik koordinat bumi untuk perhitungan hisab waktu sholat. |
| `timezone` | `float` | Selisih waktu UTC (misal `7.0` untuk WIB, `8.0` untuk WITA). |
| `pause_music_on_adzan` | `boolean` | `true` untuk menjeda musik otomatis saat masuk waktu sholat. |
| `enable_mascot` | `boolean` | `true` untuk mengaktifkan maskot robot OLED interaktif. |
| `autostart` | `boolean` | Mulai otomatis saat login (Linux: `~/.config/autostart`, Windows: registry `Run`). |
| `check_updates` | `boolean` | Pemeriksaan versi baru otomatis ke GitHub Releases. |

> Semua opsi posisi juga bisa diatur langsung dari GUI: **Pengaturan → tab Tampilan → Penataan & Posisi**
> (tombol kunci 🔒/🔓, spinbox X/Y, Reset, Tengahkan, dan combo **Layar Target**).

---

## 🗒️ Changelog

### v1.3.0
**Fitur baru (Linux & Windows)**
- Tab **Tampilan** Windows kini 100% identik dengan Linux: grup **Penataan & Posisi** (tombol kunci posisi, spinbox koordinat X/Y, Reset X/Y, Tengahkan, dan pemilih **Layar Target**).
- **Drag manual** island (Windows & Linux) saat posisi tidak terkunci; kunci posisi mencegah geser tak sengaja.
- **Layar Target** bisa memilih layar mana pun yang terdeteksi; **default = layar utama** di Linux dan Windows.
- Pintasan menu klik kanan island: *Kunci/Buka Kunci Posisi* dan *Reset Posisi Tengah*.
- Installer Windows bergaya wizard: pilih folder tujuan, **Pasang / Perbaiki (Repair) / Copot Pemasangan**, shortcut, autostart, terdaftar di *Aplikasi terinstal* Windows.
- Paket Linux binari mandiri (`ixsland-linux-x64.tar.gz`) + pemasang satu baris — **pengguna tidak perlu memasang Python**.

**Perbaikan bug**
- Tab dialog Pengaturan di Windows tidak lagi terpotong (`◄►` / `...`) — semua 6 tab dan label terbaca jelas.
- Tinggi dialog Pengaturan otomatis menyesuaikan konten terbesar, mencegah baris tombol Reset X/Y terkompresi atau teks tombol hilang di Windows.
- Tab **Tentang** Windows memakai tema gelap konsisten (#151822) dan bisa di-*scroll*, seluruh teks profil, status pembaruan, dan tautan terbaca jelas.
- Uninstaller Windows (`Uninstall.exe` / `Setup.exe --uninstall`) memindahkan proses dirinya ke `%TEMP%` secara otomatis sehingga folder instalasi `C:\ixsland` terhapus bersih tanpa terkunci berkas eksekutabel.
- Tombol **Batal** pada dialog Pengaturan Windows mengembalikan skala, transparansi, posisi, dan status kunci seperti semula.
- Path ikon autostart Linux menunjuk ke `~/.local/share/ixsland/icon.png` (sebelumnya menunjuk folder temp PyInstaller yang bisa hilang).
- `install.sh` selalu me-*restart* layanan, sehingga versi terbaru langsung dipakai saat perbaruan pemasangan.

---

<div align="center">

## ☕ Treat Me a Coffee!

Jika Anda menyukai proyek Dynamic Island `ixsland` ini di Linux maupun Windows dan ingin mendukung pengembangannya, donasi secangkir kopi sangat berarti! 🚀

<br/>

<a href="https://saweria.co/rezariski42" target="_blank">
  <img src="https://img.shields.io/badge/Saweria-Treat%20Me%20A%20Coffee-F59E0B?style=for-the-badge&logo=coffeescript&logoColor=white&labelColor=140E26" height="42" alt="Saweria Tip" />
</a>

<br/>
<br/>

**Saweria Tip Link**: [saweria.co/rezariski42](https://saweria.co/rezariski42)

<br/>

<sub>Crafted with passion by **Reza Rizki** • Built for Linux & Windows (Linux/Windows) • Licensed under GPL-3.0</sub>

</div>
