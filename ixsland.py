#!/usr/bin/env python3
"""
ixsland Dynamic Island for Linux (KDE Wayland / X11)
Targeted for Primary / Main Display - Full Feature Parity & Fixed Anchoring
Includes Interactive Eye-Tracking Robot Mascot & Unclipped Fluid Morphing
"""

import sys
import os
import re
import math
import time
import json
import glob
import tempfile
import shutil
import urllib.request
import subprocess
from datetime import datetime, date, timedelta

from PyQt6.QtCore import (
    Qt, QTimer, QPoint, QRect, QRectF, QSize, QPointF, QUrl,
    QVariantAnimation, QEasingCurve, pyqtSignal, pyqtSlot, QObject, QThread
)
from PyQt6.QtWidgets import (
    QApplication, QWidget, QGraphicsDropShadowEffect, QMenu, QSystemTrayIcon,
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QSlider, QComboBox,
    QCheckBox, QPushButton, QTabWidget, QGroupBox, QSpinBox
)
from PyQt6.QtGui import (
    QPainter, QColor, QBrush, QPen, QPainterPath,
    QFont, QPixmap, QAction, QRegion, QIcon, QCursor, QDesktopServices
)
from PyQt6 import QtDBus

CONFIG_DIR = os.path.expanduser("~/.local/share/ixsland")
CONFIG_PATH = os.path.join(CONFIG_DIR, "config.json")
CACHE_DIR = "/tmp/ixsland_cache"
NOTIF_FILE = "/tmp/macos-notifications-history.json"

# Build PyInstaller (binari mandiri, pengguna TIDAK perlu memasang Python):
# aset diekstrak ke _MEIPASS, sedangkan versi sumber berjalan dari folder repo.
IS_FROZEN = bool(getattr(sys, "frozen", False))
APP_DIR = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
ASSETS_DIR = os.path.join(APP_DIR, "assets")

def app_exec_path():
    """Path yang dipakai desktop entry/autostart untuk menjalankan aplikasi."""
    if IS_FROZEN:
        return os.path.abspath(sys.executable)
    script = os.path.join(APP_DIR, "ixsland.py")
    if os.path.exists(script):
        return script
    return os.path.abspath(sys.argv[0])
AUTOSTART_DIR = os.path.expanduser("~/.config/autostart")
PLUGIN_NAME_FILE = os.path.join(CACHE_DIR, "kwin_script_plugin_name")
AUTOSTART_FILE = os.path.join(AUTOSTART_DIR, "ixsland.desktop")
os.makedirs(CACHE_DIR, exist_ok=True)
os.makedirs(CONFIG_DIR, exist_ok=True)

# Fixed Canvas Geometry (Wayland toplevel MUST never resize to keep KWin position permanent)
CANVAS_W = 380
CANVAS_H = 175

CITY_COORDINATES = {
    "Jakarta (WIB)": (-6.2088, 106.8456, 7.0),
    "Surabaya (WIB)": (-7.2575, 112.7521, 7.0),
    "Bandung (WIB)": (-6.9175, 107.6191, 7.0),
    "Semarang (WIB)": (-6.9667, 110.4167, 7.0),
    "Yogyakarta (WIB)": (-7.7956, 110.3695, 7.0),
    "Medan (WIB)": (3.5952, 98.6722, 7.0),
    "Makassar (WITA)": (-5.1477, 119.4327, 8.0),
    "Denpasar (WITA)": (-8.6705, 115.2126, 8.0),
    "Jayapura (WIT)": (-2.5337, 140.7181, 9.0)
}

APP_VERSION = "1.3.0"
GITHUB_REPO = "rezariski/ixsland"
UPDATE_CHECK_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"

DEFAULT_CONFIG = {
    "target_screen": "primary",
    "top_margin": 16,
    "offset_x": 0,
    "pos_locked": False,
    "scale": 1.0,
    "bg_opacity": 98,
    "enable_mascot": True,
    "enable_marquee": True,
    "latitude": -6.2088,
    "longitude": 106.8456,
    "timezone": 7.0,
    "city": "Jakarta (WIB)",
    "pause_music_on_adzan": True,
    "autostart": True,
    "enable_notifications": True,
    "enable_clipboard_bubble": True,
    "enable_game_mode": True,
    "enable_battery_alert": True,
    "enable_privacy_dot": True,
    "check_updates": True
}

def load_config():
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                cfg = json.load(f)
                return {**DEFAULT_CONFIG, **cfg}
        except Exception:
            pass
    return DEFAULT_CONFIG.copy()

def save_config(cfg):
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=4)
    except Exception:
        pass

# --- PRAYER TIMES CALCULATION (OFFLINE PRAYER TIMES ENGINE) ---
def calculate_prayer_times(lat, lng, tz_offset, dt=None):
    if dt is None:
        dt = date.today()
    day_of_year = dt.timetuple().tm_yday
    b = 2 * math.pi * (day_of_year - 81) / 365.0
    eot = 9.87 * math.sin(2 * b) - 7.53 * math.cos(b) - 1.5 * math.sin(b)
    solar_noon_minutes = 720 - (4 * lng) - eot + (tz_offset * 60)
    
    decl = 23.45 * math.sin(math.radians(360 / 365.0 * (day_of_year - 81)))
    decl_rad = math.radians(decl)
    lat_rad = math.radians(lat)
    
    def hour_angle(alt):
        alt_rad = math.radians(alt)
        num = math.sin(alt_rad) - math.sin(lat_rad) * math.sin(decl_rad)
        den = math.cos(lat_rad) * math.cos(decl_rad)
        cos_ha = num / den
        if cos_ha > 1: return 0.0
        if cos_ha < -1: return 180.0
        return math.degrees(math.acos(cos_ha))
    
    ha_fajr = hour_angle(-20.0)
    ha_maghrib = hour_angle(-0.833)
    ha_isha = hour_angle(-18.0)
    
    asr_alt = math.degrees(math.atan(1.0 / (1.0 + math.tan(math.radians(abs(lat - decl))))))
    ha_asr = hour_angle(asr_alt)
    
    fajr_min = solar_noon_minutes - (ha_fajr * 4)
    dhuhr_min = solar_noon_minutes + 2
    asr_min = solar_noon_minutes + (ha_asr * 4)
    maghrib_min = solar_noon_minutes + (ha_maghrib * 4)
    isha_min = solar_noon_minutes + (ha_isha * 4)
    
    def min_to_str(m):
        m = int(round(m))
        h = (m // 60) % 24
        mn = m % 60
        return f"{h:02d}:{mn:02d}"

    def min_to_mins(m):
        return int(round(m))
    
    return [
        ("Subuh", min_to_str(fajr_min), min_to_mins(fajr_min)),
        ("Dzuhur", min_to_str(dhuhr_min), min_to_mins(dhuhr_min)),
        ("Ashar", min_to_str(asr_min), min_to_mins(asr_min)),
        ("Maghrib", min_to_str(maghrib_min), min_to_mins(maghrib_min)),
        ("Isya", min_to_str(isha_min), min_to_mins(isha_min))
    ]

# --- MPRIS MEDIA MONITOR ---
class MediaController(QObject):
    mediaChanged = pyqtSignal(dict)
    
    def __init__(self):
        super().__init__()
        self.bus = QtDBus.QDBusConnection.sessionBus()
        self.current_player = None
        self.current_info = {
            "status": "Stopped",
            "title": "",
            "artist": "",
            "art_url": "",
            "art_pixmap": None,
            "length": 0,
            "position": 0,
            "player": "",
            "trackid": ""
        }
        self.cached_art_url = None
        self.cached_pixmap = None
        self.is_mock = False
        self.mock_deadline = 0.0
        self._mock_counter = 0
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.poll_media)
        self.timer.start(500)
        self.poll_media()

    def get_active_players(self):
        interface = QtDBus.QDBusInterface(
            "org.freedesktop.DBus",
            "/org/freedesktop/DBus",
            "org.freedesktop.DBus",
            self.bus
        )
        reply = interface.call("ListNames")
        if reply.type() == QtDBus.QDBusMessage.MessageType.ReplyMessage:
            names = reply.arguments()[0]
            return [n for n in names if n.startswith("org.mpris.MediaPlayer2.")]
        return []

    def poll_media(self):
        if getattr(self, "is_mock", False):
            if time.time() > self.mock_deadline:
                self.is_mock = False
            else:
                if self.current_info.get("status") == "Playing":
                    length = self.current_info.get("length", 0)
                    self._mock_counter += 1
                    if length > 0 and self._mock_counter % 2 == 0:
                        self.current_info["position"] = (self.current_info.get("position", 0) + 1) % length
                self.mediaChanged.emit(self.current_info)
                return
        players = self.get_active_players()
        if not players:
            if self.current_info["status"] != "Stopped":
                self.current_info = {
                    "status": "Stopped", "title": "", "artist": "",
                    "art_url": "", "art_pixmap": None, "length": 0, "position": 0, "player": ""
                }
                self.mediaChanged.emit(self.current_info)
            return

        best_player = players[0]
        best_props = None
        
        for p in players:
            msg = QtDBus.QDBusMessage.createMethodCall(
                p, "/org/mpris/MediaPlayer2", "org.freedesktop.DBus.Properties", "GetAll"
            )
            msg.setArguments(["org.mpris.MediaPlayer2.Player"])
            reply = self.bus.call(msg, QtDBus.QDBus.CallMode.Block, 100)
            if reply.type() == QtDBus.QDBusMessage.MessageType.ReplyMessage:
                props = reply.arguments()[0]
                status = str(props.get("PlaybackStatus", "Stopped"))
                if status == "Playing":
                    best_player = p
                    best_props = props
                    break
                elif best_props is None:
                    best_props = props

        if not best_props:
            return

        status = str(best_props.get("PlaybackStatus", "Stopped"))
        meta = best_props.get("Metadata", {})
        title = str(meta.get("xesam:title", ""))
        artists = meta.get("xesam:artist", [])
        artist = ", ".join(artists) if isinstance(artists, list) else str(artists)
        art_url = str(meta.get("mpris:artUrl", ""))
        trackid = str(meta.get("mpris:trackid", ""))
        
        try:
            length = int(meta.get("mpris:length", 0)) // 1000000
        except Exception:
            length = 0

        pos = 0
        try:
            pos_msg = QtDBus.QDBusMessage.createMethodCall(
                best_player, "/org/mpris/MediaPlayer2", "org.freedesktop.DBus.Properties", "Get"
            )
            pos_msg.setArguments(["org.mpris.MediaPlayer2.Player", "Position"])
            pos_reply = self.bus.call(pos_msg, QtDBus.QDBus.CallMode.Block, 80)
            if pos_reply.type() == QtDBus.QDBusMessage.MessageType.ReplyMessage:
                pos = int(pos_reply.arguments()[0]) // 1000000
        except Exception:
            pos = 0

        player_name = best_player.replace("org.mpris.MediaPlayer2.", "").capitalize()
        
        if art_url != self.cached_art_url:
            self.cached_art_url = art_url
            self.cached_pixmap = self.fetch_art(art_url)

        changed = (
            self.current_info["status"] != status or
            self.current_info["title"] != title or
            self.current_info["artist"] != artist or
            self.current_player != best_player or
            self.current_info.get("position", 0) != pos or
            self.current_info.get("length", 0) != length
        )

        self.current_player = best_player
        self.current_info = {
            "status": status,
            "title": title,
            "artist": artist,
            "art_url": art_url,
            "art_pixmap": self.cached_pixmap,
            "length": length,
            "position": pos,
            "player": player_name,
            "trackid": trackid
        }

        if changed:
            self.mediaChanged.emit(self.current_info)

    def seek(self, target_seconds):
        if not self.current_player:
            return
        trackid = self.current_info.get("trackid", "")
        if not trackid:
            return
        try:
            target_us = str(int(target_seconds * 1000000))
            subprocess.Popen([
                "qdbus6", self.current_player, "/org/mpris/MediaPlayer2",
                "org.mpris.MediaPlayer2.Player.SetPosition", trackid, target_us
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            self.current_info["position"] = int(target_seconds)
            self.mediaChanged.emit(self.current_info)
        except Exception:
            pass

    def fetch_art(self, url):
        if not url:
            return None
        try:
            if url.startswith("file://"):
                path = url[7:]
                pix = QPixmap(path)
                return pix if not pix.isNull() else None
            elif url.startswith("http://") or url.startswith("https://"):
                hashed = str(abs(hash(url))) + ".jpg"
                dest = os.path.join(CACHE_DIR, hashed)
                if not os.path.exists(dest):
                    urllib.request.urlretrieve(url, dest)
                pix = QPixmap(dest)
                return pix if not pix.isNull() else None
        except Exception:
            return None
        return None

    def set_mock_track(self, title, artist, art_path=None, duration=195):
        pix = QPixmap(art_path) if art_path and os.path.exists(art_path) else None
        self.is_mock = True
        self.mock_deadline = time.time() + 120
        self._mock_counter = 0
        self.current_info = {
            "status": "Playing",
            "title": title,
            "artist": artist,
            "art_url": art_path or "",
            "art_pixmap": pix,
            "length": duration,
            "position": 18,
            "player": "Spotify",
            "trackid": ""
        }
        self.mediaChanged.emit(self.current_info)

    def play_pause(self):
        if getattr(self, "is_mock", False):
            new_st = "Paused" if self.current_info.get("status") == "Playing" else "Playing"
            self.current_info["status"] = new_st
            self.mediaChanged.emit(self.current_info)
            return
        if self.current_player:
            msg = QtDBus.QDBusMessage.createMethodCall(
                self.current_player, "/org/mpris/MediaPlayer2",
                "org.mpris.MediaPlayer2.Player", "PlayPause"
            )
            self.bus.call(msg, QtDBus.QDBus.CallMode.NoBlock)
            QTimer.singleShot(80, self.poll_media)

    def next_track(self):
        if self.current_player:
            msg = QtDBus.QDBusMessage.createMethodCall(
                self.current_player, "/org/mpris/MediaPlayer2",
                "org.mpris.MediaPlayer2.Player", "Next"
            )
            self.bus.call(msg, QtDBus.QDBus.CallMode.NoBlock)
            QTimer.singleShot(120, self.poll_media)

    def prev_track(self):
        if self.current_player:
            msg = QtDBus.QDBusMessage.createMethodCall(
                self.current_player, "/org/mpris/MediaPlayer2",
                "org.mpris.MediaPlayer2.Player", "Previous"
            )
            self.bus.call(msg, QtDBus.QDBus.CallMode.NoBlock)
            QTimer.singleShot(120, self.poll_media)

# --- SYSTEM VOLUME HELPER ---
def get_volume():
    try:
        out = subprocess.check_output(["wpctl", "get-volume", "@DEFAULT_AUDIO_SINK@"], timeout=1).decode()
        parts = out.strip().split()
        vol = float(parts[1]) if len(parts) > 1 else 0.0
        muted = "[MUTED]" in out
        return int(round(vol * 100)), muted
    except Exception:
        return 50, False

def change_volume(delta):
    try:
        sign = "+" if delta > 0 else "-"
        subprocess.run(["wpctl", "set-volume", "@DEFAULT_AUDIO_SINK@", f"{abs(delta)}%{sign}"], timeout=1)
    except Exception:
        pass

# --- CAPS LOCK HELPER ---
def get_caps_lock_state():
    try:
        paths = glob.glob("/sys/class/leds/*capslock*/brightness")
        for p in paths:
            with open(p, "r") as f:
                val = f.read().strip()
                if val == "1":
                    return True
        return False
    except Exception:
        return False

# --- BATTERY HELPER (Linux /sys power_supply) ---
def get_system_battery():
    """Returns (has_battery, percent, is_charging)."""
    try:
        base = "/sys/class/power_supply"
        if not os.path.isdir(base):
            return False, 100, True
        for name in os.listdir(base):
            d = os.path.join(base, name)
            try:
                with open(os.path.join(d, "type")) as f:
                    if f.read().strip() != "Battery":
                        continue
            except Exception:
                continue
            pct = 100
            try:
                with open(os.path.join(d, "capacity")) as f:
                    pct = int(f.read().strip())
            except Exception:
                pass
            charging = True
            try:
                with open(os.path.join(d, "status")) as f:
                    st = f.read().strip().lower()
                    charging = st in ("charging", "full")
            except Exception:
                pass
            return True, pct, charging
    except Exception:
        pass
    return False, 100, True

# --- PRIVACY DOT HELPER (Linux /proc fd scan for camera & mic capture) ---
def check_linux_privacy_usage():
    """Best-effort scan for camera (/dev/video*) and microphone (capture PCM) use."""
    cam_active = False
    mic_active = False
    try:
        for pid in os.listdir("/proc"):
            if not pid.isdigit():
                continue
            fd_dir = os.path.join("/proc", pid, "fd")
            try:
                for fd in os.listdir(fd_dir):
                    try:
                        target = os.readlink(os.path.join(fd_dir, fd))
                    except Exception:
                        continue
                    if target.startswith("/dev/video"):
                        cam_active = True
                    elif target.startswith("/dev/snd/pcm") and target.endswith("c"):
                        mic_active = True
            except Exception:
                continue
            if cam_active and mic_active:
                break
    except Exception:
        pass
    return cam_active, mic_active

def parse_version_tuple(v_str):
    if not v_str:
        return (0, 0, 0)
    nums = re.findall(r"\d+", str(v_str))
    return tuple(map(int, nums)) if nums else (0, 0, 0)

# --- BACKGROUND GITHUB RELEASES UPDATE CHECKER ---
class UpdateCheckerThread(QThread):
    """Checks GitHub Releases for new ixsland versions in background."""
    updateChecked = pyqtSignal(bool, str, str, str)  # has_update, remote_tag, release_url, release_notes

    def __init__(self, parent=None, timeout=6):
        super().__init__(parent)
        self.timeout = timeout

    def run(self):
        req = urllib.request.Request(
            UPDATE_CHECK_URL,
            headers={
                "User-Agent": f"ixsland-Linux/{APP_VERSION}",
                "Accept": "application/vnd.github.v3+json"
            }
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read().decode("utf-8", "ignore"))
                tag = data.get("tag_name", "").strip()
                url = data.get("html_url", f"https://github.com/{GITHUB_REPO}/releases/latest")
                body = data.get("body", "")
                remote_ver = parse_version_tuple(tag)
                local_ver = parse_version_tuple(APP_VERSION)
                has_update = remote_ver > local_ver
                self.updateChecked.emit(has_update, tag or APP_VERSION, url, body or "")
        except Exception as e:
            self.updateChecked.emit(False, APP_VERSION, "", str(e))

# --- LINUX XDG AUTOSTART SYNCHRONIZER ---
def sync_autostart_registration(enabled=True):
    try:
        if enabled:
            os.makedirs(AUTOSTART_DIR, exist_ok=True)
            target = app_exec_path()
            if IS_FROZEN:
                exec_line = f'"{target}"'
            else:
                exec_line = f'python3 "{target}"'
            # Salin ikon ke folder konfigurasi supaya path desktop entry
            # tetap valid walau binari PyInstaller diekstrak ke folder temp.
            icon = os.path.join(CONFIG_DIR, "icon.png")
            try:
                src_icon = os.path.join(ASSETS_DIR, "icon.png")
                if os.path.exists(src_icon) and (
                        not os.path.exists(icon)
                        or os.path.getsize(src_icon) != os.path.getsize(icon)):
                    shutil.copy2(src_icon, icon)
            except Exception:
                pass
            if not os.path.exists(icon):
                icon = os.path.join(ASSETS_DIR, "icon.png")
            content = (
                "[Desktop Entry]\n"
                "Type=Application\n"
                "Name=ixsland Dynamic Island\n"
                "Comment=Dynamic Island overlay untuk Linux\n"
                f"Exec={exec_line}\n"
                f"Icon={icon}\n"
                "Terminal=false\n"
                "X-GNOME-Autostart-enabled=true\n"
                "StartupNotify=false\n"
            )
            with open(AUTOSTART_FILE, "w", encoding="utf-8") as f:
                f.write(content)
        else:
            if os.path.exists(AUTOSTART_FILE):
                os.unlink(AUTOSTART_FILE)
    except Exception:
        pass

# --- SMOOTH MARQUEE TEXT DRAWER ---
def draw_marquee_text(p, text, rect, font, color, offset):
    p.setFont(font)
    fm = p.fontMetrics()
    text_w = fm.horizontalAdvance(text)
    if text_w <= rect.width():
        p.setPen(color)
        p.drawText(rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, text)
    else:
        p.save()
        p.setClipRect(rect)
        gap = 40
        span = text_w + gap
        shift = int(offset) % span
        p.setPen(color)
        p.drawText(int(rect.x() - shift), rect.y(), text_w, rect.height(), Qt.AlignmentFlag.AlignVCenter, text)
        p.drawText(int(rect.x() - shift + span), rect.y(), text_w, rect.height(), Qt.AlignmentFlag.AlignVCenter, text)
        p.restore()

# --- KWIN GLOBAL CURSOR TRACKER (FOR INTERACTIVE ROBOT MASCOT) ---
class KWinCursorTracker(QObject):
    def __init__(self):
        super().__init__()
        self.script_id = None
        self.script_file = None
        self.ready = False
        self._verify_tries = 0
        # Nama plugin unik per proses: KWin menyimpan script lama per nama dan
        # loadScript dengan nama yang sama tidak menggantinya (pin jadi mati).
        self.plugin_name = f"ixsland_cursor_{os.getpid()}"
        self.setup_kwin_script()

    def mark_ready(self):
        self.ready = True

    def _unload_script(self, name):
        """Buang script KWin bernama `name` (proses lama bisa terbunuh tanpa cleanup)."""
        try:
            subprocess.run([
                "qdbus6", "org.kde.KWin", "/Scripting",
                "org.kde.kwin.Scripting.unloadScript", name
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=2)
        except Exception:
            pass

    @staticmethod
    def _previous_plugin_names():
        names = {"ixsland_cursor"}          # nama lama (versi sebelumnya)
        try:
            if os.path.exists(PLUGIN_NAME_FILE):
                with open(PLUGIN_NAME_FILE) as fh:
                    old = fh.read().strip()
                if old:
                    names.add(old)
        except Exception:
            pass
        return names

    def _load_and_run(self):
        """Muat + jalankan script KWin. True kalau KWin mengonfirmasi script jalan."""
        last_err = ""
        script_id = None
        for _ in range(3):
            try:
                out = subprocess.check_output([
                    "qdbus6", "org.kde.KWin", "/Scripting",
                    "org.kde.kwin.Scripting.loadScript",
                    self.script_file, self.plugin_name
                ], stderr=subprocess.STDOUT, timeout=3).decode().strip()
            except subprocess.CalledProcessError as e:
                last_err = (e.output or b"").decode(errors="replace").strip()[-200:]
                out = ""
            except Exception as e:
                last_err = str(e)
                out = ""
            if out.isdigit():
                script_id = out
                break
            time.sleep(0.3)
        if not script_id:
            print(f"[ixsland] load script KWin gagal: {last_err}", flush=True)
            return False

        self.script_id = script_id
        print(f"[ixsland] script KWin dimuat name={self.plugin_name} id={script_id}", flush=True)
        try:
            with open(PLUGIN_NAME_FILE, "w") as fh:
                fh.write(self.plugin_name)
        except Exception:
            pass

        # KWin perlu waktu menyiapkan objek script; run terlalu cepat diam-diam
        # gagal (returncode 0 tapi script tidak dieksekusi).
        time.sleep(0.4)
        for attempt in range(3):
            try:
                proc = subprocess.run([
                    "qdbus6", "org.kde.KWin", f"/Scripting/Script{script_id}",
                    "org.kde.kwin.Script.run"
                ], capture_output=True, timeout=3)
                if proc.returncode == 0:
                    subprocess.run([
                        "qdbus6", "org.kde.KWin", "/Scripting",
                        "org.kde.kwin.Scripting.start"
                    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=2)
                    print(f"[ixsland] script KWin dijalankan id={script_id} "
                          f"out={(proc.stdout or b'').decode(errors='replace').strip()[:120]!r}", flush=True)
                    return True
                last_err = (proc.stderr or b"").decode(errors="replace").strip()[-200:]
            except Exception as e:
                last_err = str(e)
            time.sleep(0.4)
        print(f"[ixsland] jalankan script KWin gagal: {last_err}", flush=True)
        return False

    def _verify_ready(self):
        """Script dianggap hidup hanya setelah memanggil kwinScriptReady."""
        if self.ready:
            return
        self._verify_tries += 1
        if self._verify_tries > 3:
            print("[ixsland] script KWin pin/cursor TIDAK aktif — posisi island "
                  "akan mengikuti penempatan KWin", flush=True)
            return
        # Script.run kadang tidak mengeksekusi apa pun; paksa lewat Scripting.start()
        print("[ixsland] script KWin belum memberi sinyal siap — paksa start()", flush=True)
        self._start_all_scripts()
        QTimer.singleShot(2500, self._verify_ready)

    def setup_kwin_script(self):
        try:
            try:
                subprocess.run([
                    "qdbus6", "org.kde.KWin", "/Scripting",
                    "org.kde.kwin.Scripting.unloadScript", "ixsland_cursor"
                ], stderr=subprocess.DEVNULL, timeout=1)
            except Exception:
                pass

            code = """
            var lastSent = 0;
            var lastRealActive = null;
            try {
                workspace.cursorPosChanged.connect(function() {
                    var now = Date.now();
                    if (now - lastSent > 35) {
                        lastSent = now;
                        callDBus('org.ixsland.Island', '/Island', '', 'setCursor', Math.round(workspace.cursorPos.x), Math.round(workspace.cursorPos.y));
                    }
                });
            } catch (e) {}
            try {
                callDBus('org.ixsland.Island', '/Island', '', 'setCursor', Math.round(workspace.cursorPos.x), Math.round(workspace.cursorPos.y));
            } catch (e) {}

            function isIgnorableWin(w) {
                try {
                    if (!w) return true;
                    if (isIslandWin(w)) return true;
                    var rc = (w.resourceClass || "").toLowerCase();
                    if (rc === "plasmashell" || rc === "ksplashqml" || rc === "ksmserver" || rc === "kwin_wayland") return true;
                    if (w.desktopWindow) return true;
                    if (w.dock) return true;
                } catch (e) {}
                return false;
            }
            function reportActiveWin() {
                try {
                    placeAllIslands();
                    var a = workspace.activeWindow;
                    if (a && isIslandWin(a)) {
                        if (lastRealActive) {
                            try { workspace.activeWindow = lastRealActive; } catch (e) {}
                        }
                    } else if (a && !isIgnorableWin(a)) {
                        lastRealActive = a;
                    }
                    var w = (a && !isIslandWin(a) && !isIgnorableWin(a)) ? a : lastRealActive;
                    if (w && !isIgnorableWin(w)) {
                        var g = w.frameGeometry;
                        callDBus('org.ixsland.Island', '/Island', '', 'setActiveWindowGeom', Math.round(g.x), Math.round(g.y), Math.round(g.width), Math.round(g.height));
                    } else {
                        callDBus('org.ixsland.Island', '/Island', '', 'setActiveWindowGeom', 0, 0, 0, 0);
                    }
                } catch (e) {}
            }
            try { workspace.activeWindowChanged.connect(reportActiveWin); } catch (e) {}
            try { workspace.windowActivated.connect(reportActiveWin); } catch (e) {}
            reportActiveWin();

            // --- Pin ixsland island windows & ensure ALWAYS ON TOP (AboveLayer) across all desktops ---
            function isIslandWin(w) {
                if (!w) return false;
                var c = (w.caption || "");
                return c.indexOf("IXSLAND") === 0;
            }
            function placeIslandWin(w) {
                try {
                    if (!isIslandWin(w)) return;

                    // Enforce topmost layer (AboveLayer) across all virtual desktops
                    try {
                        if (!w.keepAbove) w.keepAbove = true;
                        if (!w.onAllDesktops) w.onAllDesktops = true;
                        if (!w.skipTaskbar) w.skipTaskbar = true;
                        if (!w.skipPager) w.skipPager = true;
                        if (!w.skipSwitcher) w.skipSwitcher = true;
                    } catch (e0) {}

                    if (w.caption && w.caption.indexOf("IXSLAND:") === 0) {
                        var parts = w.caption.substring(8).split(",");
                        if (parts.length >= 4) {
                            var x = parseInt(parts[0], 10);
                            var y = parseInt(parts[1], 10);
                            var ww = parseInt(parts[2], 10);
                            var hh = parseInt(parts[3], 10);
                            if (!isNaN(x) && !isNaN(y) && !isNaN(ww) && !isNaN(hh)) {
                                var fg = w.frameGeometry;
                                if (fg.x !== x || fg.y !== y || fg.width !== ww || fg.height !== hh) {
                                    try {
                                        w.frameGeometry = { x: x, y: y, width: ww, height: hh };
                                    } catch (e1) {}
                                    if (lastRealActive) {
                                        try { workspace.activeWindow = lastRealActive; } catch (e2) {}
                                    }
                                }
                            }
                        }
                    }
                } catch (e) {}
            }
            function placeAllIslands() {
                try {
                    var list = workspace.windowList ? workspace.windowList() : workspace.clientList();
                    for (var i = 0; i < list.length; i++) { placeIslandWin(list[i]); }
                } catch (e) {}
            }
            try {
                workspace.windowAdded.connect(function(w) {
                    placeIslandWin(w);
                    if (isIslandWin(w)) {
                        if (lastRealActive) {
                            try { workspace.activeWindow = lastRealActive; } catch (e) {}
                        }
                        try {
                            w.keepAboveChanged.connect(function() {
                                if (!w.keepAbove) w.keepAbove = true;
                            });
                        } catch (e_ka) {}
                    }
                    try { w.captionChanged.connect(function() { placeIslandWin(w); }); } catch (e) {}
                    try { w.frameGeometryChanged.connect(function() { placeIslandWin(w); }); } catch (e) {}
                });
            } catch (e) {}
            try {
                workspace.activeWindowChanged.connect(function() {
                    placeAllIslands();
                });
            } catch (e) {}
            placeAllIslands();
            try { callDBus('org.ixsland.Island', '/Island', '', 'kwinScriptReady'); } catch (e) {}
            """
            f = tempfile.NamedTemporaryFile("w", suffix=".js", delete=False)
            f.write(code)
            f.flush()
            f.close()
            self.script_file = f.name

            # Buang script milik proses sebelumnya SETELAH script baru jalan:
            # unload sebelum load menggeser indeks id di KWin sehingga Script.run
            # bisa menunjuk script yang salah (pin tidak pernah aktif).
            prev_names = self._previous_plugin_names() - {self.plugin_name}
            time.sleep(0.15)
            if not self._load_and_run():
                print("[ixsland] script KWin pin/cursor gagal dipasang", flush=True)
                return
            for _old in prev_names:
                self._unload_script(_old)
            QTimer.singleShot(2500, self._verify_ready)
        except Exception as e:
            print(f"[ixsland] setup script KWin gagal: {e}", flush=True)

    @staticmethod
    def _start_all_scripts():
        """Jalankan semua script KWin yang termuat (fallback kalau Script.run tidak jalan)."""
        try:
            proc = subprocess.run([
                "qdbus6", "org.kde.KWin", "/Scripting",
                "org.kde.kwin.Scripting.start"
            ], capture_output=True, timeout=3)
            return proc.returncode == 0
        except Exception:
            return False

    def cleanup(self):
        try:
            if self.script_id:
                subprocess.run([
                    "qdbus6", "org.kde.KWin", f"/Scripting/Script{self.script_id}",
                    "org.kde.kwin.Script.stop"
                ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=1)
            self._unload_script(self.plugin_name)
            if os.path.exists(PLUGIN_NAME_FILE):
                with open(PLUGIN_NAME_FILE) as fh:
                    if fh.read().strip() == self.plugin_name:
                        os.unlink(PLUGIN_NAME_FILE)
        except Exception:
            pass
        if self.script_file and os.path.exists(self.script_file):
            try:
                os.unlink(self.script_file)
            except Exception:
                pass


# --- MINIMIZE TOP NOTCH TRIGGER ---
class HiddenTriggerWidget(QWidget):
    def __init__(self, parent_island):
        super().__init__(None)
        self.island = parent_island
        self.setWindowTitle("IXSLAND_TRIGGER")
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool |
            Qt.WindowType.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.resize(130, 8)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("Dynamic Island diminimalkan\nSentuh kursor atau klik di sini untuk memunculkan")

    def enterEvent(self, event):
        self.island.toggle_minimize()
        super().enterEvent(event)

    def mousePressEvent(self, event):
        self.island.toggle_minimize()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor(0, 180, 216, 180)))
        p.drawRoundedRect(QRectF(15, 0, 100, 5), 2.5, 2.5)


# --- SLEEK FLUENT UI SETTINGS DIALOG ---
class SettingsDialog(QDialog):
    def __init__(self, parent_island):
        super().__init__(None)
        self.island = parent_island
        self.cfg = self.island.cfg.copy()
        self.orig_bg_opacity = self.island.cfg.get("bg_opacity", 98)
        self.orig_scale = self.island.cfg.get("scale", 1.0)
        self.orig_offset_x = self.island.cfg.get("offset_x", 0)
        self.orig_top_margin = self.island.cfg.get("top_margin", 16)
        self.orig_pos_locked = self.island.cfg.get("pos_locked", False)
        self._suppress_pos = False

        self.setWindowTitle("Pengaturan Dynamic Island")
        icon_path = os.path.join(ASSETS_DIR, "icon.png")
        if not os.path.exists(icon_path):
            icon_path = os.path.join(ASSETS_DIR, "icon.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        # Lebar cukup supaya 6 tab muat tanpa tombol scroll dan kolom
        # spinbox/kombo tidak terpotong ("····") saat dialog dibuka.
        self.resize(760, 570)
        self.setMinimumSize(700, 520)
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.WindowCloseButtonHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setStyleSheet("""
            QDialog { background-color: #101218; color: #EDEDED; font-family: 'Cantarell', 'Segoe UI', Arial; }
            QTabWidget::pane { border: 1px solid rgba(255, 255, 255, 0.12); background: #151822; border-radius: 8px; }
            QTabBar::tab { background: #0E1016; color: #A0A5B5; padding: 9px 14px; border-top-left-radius: 6px; border-top-right-radius: 6px; margin-right: 4px; font-weight: bold; font-size: 11px; }
            QTabBar::tab:selected { background: #181C28; color: #00D4FF; border-bottom: 2px solid #00D4FF; }
            QGroupBox { border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 8px; margin-top: 14px; font-weight: bold; color: #00D4FF; padding-top: 16px; }
            QGroupBox::title { subcontrol-origin: margin; left: 14px; padding: 0 4px; }
            QLabel { color: #E0E2EC; font-size: 12px; }
            QSlider::groove:horizontal { height: 6px; background: #252A38; border-radius: 3px; }
            QSlider::sub-page:horizontal { background: #00D4FF; border-radius: 3px; }
            QSlider::handle:horizontal { background: #FFFFFF; width: 16px; margin-top: -5px; margin-bottom: -5px; border-radius: 8px; }
            QComboBox { background: #1E2332; color: #FFFFFF; border: 1px solid rgba(255, 255, 255, 0.15); border-radius: 6px; padding: 6px 12px; font-size: 12px; }
            QSpinBox { background: #1E2332; color: #FFFFFF; border: 1px solid rgba(255, 255, 255, 0.15); border-radius: 6px; padding: 5px 8px; font-size: 12px; }
            QCheckBox { color: #E0E2EC; font-size: 12px; spacing: 8px; }
            QCheckBox::indicator { width: 18px; height: 18px; border-radius: 4px; border: 1px solid rgba(255, 255, 255, 0.25); background: #1C202C; }
            QCheckBox::indicator:checked { background: #00D4FF; }
            QPushButton { background: #202636; color: #FFFFFF; border: 1px solid rgba(255, 255, 255, 0.15); border-radius: 6px; padding: 8px 18px; font-weight: bold; font-size: 12px; }
            QPushButton:hover { background: #2B3348; border-color: #00D4FF; }
            QPushButton#btnSave { background: #0078D7; color: white; border: none; font-size: 13px; }
            QPushButton#btnSave:hover { background: #1084E3; }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        hdr_layout = QHBoxLayout()
        hdr_layout.setSpacing(12)
        if os.path.exists(icon_path):
            lbl_ico = QLabel()
            pix = QPixmap(icon_path).scaled(38, 38, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            lbl_ico.setPixmap(pix)
            hdr_layout.addWidget(lbl_ico)
        v_hdr = QVBoxLayout()
        v_hdr.setSpacing(2)
        header = QLabel("PENGATURAN DYNAMIC ISLAND")
        header.setStyleSheet("font-size: 15px; font-weight: bold; color: #FFFFFF; letter-spacing: 0.5px;")
        sub_header = QLabel("KDE Wayland / X11 Linux Edition")
        sub_header.setStyleSheet("font-size: 11px; color: #8F9BB3;")
        v_hdr.addWidget(header)
        v_hdr.addWidget(sub_header)
        hdr_layout.addLayout(v_hdr)
        hdr_layout.addStretch()
        layout.addLayout(hdr_layout)

        tabs = QTabWidget()
        # Lebar tab mengikuti teksnya penuh (tanpa "…"), bukan dibagi rata;
        # tombol scroll hanya muncul kalau ruang benar-benar habis.
        tabs.tabBar().setExpanding(False)
        tabs.tabBar().setUsesScrollButtons(True)
        tabs.tabBar().setElideMode(Qt.TextElideMode.ElideNone)
        layout.addWidget(tabs)

        # --- TAB 1: TAMPILAN & POSISI ---
        tab_view = QWidget()
        v_box = QVBoxLayout(tab_view)

        grp_pos = QGroupBox("Penataan & Posisi (Position & Drag)")
        p_lay = QVBoxLayout(grp_pos)

        self.btn_lock = QPushButton()
        self.btn_lock.clicked.connect(self.on_toggle_lock)
        p_lay.addWidget(self.btn_lock)

        self.lbl_lock_status = QLabel()
        p_lay.addWidget(self.lbl_lock_status)

        grid_pos = QGridLayout()
        grid_pos.setSpacing(8)
        grid_pos.addWidget(QLabel("Geser Horizontal (X):"), 0, 0)
        self.spin_x = QSpinBox()
        self.spin_x.setRange(-4000, 4000)
        self.spin_x.setSuffix(" px")
        self.spin_x.setValue(int(self.island.cfg.get("offset_x", 0)))
        self.spin_x.valueChanged.connect(self.on_pos_changed)
        grid_pos.addWidget(self.spin_x, 0, 1)
        btn_rx = QPushButton("Reset X")
        btn_rx.clicked.connect(lambda: self.spin_x.setValue(0))
        grid_pos.addWidget(btn_rx, 0, 2)

        grid_pos.addWidget(QLabel("Jarak dari Atas (Y):"), 1, 0)
        self.spin_y = QSpinBox()
        self.spin_y.setRange(0, 2000)
        self.spin_y.setSuffix(" px")
        self.spin_y.setValue(int(self.island.cfg.get("top_margin", 16)))
        self.spin_y.valueChanged.connect(self.on_pos_changed)
        grid_pos.addWidget(self.spin_y, 1, 1)
        btn_ry = QPushButton("Reset Y")
        btn_ry.clicked.connect(lambda: self.spin_y.setValue(16))
        grid_pos.addWidget(btn_ry, 1, 2)

        grid_pos.addWidget(QLabel("Layar Target (Screen):"), 2, 0)
        self.cb_screen = QComboBox()
        screens = QApplication.screens()
        for s in screens:
            self.cb_screen.addItem(s.name())
        cur_screen = getattr(self.island, "target_screen_name", None)
        if cur_screen in [s.name() for s in screens]:
            self.cb_screen.setCurrentText(cur_screen)
        self.cb_screen.currentTextChanged.connect(self.on_screen_changed)
        grid_pos.addWidget(self.cb_screen, 2, 1)
        btn_center = QPushButton("Tengahkan")
        btn_center.clicked.connect(self.on_reset_position)
        grid_pos.addWidget(btn_center, 2, 2)
        # Kolom input diberi ruang lebar penuh, tombol reset cukup 1 baris
        grid_pos.setColumnStretch(1, 1)
        self.spin_x.setMinimumWidth(140)
        self.spin_y.setMinimumWidth(140)
        self.cb_screen.setMinimumWidth(160)
        btn_rx.setMinimumWidth(96)
        btn_ry.setMinimumWidth(96)
        btn_center.setMinimumWidth(104)
        p_lay.addLayout(grid_pos)

        v_box.addWidget(grp_pos)

        grp_scale = QGroupBox("Skala Ukuran (Island Size)")
        sc_lay = QVBoxLayout(grp_scale)
        self.lbl_scale = QLabel(f"Ukuran Saat Ini: {int(self.cfg.get('scale', 1.0) * 100)}%")
        self.slider_scale = QSlider(Qt.Orientation.Horizontal)
        self.slider_scale.setRange(50, 150)
        self.slider_scale.setValue(int(self.cfg.get('scale', 1.0) * 100))
        self.slider_scale.valueChanged.connect(self.on_scale_slide)
        sc_lay.addWidget(self.lbl_scale)
        sc_lay.addWidget(self.slider_scale)
        v_box.addWidget(grp_scale)

        grp_op = QGroupBox("Transparansi Kaca (Glass Opacity)")
        op_lay = QVBoxLayout(grp_op)
        cur_op = int(self.cfg.get("bg_opacity", 98))
        self.lbl_op = QLabel(f"Tingkat Kegelapan: {cur_op}%")
        self.slider_op = QSlider(Qt.Orientation.Horizontal)
        self.slider_op.setRange(40, 100)
        self.slider_op.setValue(cur_op)
        self.slider_op.valueChanged.connect(self.on_opacity_slide)
        op_lay.addWidget(self.lbl_op)
        op_lay.addWidget(self.slider_op)
        v_box.addWidget(grp_op)
        v_box.addStretch()
        tabs.addTab(tab_view, "Tampilan")

        self.update_lock_ui()

        # --- TAB 2: FITUR & PERILAKU ---
        tab_feat = QWidget()
        f_box = QVBoxLayout(tab_feat)

        self.chk_mascot = QCheckBox("Aktifkan Maskot Robot OLED Interaktif (Gaze Tracking)")
        self.chk_mascot.setChecked(self.cfg.get("enable_mascot", True))
        f_box.addWidget(self.chk_mascot)

        self.chk_marquee = QCheckBox("Teks Berjalan Halus (Smooth Marquee untuk judul panjang)")
        self.chk_marquee.setChecked(self.cfg.get("enable_marquee", True))
        f_box.addWidget(self.chk_marquee)

        self.chk_adzan_pause = QCheckBox("Jeda Musik Otomatis saat Waktu Sholat Tiba (Adzan)")
        self.chk_adzan_pause.setChecked(self.cfg.get("pause_music_on_adzan", True))
        f_box.addWidget(self.chk_adzan_pause)

        self.chk_clipboard_bubble = QCheckBox("Notifikasi Bubble saat Menyalin Teks (Clipboard Bubble)")
        self.chk_clipboard_bubble.setChecked(self.cfg.get("enable_clipboard_bubble", True))
        f_box.addWidget(self.chk_clipboard_bubble)

        self.chk_game_mode = QCheckBox("Game Mode (Otomatis Sembunyi saat Game / Video Fullscreen)")
        self.chk_game_mode.setChecked(self.cfg.get("enable_game_mode", True))
        f_box.addWidget(self.chk_game_mode)

        self.chk_battery_alert = QCheckBox("Indikator Daya Baterai & Charger (Laptop)")
        self.chk_battery_alert.setChecked(self.cfg.get("enable_battery_alert", True))
        f_box.addWidget(self.chk_battery_alert)

        self.chk_privacy_dot = QCheckBox("Privacy Dot (Indikator Hijau/Oranye saat Kamera/Mic Aktif)")
        self.chk_privacy_dot.setChecked(self.cfg.get("enable_privacy_dot", True))
        f_box.addWidget(self.chk_privacy_dot)

        self.chk_notif = QCheckBox("Notifikasi Sistem (File History /tmp/macos-notifications-history.json)")
        self.chk_notif.setChecked(self.cfg.get("enable_notifications", True))
        f_box.addWidget(self.chk_notif)

        f_box.addStretch()
        tabs.addTab(tab_feat, "Fitur & Perilaku")

        # --- TAB 3: WAKTU SHOLAT ---
        tab_prayer = QWidget()
        p_box = QVBoxLayout(tab_prayer)
        grp_city = QGroupBox("Lokasi Jadwal Sholat")
        c_lay = QVBoxLayout(grp_city)
        c_lay.addWidget(QLabel("Pilih Kota Anda:"))
        self.cb_city = QComboBox()
        self.cb_city.addItems(list(CITY_COORDINATES.keys()))
        cur_c = self.cfg.get("city", "Jakarta (WIB)")
        if cur_c in CITY_COORDINATES:
            self.cb_city.setCurrentText(cur_c)
        c_lay.addWidget(self.cb_city)
        p_box.addWidget(grp_city)
        p_box.addStretch()
        tabs.addTab(tab_prayer, "Jadwal Sholat")

        # --- TAB 4: SISTEM ---
        tab_sys = QWidget()
        s_box = QVBoxLayout(tab_sys)
        self.chk_autostart = QCheckBox("Jalankan otomatis saat login (~/.config/autostart)")
        self.chk_autostart.setChecked(self.cfg.get("autostart", True))
        s_box.addWidget(self.chk_autostart)
        lbl_desc = QLabel(
            "Dynamic Island dirancang terintegrasi native dengan KDE Plasma (Wayland & X11).\n"
            "Mendukung deteksi media MPRIS, OSD Volume (wpctl), Caps Lock, serta notifikasi sistem."
        )
        lbl_desc.setWordWrap(True)
        lbl_desc.setStyleSheet("color: #8C92A4; margin-top: 10px; line-height: 140%;")
        s_box.addWidget(lbl_desc)
        s_box.addStretch()
        tabs.addTab(tab_sys, "Sistem")

        # --- TAB 5: UJI FITUR & DEMO ---
        tab_test = QWidget()
        t_box = QVBoxLayout(tab_test)
        lbl_test_hint = QLabel("Uji coba langsung animasi & notifikasi Dynamic Island di layar:")
        lbl_test_hint.setStyleSheet("color: #00D4FF; font-weight: bold; margin-bottom: 6px;")
        t_box.addWidget(lbl_test_hint)
        test_grid = QGridLayout()
        test_grid.setSpacing(10)

        btn_t_prayer = QPushButton("🕌 Test Adzan Ashar")
        btn_t_prayer.clicked.connect(lambda: self.island.trigger_prayer_alert("Ashar"))
        test_grid.addWidget(btn_t_prayer, 0, 0)

        btn_t_charger = QPushButton("⚡ Test Charger (85%)")
        btn_t_charger.clicked.connect(lambda: self.island.trigger_battery_alert(85, True))
        test_grid.addWidget(btn_t_charger, 0, 1)

        btn_t_lowbat = QPushButton("🪫 Test Baterai Lemah (15%)")
        btn_t_lowbat.clicked.connect(lambda: self.island.trigger_battery_alert(15, False))
        test_grid.addWidget(btn_t_lowbat, 1, 0)

        btn_t_privacy = QPushButton("🟢 Test Privacy Dot (Cam/Mic)")
        btn_t_privacy.clicked.connect(self.island.toggle_privacy_demo)
        test_grid.addWidget(btn_t_privacy, 1, 1)

        btn_t_clip = QPushButton("📋 Test Clipboard Bubble")
        btn_t_clip.clicked.connect(lambda: self.island.trigger_clipboard_bubble("https://github.com/rezariski"))
        test_grid.addWidget(btn_t_clip, 2, 0)

        btn_t_vol = QPushButton("🔊 Test Volume Overboost")
        btn_t_vol.clicked.connect(lambda: self.island.trigger_volume_osd(125, False))
        test_grid.addWidget(btn_t_vol, 2, 1)

        btn_t_media = QPushButton("🎵 Test Media Player")
        btn_t_media.clicked.connect(self.run_test_media)
        test_grid.addWidget(btn_t_media, 3, 0)

        btn_t_caps = QPushButton("🔤 Test Caps Lock OSD")
        btn_t_caps.clicked.connect(lambda: self.island.trigger_caps_osd(True))
        test_grid.addWidget(btn_t_caps, 3, 1)

        btn_t_notif = QPushButton("💬 Test Notifikasi Chat")
        btn_t_notif.clicked.connect(lambda: self.island.trigger_notification("WhatsApp", "Budi Santoso", "Halo! Notifikasi berhasil terbaca di Dynamic Island."))
        test_grid.addWidget(btn_t_notif, 4, 0)

        btn_t_email = QPushButton("📩 Test Notifikasi Email")
        btn_t_email.clicked.connect(lambda: self.island.trigger_notification("Outlook", "Reza Riski", "Update commit ixsland Linux siap direview."))
        test_grid.addWidget(btn_t_email, 4, 1)

        btn_t_update = QPushButton("🚀 Test Notif Update Baru")
        btn_t_update.clicked.connect(self.island.trigger_update_demo)
        test_grid.addWidget(btn_t_update, 5, 0)

        btn_t_chk = QPushButton("🔍 Cek Update GitHub Asli")
        btn_t_chk.clicked.connect(self.on_check_update_clicked)
        test_grid.addWidget(btn_t_chk, 5, 1)

        t_box.addLayout(test_grid)
        btn_t_reset = QPushButton("↩ Kembalikan ke Normal (IDLE)")
        btn_t_reset.setStyleSheet("background-color: #2D3139; color: #FFFFFF; font-weight: bold; padding: 7px;")
        btn_t_reset.clicked.connect(self.island.collapse_to_base_mode)
        t_box.addWidget(btn_t_reset)
        t_box.addStretch()
        tabs.addTab(tab_test, "Uji Fitur")

        # --- TAB 6: TENTANG AUTHOR ---
        tab_about = QWidget()
        a_box = QVBoxLayout(tab_about)
        head_lay = QHBoxLayout()
        logo_lbl = QLabel()
        logo_path = os.path.join(ASSETS_DIR, "icon.png")
        if os.path.exists(logo_path):
            pix = QPixmap(logo_path).scaled(58, 58, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            logo_lbl.setPixmap(pix)
        else:
            logo_lbl.setText("🏝️")
            logo_lbl.setStyleSheet("font-size: 38px;")
        head_lay.addWidget(logo_lbl)
        title_lay = QVBoxLayout()
        lbl_app_name = QLabel("ixsland Dynamic Island")
        lbl_app_name.setStyleSheet("font-size: 14pt; font-weight: bold; color: #FFFFFF;")
        lbl_app_ver = QLabel(f"Version {APP_VERSION} (Linux Native Edition)")
        lbl_app_ver.setStyleSheet("font-size: 9pt; color: #00D4FF;")
        title_lay.addWidget(lbl_app_name)
        title_lay.addWidget(lbl_app_ver)
        head_lay.addLayout(title_lay)
        head_lay.addStretch()
        a_box.addLayout(head_lay)

        grp_update = QGroupBox("Pembaruan Perangkat Lunak (Updates)")
        up_lay = QVBoxLayout(grp_update)
        up_info_lay = QHBoxLayout()
        self.lbl_update_status = QLabel(f"Versi Terpasang: v{APP_VERSION} (Terbaru)")
        self.lbl_update_status.setStyleSheet("color: #00E676; font-size: 9pt;")
        up_info_lay.addWidget(self.lbl_update_status)
        up_info_lay.addStretch()
        self.btn_check_update = QPushButton("🔄 Periksa Pembaruan")
        self.btn_check_update.setStyleSheet("background-color: #1F232B; border: 1px solid #383F4D; padding: 5px 12px;")
        self.btn_check_update.clicked.connect(self.on_check_update_clicked)
        up_info_lay.addWidget(self.btn_check_update)
        up_lay.addLayout(up_info_lay)
        self.chk_auto_update = QCheckBox("Periksa pembaruan secara otomatis saat aplikasi dibuka")
        self.chk_auto_update.setChecked(self.cfg.get("check_updates", True))
        up_lay.addWidget(self.chk_auto_update)
        a_box.addWidget(grp_update)

        grp_author = QGroupBox("Profil Pembuat")
        auth_lay = QVBoxLayout(grp_author)
        lbl_name = QLabel("Pembuat: Reza Riski (@rezariski)")
        lbl_name.setStyleSheet("font-size: 10pt; font-weight: bold; color: #FFFFFF;")
        auth_lay.addWidget(lbl_name)
        lbl_role = QLabel("Peran: Creator & Lead Developer")
        lbl_role.setStyleSheet("color: #00E676; font-size: 9pt;")
        auth_lay.addWidget(lbl_role)
        lbl_bio = QLabel(
            "Software developer & system architect, fokus pada utilitas desktop interaktif, "
            "integrasi antarmuka modern, dan otomasi sistem untuk Windows dan Linux."
        )
        lbl_bio.setWordWrap(True)
        lbl_bio.setStyleSheet("color: #B0B8C8; margin-top: 6px; line-height: 140%;")
        auth_lay.addWidget(lbl_bio)
        link_box = QHBoxLayout()
        btn_github = QPushButton("🌐 Profil GitHub")
        btn_github.setStyleSheet("background-color: #1F232B; border: 1px solid #383F4D; padding: 6px 10px;")
        btn_github.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://github.com/rezariski")))
        link_box.addWidget(btn_github)
        btn_repo = QPushButton("📦 Repositori ixsland")
        btn_repo.setStyleSheet("background-color: #1F232B; border: 1px solid #383F4D; padding: 6px 10px;")
        btn_repo.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://github.com/rezariski/ixsland")))
        link_box.addWidget(btn_repo)
        auth_lay.addLayout(link_box)
        a_box.addWidget(grp_author)
        lbl_copy = QLabel("Copyright © 2026 Reza Riski. Hak cipta dilindungi undang-undang.")
        lbl_copy.setStyleSheet("color: #6C7280; font-size: 8pt; margin-top: 6px;")
        a_box.addWidget(lbl_copy)
        a_box.addStretch()
        tabs.addTab(tab_about, "Tentang")

        btn_box = QHBoxLayout()
        btn_box.addStretch()
        btn_cancel = QPushButton("Batal")
        btn_cancel.clicked.connect(self.reject)
        btn_box.addWidget(btn_cancel)
        btn_save = QPushButton("Simpan Pengaturan")
        btn_save.setObjectName("btnSave")
        btn_save.clicked.connect(self.save_and_apply)
        btn_box.addWidget(btn_save)
        layout.addLayout(btn_box)

        # Tinggi jendela mengikuti kebutuhan konten tab terbesar supaya
        # tidak ada tab yang terkompresi (tombol/combo jadi pendek, teks terpotong).
        self.layout().activate()
        best = self.sizeHint()
        for i in range(tabs.count()):
            tabs.setCurrentIndex(i)
            self.layout().activate()
            best = best.expandedTo(self.sizeHint())
        tabs.setCurrentIndex(0)
        self.layout().activate()
        self.resize(max(760, best.width()), max(570, best.height()))
        self.setMinimumSize(max(700, best.width()), max(520, best.height()))

    # --- POSITION / LOCK HANDLERS ---
    def update_lock_ui(self):
        locked = bool(self.island.cfg.get("pos_locked", False))
        if locked:
            self.btn_lock.setText("🔒 Posisi Terkunci — Klik untuk Buka Kunci Drag")
            self.btn_lock.setStyleSheet("background-color: #3A2A12; border: 1px solid #FFB300; color: #FFD166; padding: 9px;")
            self.lbl_lock_status.setText("Posisi terkunci rapat. Geser manual dinonaktifkan.")
            self.lbl_lock_status.setStyleSheet("color: #FFB300; font-size: 11px; font-weight: bold;")
        else:
            self.btn_lock.setText("🔓 Posisi Terbuka — Klik untuk Kunci (Drag Aktif)")
            self.btn_lock.setStyleSheet("background-color: #123A1E; border: 1px solid #00E676; color: #7CFFB2; padding: 9px;")
            self.lbl_lock_status.setText("Posisi terbuka: tarik langsung di layar atau masukkan koordinat X/Y.")
            self.lbl_lock_status.setStyleSheet("color: #00E676; font-size: 11px; font-weight: bold;")

    def on_toggle_lock(self):
        locked = not bool(self.island.cfg.get("pos_locked", False))
        self.island.set_pos_locked(locked)
        self.update_lock_ui()

    def on_pos_changed(self):
        if self._suppress_pos:
            return
        self.island.set_position_offset(offset_x=self.spin_x.value(), top_margin=self.spin_y.value())

    def on_reset_position(self):
        self._suppress_pos = True
        self.spin_x.setValue(0)
        self.spin_y.setValue(16)
        self._suppress_pos = False
        self.island.set_position_offset(offset_x=0, top_margin=16)

    def on_screen_changed(self, name):
        if name:
            self.island.set_target_screen(name)

    def sync_position_inputs(self, offset_x, top_margin):
        self._suppress_pos = True
        self.spin_x.setValue(int(offset_x))
        self.spin_y.setValue(int(top_margin))
        self._suppress_pos = False

    def on_scale_slide(self, v):
        self.lbl_scale.setText(f"Ukuran Saat Ini: {v}%")
        self.island.scale = v / 100.0
        self.island.cfg["scale"] = v / 100.0
        self.island.init_placement()
        self.island.update_mask_for_mode()
        self.island.update()

    def on_opacity_slide(self, v):
        self.lbl_op.setText(f"Tingkat Kegelapan: {v}%")
        self.island.cfg["bg_opacity"] = v
        self.island.update()

    def closeEvent(self, event):
        self.island.settings_dialog = None
        super().closeEvent(event)

    def reject(self):
        self.island.cfg["bg_opacity"] = self.orig_bg_opacity
        self.island.cfg["scale"] = self.orig_scale
        self.island.cfg["offset_x"] = self.orig_offset_x
        self.island.cfg["top_margin"] = self.orig_top_margin
        self.island.scale = self.orig_scale
        self.island.set_pos_locked(self.orig_pos_locked)
        self.island.init_placement()
        self.island.update_mask_for_mode()
        self.island.update()
        self.island.settings_dialog = None
        super().reject()

    def on_check_update_clicked(self):
        self.lbl_update_status.setText("Sedang memeriksa rilis GitHub...")
        self.lbl_update_status.setStyleSheet("color: #00D4FF; font-size: 9pt;")
        self.btn_check_update.setEnabled(False)
        self.island.check_for_updates(callback=self.on_update_result)

    def on_update_result(self, has_update, tag, url, body):
        self.btn_check_update.setEnabled(True)
        if has_update:
            self.lbl_update_status.setText(f"🚀 Versi {tag} tersedia!")
            self.lbl_update_status.setStyleSheet("color: #FFB300; font-weight: bold; font-size: 9pt;")
            self.btn_check_update.setText("🌐 Unduh Versi Baru")
            try:
                self.btn_check_update.clicked.disconnect()
            except Exception:
                pass
            self.btn_check_update.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(url)))
        else:
            if url:
                self.lbl_update_status.setText(f"✓ Anda sudah menggunakan versi terbaru (v{APP_VERSION})")
                self.lbl_update_status.setStyleSheet("color: #00E676; font-size: 9pt;")
            else:
                self.lbl_update_status.setText("Gagal memeriksa pembaruan (offline / rate limit).")
                self.lbl_update_status.setStyleSheet("color: #FF5252; font-size: 9pt;")

    def run_test_media(self):
        self.island.media_ctrl.set_mock_track("Starboy", "The Weeknd ft. Daft Punk", None, 230)
        self.island.mode = "EXPANDED_MEDIA"
        self.island.expanded_at = time.time()
        self.island.update_mode_targets()
        self.island.auto_collapse_timer.start(12000)

    def save_and_apply(self):
        self.cfg["scale"] = self.slider_scale.value() / 100.0
        self.cfg["bg_opacity"] = self.slider_op.value()
        self.cfg["offset_x"] = self.spin_x.value()
        self.cfg["top_margin"] = self.spin_y.value()
        # Preserve live-toggled values not backed by a dialog widget
        self.cfg["pos_locked"] = bool(self.island.cfg.get("pos_locked", False))
        self.cfg["target_screen"] = self.island.cfg.get("target_screen", self.cfg.get("target_screen", "primary"))
        self.cfg["enable_mascot"] = self.chk_mascot.isChecked()
        self.cfg["enable_marquee"] = self.chk_marquee.isChecked()
        self.cfg["pause_music_on_adzan"] = self.chk_adzan_pause.isChecked()
        self.cfg["enable_clipboard_bubble"] = self.chk_clipboard_bubble.isChecked()
        self.cfg["enable_game_mode"] = self.chk_game_mode.isChecked()
        self.cfg["enable_battery_alert"] = self.chk_battery_alert.isChecked()
        self.cfg["enable_privacy_dot"] = self.chk_privacy_dot.isChecked()
        self.cfg["enable_notifications"] = self.chk_notif.isChecked()
        self.cfg["check_updates"] = self.chk_auto_update.isChecked()
        self.cfg["autostart"] = self.chk_autostart.isChecked()

        city_name = self.cb_city.currentText()
        if city_name in CITY_COORDINATES:
            lat, lng, tz = CITY_COORDINATES[city_name]
            self.cfg["city"] = city_name
            self.cfg["latitude"] = lat
            self.cfg["longitude"] = lng
            self.cfg["timezone"] = tz

        save_config(self.cfg)
        self.island.apply_config(self.cfg)
        self.island.settings_dialog = None
        self.close()


# --- MAIN DYNAMIC ISLAND WIDGET ---
class IxslandWidget(QWidget):
    def __init__(self, target_screen_name="DP-1", title_suffix="Screen 2", shared_media=None, is_primary_instance=True):
        super().__init__()
        self.target_screen_name = target_screen_name
        self.title_suffix = title_suffix
        self.is_primary_instance = is_primary_instance
        self.secondary_island = None
        self.cfg = load_config()
        self.scale = float(self.cfg.get("scale", 1.0))
        self.is_minimized = False
        self.is_hovered = False
        self.hidden_trigger = None
        self.settings_dialog = None
        # Manual position drag state
        self._drag_pending = False
        self._dragging = False
        self._drag_start_gpos = None
        self._drag_start_geom = None
        self.mode = "IDLE"
        self.prev_mode = "IDLE"
        
        # Dimensions inside canvas
        self.curr_pill_w = 200
        self.curr_pill_h = 36
        self.target_pill_w = 200
        self.target_pill_h = 36
        
        # PERMANENT ANCHOR: Top margin inside fixed canvas is always 6
        self.pill_y = 6
        
        # Subsystems
        if shared_media:
            self.media_ctrl = shared_media
        else:
            self.media_ctrl = MediaController()
        self.media_ctrl.mediaChanged.connect(self.on_media_changed)
        self.media_info = self.media_ctrl.current_info
        
        self.vol_percent, self.vol_muted = get_volume()
        self.display_vol = float(self.vol_percent)
        self.last_known_vol = self.vol_percent
        self.last_known_mute = self.vol_muted
        self.vol_anim = None
        
        self.caps_lock_state = get_caps_lock_state()
        self.last_caps_state = self.caps_lock_state
        
        self.prayer_times = calculate_prayer_times(
            self.cfg["latitude"], self.cfg["longitude"], self.cfg["timezone"]
        )
        self.last_announced_prayer = None
        
        # Cursor & Robot Mascot State
        self.cursor_x = 2460
        self.cursor_y = 500
        self.curr_gaze_x = 0.0
        self.curr_gaze_y = 0.0
        self.last_cursor_move_time = time.time()
        
        # D-Bus IPC & KWin Integration
        if self.is_primary_instance:
            self.bus = QtDBus.QDBusConnection.sessionBus()
            self.bus.registerService("org.ixsland.Island")
            self.bus.registerObject("/Island", self, QtDBus.QDBusConnection.RegisterOption.ExportAllSlots)
            self.cursor_tracker = KWinCursorTracker()
        else:
            self.bus = None
            self.cursor_tracker = None
        
        # Notification System
        self.last_notif_id = None
        self.active_notif = {"app": "", "summary": "", "body": ""}
        
        # Animation & Timers
        self.anim = None
        self.eq_bars = [4, 8, 12, 6]
        
        self.eq_timer = QTimer(self)
        self.eq_timer.timeout.connect(self.animate_eq)
        self.eq_timer.start(120)
        
        self.clock_timer = QTimer(self)
        self.clock_timer.timeout.connect(self.on_tick_1s)
        self.clock_timer.start(1000)
        self.idle_view_counter = 0
        
        # Smooth Mascot Gaze & Blinking Engine (25 FPS)
        self.mascot_timer = QTimer(self)
        self.mascot_timer.timeout.connect(self.on_mascot_tick)
        self.mascot_timer.start(40)
        
        # Hardware Poller (Caps Lock, Volume keys, Notifications)
        self.hw_timer = QTimer(self)
        self.hw_timer.timeout.connect(self.poll_hardware_state)
        self.hw_timer.start(120)
        
        # Transient OSD / Notif Revert Timer
        self.revert_timer = QTimer(self)
        self.revert_timer.setSingleShot(True)
        self.revert_timer.timeout.connect(self.revert_transient_mode)
        
        # Auto-Collapse on Mouse Leave (Expanded Area)
        self.expanded_at = 0.0
        self.auto_collapse_timer = QTimer(self)
        self.auto_collapse_timer.setSingleShot(True)
        self.auto_collapse_timer.timeout.connect(self.check_and_collapse_expanded)

        # Battery Indicator Setup
        self.has_battery, self.battery_pct, self.battery_charging = get_system_battery()
        self.last_battery_charging = self.battery_charging
        self.last_battery_pct = self.battery_pct

        # Privacy Dot Setup (Green = Cam, Orange = Mic)
        self.privacy_cam_active = False
        self.privacy_mic_active = False
        self.privacy_demo_active = False

        # Clipboard Bubble Setup
        self.last_clipboard_text = ""
        self.clipboard_snippet = ""

        # Fullscreen / Game Mode Setup
        self.is_hidden_by_fullscreen = False
        self.active_win_geom = None

        # Marquee & Updates
        self.marquee_offset = 0.0
        self.latest_update_info = None
        self.update_checker = None
        self.tray_icon = None

        if self.is_primary_instance:
            self.battery_timer = QTimer(self)
            self.battery_timer.timeout.connect(self.check_battery_status)
            self.battery_timer.start(3500)

            self.privacy_timer = QTimer(self)
            self.privacy_timer.timeout.connect(self.check_privacy_dots)
            self.privacy_timer.start(2000)

            app_inst = QApplication.instance()
            if app_inst and app_inst.clipboard():
                app_inst.clipboard().dataChanged.connect(self.on_clipboard_data_changed)

            # Wayland: window kita tak pernah dapat fokus keyboard, jadi QClipboard
            # tidak pernah menerima event salinan dari aplikasi lain. Klipper
            # (riwayat clipboard KDE) memantaunya dan mengekspos teks via D-Bus.
            self.setup_klipper_clipboard_monitor()

            self.fullscreen_timer = QTimer(self)
            self.fullscreen_timer.timeout.connect(self.check_fullscreen_window)
            self.fullscreen_timer.start(1500)

            sync_autostart_registration(self.cfg.get("autostart", True))

            if self.cfg.get("check_updates", True):
                QTimer.singleShot(8000, self.check_for_updates)

        # Window Flags & Fixed Size
        obj_name = f"ixsland_{self.title_suffix.lower().replace(' ', '')}"
        self.setObjectName(obj_name)
        # Caption carries the requested geometry. A KWin script (injected by KWinCursorTracker)
        # parses it and pins the Wayland toplevel, since KWin ignores client setGeometry.
        self.setWindowTitle(f"IXSLAND:0,0,{int(round(CANVAS_W * self.scale))},{int(round(CANVAS_H * self.scale))}")
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool |
            Qt.WindowType.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setMouseTracking(True)
        
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(16)
        shadow.setColor(QColor(0, 0, 0, 160))
        shadow.setOffset(0, 2)
        self.setGraphicsEffect(shadow)
        
        if self.is_primary_instance:
            self.setup_system_tray()

        self.init_placement()
        self.update_mask_for_mode()
        self.show()
        self.raise_()

    def get_target_screen(self):
        screens = QApplication.screens()
        target = self.target_screen_name or self.cfg.get("target_screen", "primary")
        if target and target.lower() not in ("primary", "main", "default"):
            for s in screens:
                if s.name() == target:
                    return s
        primary = QApplication.primaryScreen()
        return primary if primary else (screens[0] if screens else None)

    def context_center_x(self, geom, scale=None):
        scale = scale if scale is not None else getattr(self, "scale", 1.0)
        canvas_w = int(round(CANVAS_W * scale))
        return geom.x() + (geom.width() - canvas_w) // 2

    def init_placement(self):
        s = self.get_target_screen()
        geom = s.geometry() if s else QRect(0, 0, 1920, 1080)
        
        self.winId()
        if self.windowHandle() and s:
            self.windowHandle().setScreen(s)

        scale = getattr(self, "scale", 1.0)
        canvas_w = int(round(CANVAS_W * scale))
        canvas_h = int(round(CANVAS_H * scale))
        offset_x = int(self.cfg.get("offset_x", 0))
        top_margin = int(round(self.cfg.get("top_margin", 16) * scale))

        canvas_x = self.context_center_x(geom, scale) + offset_x
        canvas_y = geom.y() + top_margin

        # FIXED CANVAS SIZE: Never resize window to keep KWin Wayland position permanent
        self.setGeometry(canvas_x, canvas_y, canvas_w, canvas_h)
        self.setFixedSize(canvas_w, canvas_h)
        self._push_kwin_position(canvas_x, canvas_y, canvas_w, canvas_h)

    def _push_kwin_position(self, x, y, w, h):
        """Publish target geometry through the window caption for the KWin pin script."""
        try:
            self.setWindowTitle(f"IXSLAND:{int(x)},{int(y)},{int(w)},{int(h)}")
            self.raise_()
        except Exception:
            pass

    def set_target_screen(self, name):
        if not name:
            return
        self.target_screen_name = name
        self.cfg["target_screen"] = name
        save_config(self.cfg)
        self.init_placement()
        self.update_mask_for_mode()
        self.update()

    def set_pos_locked(self, locked):
        locked = bool(locked)
        self.cfg["pos_locked"] = locked
        save_config(self.cfg)
        if self.secondary_island:
            self.secondary_island.cfg["pos_locked"] = locked
        self.update()
        if self.settings_dialog:
            for island in (self, self.secondary_island):
                if island and island.settings_dialog:
                    try:
                        island.settings_dialog.update_lock_ui()
                    except Exception:
                        pass

    def set_position_offset(self, offset_x=None, top_margin=None):
        if offset_x is not None:
            self.cfg["offset_x"] = int(offset_x)
            if self.secondary_island:
                self.secondary_island.cfg["offset_x"] = int(offset_x)
        if top_margin is not None:
            self.cfg["top_margin"] = int(top_margin)
            if self.secondary_island:
                self.secondary_island.cfg["top_margin"] = int(top_margin)
        save_config(self.cfg)
        self.init_placement()
        if self.secondary_island:
            self.secondary_island.init_placement()
        self.update()

    def reset_position(self):
        self.set_position_offset(offset_x=0, top_margin=16)
        if self.settings_dialog:
            try:
                self.settings_dialog.sync_position_inputs(0, 16)
            except Exception:
                pass

    def update_mask_for_mode(self):
        # FIX FOR HORIZONTAL CLIPPING:
        # Full horizontal width (rx=0, rw=CANVAS_W) ensures pill is NEVER clipped horizontally!
        scale = getattr(self, "scale", 1.0)
        if self.mode == "EXPANDED_MEDIA":
            self.clearMask()
        else:
            # Allows clicks below y=54 to pass straight through while protecting full pill width
            self.setMask(QRegion(QRect(0, 0, int(round(CANVAS_W * scale)), int(round(54 * scale)))))

    def update_mode_targets(self):
        if self.mode == "IDLE":
            self.target_pill_w, self.target_pill_h = 200, 36
        elif self.mode == "COMPACT_MEDIA":
            self.target_pill_w, self.target_pill_h = 340, 40
        elif self.mode == "OSD_VOLUME":
            self.target_pill_w, self.target_pill_h = 260, 38
        elif self.mode == "CAPS_OSD":
            self.target_pill_w, self.target_pill_h = 230, 38
        elif self.mode == "NOTIFICATION":
            self.target_pill_w, self.target_pill_h = 360, 56
        elif self.mode == "PRAYER_ALERT":
            self.target_pill_w, self.target_pill_h = 360, 52
        elif self.mode == "BATTERY_ALERT":
            self.target_pill_w, self.target_pill_h = 250, 48
        elif self.mode == "CLIPBOARD_BUBBLE":
            self.target_pill_w, self.target_pill_h = 260, 44
        elif self.mode == "EXPANDED_MEDIA":
            self.target_pill_w, self.target_pill_h = 380, 156

        self.start_morph_animation()

    def start_morph_animation(self):
        if self.anim and self.anim.state() == QVariantAnimation.State.Running:
            self.anim.stop()

        start_w, start_h = self.curr_pill_w, self.curr_pill_h
        end_w, end_h = self.target_pill_w, self.target_pill_h

        # Clear mask during animation to eliminate any clip artifacts
        self.clearMask()

        self.anim = QVariantAnimation(self)
        self.anim.setDuration(220)
        self.anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.anim.setStartValue(0.0)
        self.anim.setEndValue(1.0)

        def step(progress):
            self.curr_pill_w = int(round(start_w + (end_w - start_w) * progress))
            self.curr_pill_h = int(round(start_h + (end_h - start_h) * progress))
            self.update()

        def on_finished():
            self.curr_pill_w = end_w
            self.curr_pill_h = end_h
            self.update_mask_for_mode()
            self.update()

        self.anim.valueChanged.connect(step)
        self.anim.finished.connect(on_finished)
        self.anim.start()

    def is_cursor_inside_expanded(self):
        if self.mode != "EXPANDED_MEDIA":
            return False
        cw = self.geometry().x()
        cy = self.geometry().y()
        pill_w = self.target_pill_w
        pill_h = self.target_pill_h
        pill_x = cw + (CANVAS_W - pill_w) // 2
        pill_y = cy + int(self.pill_y)
        rect = QRect(pill_x - 8, pill_y - 8, pill_w + 16, pill_h + 16)
        return rect.contains(self.cursor_x, self.cursor_y)

    def check_and_collapse_expanded(self):
        if self.mode == "EXPANDED_MEDIA":
            if not self.is_cursor_inside_expanded():
                self.collapse_to_base_mode()

    def collapse_to_base_mode(self):
        if self.auto_collapse_timer.isActive():
            self.auto_collapse_timer.stop()
        if self.media_info.get("status") == "Playing":
            self.mode = "COMPACT_MEDIA"
        else:
            self.mode = "IDLE"
        self.update_mode_targets()

    @pyqtSlot(int, int)
    def setCursor(self, x, y):
        self.on_global_cursor_moved(x, y)
        if self.secondary_island:
            self.secondary_island.on_global_cursor_moved(x, y)

    @pyqtSlot(str)
    def triggerPrayer(self, name):
        self.trigger_prayer_alert(name)
        if self.secondary_island:
            self.secondary_island.trigger_prayer_alert(name)

    @pyqtSlot(str, str, str)
    def triggerNotification(self, app, summary, body):
        self.trigger_notification(app, summary, body)
        if self.secondary_island:
            self.secondary_island.trigger_notification(app, summary, body)

    @pyqtSlot(int, bool)
    def triggerVolume(self, percent, muted):
        self.trigger_volume_osd(percent, muted)
        if self.secondary_island:
            self.secondary_island.trigger_volume_osd(percent, muted)

    @pyqtSlot(bool)
    def triggerCaps(self, on):
        self.caps_lock_state = on
        self.last_caps_state = on
        self.trigger_caps_osd(on)
        if self.secondary_island:
            self.secondary_island.caps_lock_state = on
            self.secondary_island.last_caps_state = on
            self.secondary_island.trigger_caps_osd(on)

    @pyqtSlot()
    def triggerExpand(self):
        self.mode = "EXPANDED_MEDIA"
        self.expanded_at = time.time()
        self.update_mode_targets()
        if self.secondary_island:
            self.secondary_island.mode = "EXPANDED_MEDIA"
            self.secondary_island.expanded_at = time.time()
            self.secondary_island.update_mode_targets()

    @pyqtSlot()
    def triggerCollapse(self):
        self.collapse_to_base_mode()
        if self.secondary_island:
            self.secondary_island.collapse_to_base_mode()

    @pyqtSlot(int)
    def triggerIdlePhase(self, phase):
        self.mode = "IDLE"
        self.idle_view_counter = phase * 5
        self.update_mode_targets()
        self.update()
        if self.secondary_island:
            self.secondary_island.mode = "IDLE"
            self.secondary_island.idle_view_counter = phase * 5
            self.secondary_island.update_mode_targets()
            self.secondary_island.update()

    @pyqtSlot(bool)
    def triggerMascotSleep(self, sleep):
        if sleep:
            self.last_cursor_move_time = time.time() - 30.0
        else:
            self.last_cursor_move_time = time.time()
        self.update()
        if self.secondary_island:
            if sleep:
                self.secondary_island.last_cursor_move_time = time.time() - 30.0
            else:
                self.secondary_island.last_cursor_move_time = time.time()
            self.secondary_island.update()

    @pyqtSlot(int, int, int, int)
    def setActiveWindowGeom(self, x, y, w, h):
        self.active_win_geom = (int(x), int(y), int(w), int(h))

    @pyqtSlot()
    def kwinScriptReady(self):
        """Dipanggil script KWin saat sudah hidup (pin + pelacak kursor)."""
        tracker = getattr(self, "cursor_tracker", None)
        if tracker is None or tracker.ready:
            return
        tracker.mark_ready()
        print("[ixsland] script KWin aktif (pin posisi + pelacak kursor)", flush=True)
        try:
            # Pin ulang posisi sekarang, siapa tahu KWin sempat menaruh bebas
            self.init_placement()
        except Exception:
            pass

    @pyqtSlot(result=str)
    def debugGeometry(self):
        s = self.get_target_screen()
        g = self.geometry()
        out = (f"target={self.target_screen_name} screen={s.name() if s else None} "
               f"screenGeom={s.geometry().x()},{s.geometry().y()},{s.geometry().width()},{s.geometry().height() if s else 0} "
               f"win={g.x()},{g.y()},{g.width()},{g.height()} scale={self.scale} "
               f"offset={self.cfg.get('offset_x')},{self.cfg.get('top_margin')} locked={self.cfg.get('pos_locked')} "
               f"title={self.windowTitle()} "
               f"activeWin={getattr(self,'active_win_geom',None)} hiddenByFS={getattr(self,'is_hidden_by_fullscreen',False)} visible={self.isVisible()} "
               f"mode={self.mode}")
        if self.secondary_island:
            sec = self.secondary_island
            sg = sec.geometry()
            ss = sec.get_target_screen()
            out += f" || SECONDARY target={sec.target_screen_name} screen={ss.name() if ss else None} win={sg.x()},{sg.y()},{sg.width()},{sg.height()}"
        return out

    @pyqtSlot(int, bool)
    def triggerBattery(self, pct, charging):
        self.trigger_battery_alert(pct, charging)
        if self.secondary_island:
            self.secondary_island.trigger_battery_alert(pct, charging)

    @pyqtSlot(str)
    def triggerClipboard(self, text):
        self.trigger_clipboard_bubble(text)
        if self.secondary_island:
            self.secondary_island.trigger_clipboard_bubble(text)

    @pyqtSlot()
    def togglePrivacy(self):
        self.toggle_privacy_demo()
        if self.secondary_island:
            self.secondary_island.privacy_cam_active = self.privacy_cam_active
            self.secondary_island.privacy_mic_active = self.privacy_mic_active
            self.secondary_island.update()

    @pyqtSlot()
    def checkUpdate(self):
        self.check_for_updates()

    @pyqtSlot()
    def triggerUpdateDemo(self):
        self.trigger_update_demo()

    @pyqtSlot(bool)
    def setPosLocked(self, locked):
        self.set_pos_locked(locked)

    @pyqtSlot(int, int)
    def setPositionOffset(self, offset_x, top_margin):
        self.set_position_offset(offset_x=offset_x, top_margin=top_margin)

    @pyqtSlot(float)
    def setScale(self, sc):
        self.scale = float(sc)
        self.cfg["scale"] = float(sc)
        if self.secondary_island:
            self.secondary_island.scale = float(sc)
            self.secondary_island.cfg["scale"] = float(sc)
        self.init_placement()
        self.update_mask_for_mode()
        self.update()

    def on_global_cursor_moved(self, x, y):
        if abs(self.cursor_x - x) > 2 or abs(self.cursor_y - y) > 2:
            self.cursor_x = x
            self.cursor_y = y
            self.last_cursor_move_time = time.time()
            
            # Auto-collapse expanded island when mouse leaves area
            if self.mode == "EXPANDED_MEDIA" and (time.time() - self.expanded_at > 0.3):
                if not self.is_cursor_inside_expanded():
                    if not self.auto_collapse_timer.isActive():
                        self.auto_collapse_timer.start(120)
                else:
                    if self.auto_collapse_timer.isActive():
                        self.auto_collapse_timer.stop()

    def mouseMoveEvent(self, event):
        gpos = event.globalPosition()
        self.on_global_cursor_moved(int(gpos.x()), int(gpos.y()))
        
        # Local widget check for fast response inside canvas
        if self.mode == "EXPANDED_MEDIA" and (time.time() - self.expanded_at > 0.3):
            pill_x = (CANVAS_W - self.target_pill_w) // 2
            pill_y = int(self.pill_y)
            rect = QRect(pill_x - 8, pill_y - 8, self.target_pill_w + 16, self.target_pill_h + 16)
            if not rect.contains(event.position().toPoint()):
                if not self.auto_collapse_timer.isActive():
                    self.auto_collapse_timer.start(120)
            else:
                if self.auto_collapse_timer.isActive():
                    self.auto_collapse_timer.stop()
        super().mouseMoveEvent(event)

    def leaveEvent(self, event):
        if self.mode == "EXPANDED_MEDIA" and (time.time() - self.expanded_at > 0.3):
            if not self.auto_collapse_timer.isActive():
                self.auto_collapse_timer.start(100)
        super().leaveEvent(event)

    def enterEvent(self, event):
        self.raise_()
        if self.mode == "EXPANDED_MEDIA":
            if self.auto_collapse_timer.isActive():
                self.auto_collapse_timer.stop()
        super().enterEvent(event)

    def on_mascot_tick(self):
        scale = getattr(self, "scale", 1.0)
        # Marquee running text advance
        if self.mode in ("COMPACT_MEDIA", "EXPANDED_MEDIA") and self.cfg.get("enable_marquee", True):
            self.marquee_offset += 1.2
            self.update()
        if self.mode == "IDLE":
            if not self.cfg.get("enable_mascot", True):
                return
            phase = (self.idle_view_counter // 5) % 3
            if phase == 2:
                # Calculate gaze towards cursor (scale-aware)
                canvas_w = CANVAS_W * scale
                island_cx = self.geometry().x() + (canvas_w / 2.0)
                island_cy = self.geometry().y() + ((self.pill_y + (self.curr_pill_h / 2.0)) * scale)
                
                dx = self.cursor_x - island_cx
                dy = self.cursor_y - island_cy
                
                target_gx = math.tanh(dx / 350.0)
                target_gy = math.tanh(dy / 400.0)
                
                # Smooth interpolation (Pixar-like gaze follow)
                self.curr_gaze_x += (target_gx - self.curr_gaze_x) * 0.28
                self.curr_gaze_y += (target_gy - self.curr_gaze_y) * 0.28
                self.update()

    def on_media_changed(self, info):
        self.media_info = info
        if self.mode not in ("OSD_VOLUME", "CAPS_OSD", "NOTIFICATION", "PRAYER_ALERT", "EXPANDED_MEDIA", "BATTERY_ALERT", "CLIPBOARD_BUBBLE"):
            if info["status"] == "Playing":
                if self.mode != "COMPACT_MEDIA":
                    self.mode = "COMPACT_MEDIA"
                    self.update_mode_targets()
            else:
                if self.mode != "IDLE":
                    self.mode = "IDLE"
                    self.update_mode_targets()
        self.update()

    def animate_eq(self):
        if self.mode in ("COMPACT_MEDIA", "EXPANDED_MEDIA") and self.media_info.get("status") == "Playing":
            import random
            self.eq_bars = [
                random.randint(4, 18),
                random.randint(6, 20),
                random.randint(3, 16),
                random.randint(5, 19)
            ]
            self.update()

    def on_tick_1s(self):
        self.idle_view_counter += 1
        now = datetime.now()
        now_mins = now.hour * 60 + now.minute
        
        # Check prayer time arrival
        for name, t_str, t_mins in self.prayer_times:
            if t_mins == now_mins and self.last_announced_prayer != name:
                self.last_announced_prayer = name
                self.trigger_prayer_alert(name)
                break
                
        if self.mode in ("IDLE", "EXPANDED_MEDIA", "COMPACT_MEDIA"):
            if self.mode == "EXPANDED_MEDIA":
                self.media_ctrl.poll_media()
            self.update()

    def poll_hardware_state(self):
        # 1. Caps Lock Check
        caps = get_caps_lock_state()
        if caps != self.last_caps_state:
            self.last_caps_state = caps
            self.caps_lock_state = caps
            self.trigger_caps_osd(caps)
            return

        # 2. System Volume Keys Check (External changes)
        vol, muted = get_volume()
        if vol != self.last_known_vol or muted != self.last_known_mute:
            self.last_known_vol = vol
            self.last_known_mute = muted
            self.trigger_volume_osd(vol, muted)
            return

        # 3. Notification Check from /tmp/macos-notifications-history.json
        if self.is_hidden_by_fullscreen:
            return
        if os.path.exists(NOTIF_FILE):
            try:
                with open(NOTIF_FILE, "r") as f:
                    notifs = json.load(f)
                    if notifs and isinstance(notifs, list):
                        latest = notifs[0]
                        notif_id = latest.get("id")
                        if self.last_notif_id is None:
                            self.last_notif_id = notif_id
                        elif notif_id != self.last_notif_id:
                            self.last_notif_id = notif_id
                            self.trigger_notification(
                                latest.get("app", "Notification"),
                                latest.get("summary", ""),
                                latest.get("body", "")
                            )
            except Exception:
                pass

    # --- OSD TRIGGERS ---
    def trigger_volume_osd(self, target_vol=None, target_muted=None):
        if target_vol is not None:
            self.vol_percent = target_vol
            self.vol_muted = target_muted if target_muted is not None else False
        else:
            self.vol_percent, self.vol_muted = get_volume()
            
        self.last_known_vol = self.vol_percent
        self.last_known_mute = self.vol_muted

        # Fluid volume animation
        if self.vol_anim and self.vol_anim.state() == QVariantAnimation.State.Running:
            self.vol_anim.stop()

        start_v = float(self.display_vol)
        end_v = float(self.vol_percent)

        self.vol_anim = QVariantAnimation(self)
        self.vol_anim.setDuration(160)
        self.vol_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.vol_anim.setStartValue(start_v)
        self.vol_anim.setEndValue(end_v)

        def on_vol_step(val):
            self.display_vol = float(val)
            if self.mode == "OSD_VOLUME":
                self.update()

        def on_vol_end():
            self.display_vol = end_v
            if self.mode == "OSD_VOLUME":
                self.update()

        self.vol_anim.valueChanged.connect(on_vol_step)
        self.vol_anim.finished.connect(on_vol_end)
        self.vol_anim.start()

        if self.mode != "OSD_VOLUME":
            if self.mode not in ("CAPS_OSD", "NOTIFICATION", "PRAYER_ALERT"):
                self.prev_mode = self.mode
            self.mode = "OSD_VOLUME"
            self.update_mode_targets()
        else:
            self.update()
        self.revert_timer.start(2200)

    def trigger_caps_osd(self, state):
        if self.mode != "CAPS_OSD":
            if self.mode not in ("OSD_VOLUME", "NOTIFICATION", "PRAYER_ALERT"):
                self.prev_mode = self.mode
            self.mode = "CAPS_OSD"
            self.update_mode_targets()
        else:
            self.update()
        self.revert_timer.start(1800)

    def trigger_notification(self, app_name, summary, body):
        self.active_notif = {"app": app_name, "summary": summary, "body": body}
        if self.mode not in ("OSD_VOLUME", "CAPS_OSD", "PRAYER_ALERT"):
            self.prev_mode = self.mode
        self.mode = "NOTIFICATION"
        self.update_mode_targets()
        self.revert_timer.start(4500)

    def trigger_prayer_alert(self, prayer_name):
        self.active_prayer_alert = prayer_name
        self.prev_mode = self.mode
        self.mode = "PRAYER_ALERT"
        self.update_mode_targets()
        
        if self.cfg.get("pause_music_on_adzan", True):
            if self.media_info.get("status") == "Playing":
                self.media_ctrl.play_pause()
                
        try:
            sound_file = "/usr/share/sounds/freedesktop/stereo/complete.oga"
            if os.path.exists(sound_file):
                subprocess.Popen(["paplay", sound_file], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass
            
        self.revert_timer.start(8000)

    def revert_transient_mode(self):
        self.collapse_to_base_mode()

    # --- SYSTEM FEATURE POLLERS ---
    def check_battery_status(self):
        if not self.cfg.get("enable_battery_alert", True):
            return
        has_bat, pct, charging = get_system_battery()
        if not has_bat:
            return
        self.has_battery = True
        if charging != getattr(self, "last_battery_charging", charging):
            self.last_battery_charging = charging
            self.last_battery_pct = pct
            self.trigger_battery_alert(pct, charging)
        elif pct <= 20 and not charging and getattr(self, "last_battery_pct", 100) > 20:
            self.last_battery_pct = pct
            self.trigger_battery_alert(pct, False)
        else:
            self.last_battery_pct = pct

    def check_privacy_dots(self):
        if getattr(self, "privacy_demo_active", False):
            return
        if not self.cfg.get("enable_privacy_dot", True):
            if self.privacy_cam_active or self.privacy_mic_active:
                self.privacy_cam_active = False
                self.privacy_mic_active = False
                self.update()
            return
        cam, mic = check_linux_privacy_usage()
        if cam != self.privacy_cam_active or mic != self.privacy_mic_active:
            self.privacy_cam_active = cam
            self.privacy_mic_active = mic
            if self.secondary_island:
                self.secondary_island.privacy_cam_active = cam
                self.secondary_island.privacy_mic_active = mic
                self.secondary_island.update()
            self.update()

    # --- Clipboard monitor -------------------------------------------------
    # Qt Wayland only reports clipboard changes for the focused surface; our
    # island is never focused, so QClipboard.dataChanged never fires here.
    # Klipper watches the real clipboard for us and exposes the text over D-Bus.
    KLIPPER_SERVICE = "org.kde.klipper"
    KLIPPER_PATH = "/klipper"
    KLIPPER_IFACE = "org.kde.klipper.klipper"

    def setup_klipper_clipboard_monitor(self):
        self._klipper_conn = QtDBus.QDBusConnection.sessionBus()
        self._klipper_ok = self._klipper_conn.connect(
            self.KLIPPER_SERVICE, self.KLIPPER_PATH, self.KLIPPER_IFACE,
            "clipboardHistoryUpdated", self.on_klipper_history_updated)
        if not self._klipper_ok:
            print("[ixsland] Klipper D-Bus tidak aktif — clipboard bubble hanya "
                  "mengandalkan Qt (hanya jalan di X11)", flush=True)
        self._klipper_timer = QTimer(self)
        self._klipper_timer.timeout.connect(self.poll_klipper_clipboard)
        self._klipper_timer.start(900)
        # Jangan tampilkan bubble untuk teks yang sudah ada saat app start.
        self.last_clipboard_text = self._read_klipper_clipboard().strip()

    @pyqtSlot()
    def on_klipper_history_updated(self):
        self.poll_klipper_clipboard()

    def _read_klipper_clipboard(self):
        msg = QtDBus.QDBusMessage.createMethodCall(
            self.KLIPPER_SERVICE, self.KLIPPER_PATH, self.KLIPPER_IFACE,
            "getClipboardContents")
        try:
            reply = self._klipper_conn.call(
                msg, QtDBus.QDBus.CallMode.Block, 300)
        except Exception:
            return ""
        if reply.type() == QtDBus.QDBusMessage.MessageType.ReplyMessage:
            args = reply.arguments()
            if args:
                return str(args[0]) or ""
        return ""

    def poll_klipper_clipboard(self):
        self.ingest_clipboard_text(self._read_klipper_clipboard())

    def ingest_clipboard_text(self, text):
        """Satu jalur masuk untuk semua sumber clipboard (Qt maupun Klipper)."""
        text = (text or "").strip()
        if not text or text == getattr(self, "last_clipboard_text", ""):
            return
        self.last_clipboard_text = text
        if not self.cfg.get("enable_clipboard_bubble", True):
            return
        self.trigger_clipboard_bubble(text)
        if self.secondary_island:
            self.secondary_island.trigger_clipboard_bubble(text)

    def on_clipboard_data_changed(self):
        app_inst = QApplication.instance()
        if not app_inst or not app_inst.clipboard():
            return
        self.ingest_clipboard_text(app_inst.clipboard().text())

    def is_foreground_fullscreen(self):
        g = getattr(self, "active_win_geom", None)
        if not g:
            return False
        x, y, w, h = g
        if w <= 0 or h <= 0:
            return False
        s = self.get_target_screen()
        if not s:
            return False
        geo = s.geometry()
        return (w >= geo.width() - 2 and h >= geo.height() - 2)

    def check_fullscreen_window(self):
        if not self.cfg.get("enable_game_mode", True):
            if getattr(self, "is_hidden_by_fullscreen", False):
                self.is_hidden_by_fullscreen = False
                self.show()
                if self.secondary_island:
                    self.secondary_island.show()
                self.init_placement()
            return
        is_fs = self.is_foreground_fullscreen()
        if is_fs and not self.is_hidden_by_fullscreen:
            self.is_hidden_by_fullscreen = True
            self.hide()
            if self.secondary_island:
                self.secondary_island.hide()
        elif not is_fs and self.is_hidden_by_fullscreen:
            self.is_hidden_by_fullscreen = False
            self.show()
            if self.secondary_island:
                self.secondary_island.show()
            self.init_placement()

    def apply_config(self, cfg):
        self.cfg = cfg
        self.scale = float(cfg.get("scale", 1.0))
        lat = cfg.get("latitude", -6.2088)
        lng = cfg.get("longitude", 106.8456)
        tz = cfg.get("timezone", 7.0)
        self.prayer_times = calculate_prayer_times(lat, lng, tz)
        sync_autostart_registration(cfg.get("autostart", True))
        self.init_placement()
        self.update_mask_for_mode()
        self.update()
        if self.secondary_island:
            sec = self.secondary_island
            sec.cfg = cfg
            sec.scale = self.scale
            sec.prayer_times = self.prayer_times
            sec.init_placement()
            sec.update_mask_for_mode()
            sec.update()

    def setup_system_tray(self):
        if not QSystemTrayIcon.isSystemTrayAvailable():
            self.tray_icon = None
            return
        self.tray_icon = QSystemTrayIcon(self)
        icon_path = os.path.join(ASSETS_DIR, "icon.png")
        if os.path.exists(icon_path):
            self.tray_icon.setIcon(QIcon(icon_path))
        menu = QMenu()
        menu.setStyleSheet("QMenu { background-color: #141822; color: #e0e0e0; border: 1px solid rgba(255,255,255,0.15); border-radius: 8px; padding: 6px; } QMenu::item { padding: 6px 24px; border-radius: 4px; font-size: 12px; } QMenu::item:selected { background-color: #0078D7; color: white; }")
        act_min = QAction("👁️ Sembunyikan / Munculkan Pulau", self)
        act_min.triggered.connect(self.toggle_minimize)
        menu.addAction(act_min)
        act_settings = QAction("⚙️ Pengaturan (Settings)", self)
        act_settings.triggered.connect(self.open_settings)
        menu.addAction(act_settings)
        menu.addSeparator()
        act_media = QAction("🎵 Demo Media Player", self)
        act_media.triggered.connect(lambda: self.media_ctrl.set_mock_track("Starboy", "The Weeknd, Daft Punk"))
        menu.addAction(act_media)
        act_recenter = QAction("🔄 Reset Posisi Tengah", self)
        act_recenter.triggered.connect(self.reset_position)
        menu.addAction(act_recenter)
        menu.addSeparator()
        act_quit = QAction("Keluar (Exit)", self)
        act_quit.triggered.connect(QApplication.instance().quit)
        menu.addAction(act_quit)
        self.tray_icon.setContextMenu(menu)
        self.tray_icon.setToolTip("ixsland Dynamic Island")
        self.tray_icon.activated.connect(self.on_tray_activated)
        self.tray_icon.show()

    def on_tray_activated(self, reason):
        if reason in (QSystemTrayIcon.ActivationReason.Trigger, QSystemTrayIcon.ActivationReason.DoubleClick):
            if self.is_minimized:
                self.toggle_minimize()
            else:
                self.open_settings()

    @pyqtSlot()
    def openSettings(self):
        self.open_settings()

    def open_settings(self):
        if self.settings_dialog is None:
            self.settings_dialog = SettingsDialog(self)
        self.settings_dialog.show()
        self.settings_dialog.raise_()
        self.settings_dialog.activateWindow()

    def toggle_minimize(self):
        self.is_minimized = not self.is_minimized
        if self.is_minimized:
            self.hide()
            s = self.get_target_screen()
            geom = s.geometry() if s else QRect(0, 0, 1920, 1080)
            if not self.hidden_trigger:
                self.hidden_trigger = HiddenTriggerWidget(self)
            self.hidden_trigger.move(geom.x() + (geom.width() - 130) // 2, geom.y())
            self.hidden_trigger.show()
            self.hidden_trigger.raise_()
            if self.tray_icon:
                self.tray_icon.showMessage(
                    "Dynamic Island Diminimalkan",
                    "Sentuh bar atas atau klik tray icon untuk memunculkan kembali.",
                    QSystemTrayIcon.MessageIcon.Information, 2000
                )
        else:
            if self.hidden_trigger:
                self.hidden_trigger.hide()
            self.show()
            self.raise_()
            self.init_placement()

    def check_for_updates(self, callback=None):
        if getattr(self, "update_checker", None) and self.update_checker.isRunning():
            return
        self.update_checker = UpdateCheckerThread(self)
        def on_done(has_update, tag, url, body):
            if has_update:
                self.latest_update_info = {"version": tag, "url": url, "body": body}
                self.trigger_notification(
                    "Pembaruan Tersedia",
                    f"Versi {tag} Dirilis",
                    "Klik pulau untuk mengunduh versi terbaru."
                )
                if self.tray_icon:
                    self.tray_icon.showMessage(
                        "Pembaruan ixsland Tersedia",
                        f"Versi {tag} sudah tersedia di GitHub.",
                        QSystemTrayIcon.MessageIcon.Information, 4000
                    )
            if callback:
                callback(has_update, tag, url, body)
        self.update_checker.updateChecked.connect(on_done)
        self.update_checker.start()

    def trigger_update_demo(self):
        demo_url = f"https://github.com/{GITHUB_REPO}/releases"
        self.latest_update_info = {"version": "v1.3.0", "url": demo_url, "body": "Fitur baru: Update Checker & Notifikasi"}
        self.trigger_notification(
            "Pembaruan Tersedia",
            "Versi v1.3.0 Dirilis 🚀",
            "Klik pulau ini untuk langsung membuka rilis terbaru."
        )

    def cleanup(self):
        if self.cursor_tracker:
            try:
                self.cursor_tracker.cleanup()
            except Exception:
                pass
        if getattr(self, "update_checker", None) and self.update_checker.isRunning():
            self.update_checker.quit()
            self.update_checker.wait(500)

    # --- NEW TRANSIENT MODES ---
    def trigger_battery_alert(self, pct, charging):
        self.battery_pct = pct
        self.battery_charging = charging
        if self.mode not in ("OSD_VOLUME", "CAPS_OSD", "PRAYER_ALERT"):
            self.prev_mode = self.mode
        self.mode = "BATTERY_ALERT"
        self.update_mode_targets()
        self.revert_timer.start(3800)

    def trigger_clipboard_bubble(self, text):
        if not text or not text.strip():
            return
        self.clipboard_snippet = text.strip()[:30]
        if self.mode not in ("OSD_VOLUME", "CAPS_OSD", "PRAYER_ALERT", "BATTERY_ALERT"):
            self.prev_mode = self.mode
        self.mode = "CLIPBOARD_BUBBLE"
        self.update_mode_targets()
        self.revert_timer.start(2400)

    def toggle_privacy_demo(self):
        self.privacy_demo_active = not getattr(self, "privacy_demo_active", False)
        self.privacy_cam_active = self.privacy_demo_active
        self.privacy_mic_active = self.privacy_demo_active
        self.update()

    # --- INPUT EVENTS ---
    def wheelEvent(self, event):
        delta = 3 if event.angleDelta().y() > 0 else -3
        change_volume(delta)
        new_v = max(0, min(150, self.vol_percent + delta))
        self.trigger_volume_osd(new_v, False)

    def _pill_geometry(self):
        scale = getattr(self, "scale", 1.0)
        canvas_w = CANVAS_W * scale
        pill_w = self.curr_pill_w * scale
        pill_h = self.curr_pill_h * scale
        pill_x = (canvas_w - pill_w) / 2.0
        pill_y = self.pill_y * scale
        return pill_x, pill_y, pill_w, pill_h, scale

    def _perform_pill_click(self):
        if self.mode in ("IDLE", "COMPACT_MEDIA"):
            self.mode = "EXPANDED_MEDIA"
            self.expanded_at = time.time()
            self.update_mode_targets()
        elif self.mode == "NOTIFICATION":
            if getattr(self, "latest_update_info", None) and self.latest_update_info.get("url"):
                QDesktopServices.openUrl(QUrl(self.latest_update_info["url"]))
                self.latest_update_info = None
                self.collapse_to_base_mode()
                return
            self.mode = "EXPANDED_MEDIA"
            self.expanded_at = time.time()
            self.update_mode_targets()
        elif self.mode in ("OSD_VOLUME", "CAPS_OSD", "PRAYER_ALERT", "BATTERY_ALERT", "CLIPBOARD_BUBBLE"):
            self.revert_timer.stop()
            self.collapse_to_base_mode()

    def _update_offset_from_geometry(self):
        self._apply_offset_from_topleft(self.geometry().topLeft())

    def _apply_offset_from_topleft(self, tl):
        """Wayland-safe: derive cfg offsets from an intended top-left, not live geometry."""
        s = self.get_target_screen()
        if not s:
            return
        geom = s.geometry()
        scale = getattr(self, "scale", 1.0)
        center_x = self.context_center_x(geom, scale)
        offset_x = tl.x() - center_x
        top_margin = int(round((tl.y() - geom.y()) / scale))
        self.cfg["offset_x"] = int(offset_x)
        self.cfg["top_margin"] = int(top_margin)
        if self.secondary_island:
            self.secondary_island.cfg["offset_x"] = int(offset_x)
            self.secondary_island.cfg["top_margin"] = int(top_margin)
        if self.settings_dialog:
            try:
                self.settings_dialog.sync_position_inputs(offset_x, top_margin)
            except Exception:
                pass
        # Push new pinned geometry to KWin script
        canvas_w = int(round(CANVAS_W * scale))
        canvas_h = int(round(CANVAS_H * scale))
        cx = center_x + int(self.cfg.get("offset_x", 0))
        cy = geom.y() + int(round(self.cfg.get("top_margin", 16) * scale))
        self._push_kwin_position(cx, cy, canvas_w, canvas_h)

    def mousePressEvent(self, event):
        self.raise_()
        pill_x, pill_y, pill_w, pill_h, scale = self._pill_geometry()
        pos = event.position()
        inside_pill = (
            pill_x <= pos.x() <= pill_x + pill_w and
            pill_y <= pos.y() <= pill_y + pill_h
        )
        nx = (pos.x() - pill_x) / scale
        ny = (pos.y() - pill_y) / scale

        if event.button() == Qt.MouseButton.LeftButton:
            # Manual drag: only when position unlocked and on the compact pill body
            if (inside_pill and not self.cfg.get("pos_locked", False)
                    and self.mode in ("IDLE", "COMPACT_MEDIA", "NOTIFICATION")):
                self._drag_pending = True
                self._dragging = False
                self._drag_start_gpos = event.globalPosition().toPoint()
                self._drag_start_geom = self.geometry()
                return

            if self.mode == "EXPANDED_MEDIA":
                w = self.curr_pill_w
                # Top action buttons: Settings [⚙], Minimize [🗕], Close [✕]
                if 4 <= ny <= 36:
                    if w - 88 <= nx <= w - 64:
                        self.open_settings()
                        return
                    if w - 62 <= nx <= w - 38:
                        self.toggle_minimize()
                        return
                    if nx >= w - 36:
                        self.collapse_to_base_mode()
                        return
                if not inside_pill:
                    self.collapse_to_base_mode()
                    return

                # Progress bar Seek
                bar_x = 18
                bar_y = 86
                bar_w = w - 36
                if bar_x - 6 <= nx <= bar_x + bar_w + 6 and bar_y - 8 <= ny <= bar_y + 16:
                    length = self.media_info.get("length", 0)
                    if length > 0:
                        click_ratio = max(0.0, min(1.0, (nx - bar_x) / float(bar_w)))
                        self.media_ctrl.seek(click_ratio * length)
                        return

                # Controls row: Previous / Play-Pause / Next
                if 104 <= ny <= 146:
                    mid_x = w / 2.0
                    if mid_x - 60 <= nx <= mid_x - 20:
                        self.media_ctrl.prev_track()
                        return
                    elif mid_x - 20 <= nx <= mid_x + 20:
                        self.media_ctrl.play_pause()
                        return
                    elif mid_x + 20 <= nx <= mid_x + 60:
                        self.media_ctrl.next_track()
                        return
                # Clicking elsewhere inside stays open (mouse exit handles auto-collapse)
                return

            # Non-expanded modes
            if inside_pill:
                self._perform_pill_click()

        elif event.button() == Qt.MouseButton.MiddleButton:
            self.media_ctrl.play_pause()
        elif event.button() == Qt.MouseButton.RightButton:
            if inside_pill:
                self.show_context_menu(event.globalPosition().toPoint())

    def mouseMoveEvent(self, event):
        gpos = event.globalPosition().toPoint()
        if self._drag_pending:
            if not self._dragging:
                if (gpos - self._drag_start_gpos).manhattanLength() > 4:
                    self._dragging = True
            if self._dragging:
                delta = gpos - self._drag_start_gpos
                new_tl = self._drag_start_geom.topLeft() + delta
                self.move(new_tl)
                self._apply_offset_from_topleft(new_tl)
                return

        self.on_global_cursor_moved(int(gpos.x()), int(gpos.y()))
        
        # Local widget check for fast response inside canvas (scale-aware)
        if self.mode == "EXPANDED_MEDIA" and (time.time() - self.expanded_at > 0.3):
            pill_x, pill_y, pill_w, pill_h, _scale = self._pill_geometry()
            rect = QRect(int(pill_x - 8), int(pill_y - 8), int(pill_w + 16), int(pill_h + 16))
            if not rect.contains(event.position().toPoint()):
                if not self.auto_collapse_timer.isActive():
                    self.auto_collapse_timer.start(120)
            else:
                if self.auto_collapse_timer.isActive():
                    self.auto_collapse_timer.stop()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._drag_pending:
            if self._dragging:
                save_config(self.cfg)
            else:
                self._perform_pill_click()
            self._drag_pending = False
            self._dragging = False
            self._drag_start_gpos = None
            self._drag_start_geom = None
        super().mouseReleaseEvent(event)

    def show_context_menu(self, point):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #1a1a1e;
                color: #e0e0e0;
                border: 1px solid rgba(255,255,255,0.15);
                border-radius: 8px;
                padding: 4px;
            }
            QMenu::item {
                padding: 6px 20px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #007acc;
                color: white;
            }
        """)
        
        act_toggle = QAction("Play / Pause Musik", self)
        act_toggle.triggered.connect(self.media_ctrl.play_pause)
        menu.addAction(act_toggle)

        locked = bool(self.cfg.get("pos_locked", False))
        act_lock = QAction("🔓 Buka Kunci Posisi (Drag)" if locked else "🔒 Kunci Posisi (Cegah Geser)", self)
        act_lock.triggered.connect(lambda: self.set_pos_locked(not self.cfg.get("pos_locked", False)))
        menu.addAction(act_lock)

        act_settings = QAction("⚙️ Pengaturan...", self)
        act_settings.triggered.connect(self.open_settings)
        menu.addAction(act_settings)

        act_recenter = QAction("🔄 Reset Posisi Tengah", self)
        act_recenter.triggered.connect(self.reset_position)
        menu.addAction(act_recenter)

        act_min = QAction("👁️ Sembunyikan / Minimize Pulau", self)
        act_min.triggered.connect(self.toggle_minimize)
        menu.addAction(act_min)
        
        act_spec = QAction("Ambil Screenshot (Spectacle)", self)
        act_spec.triggered.connect(lambda: subprocess.Popen(["spectacle", "-r"]))
        menu.addAction(act_spec)
        
        menu.addSeparator()
        act_quit = QAction("Tutup ixsland", self)
        act_quit.triggered.connect(QApplication.instance().quit)
        menu.addAction(act_quit)
        
        self.context_menu = menu
        menu.popup(point)

    # --- PAINT ENGINE ---
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        scale = getattr(self, "scale", 1.0)
        canvas_w = CANVAS_W * scale
        pill_w = self.curr_pill_w * scale
        pill_h = self.curr_pill_h * scale
        pill_x = (canvas_w - pill_w) / 2.0

        # PERMANENT TOP ANCHOR: Always pill_y inside fixed canvas (scaled)
        pill_y = self.pill_y * scale
        radius = (pill_h / 2.0) if self.mode != "EXPANDED_MEDIA" else (22.0 * scale)

        # Background Pill Glass
        path = QPainterPath()
        path.addRoundedRect(QRectF(pill_x, pill_y, pill_w, pill_h), radius, radius)

        opacity_val = int(self.cfg.get("bg_opacity", 98) * 2.55)
        painter.fillPath(path, QBrush(QColor(12, 12, 14, opacity_val)))

        # Border highlight
        border_col = QColor(255, 255, 255, 34)
        if self.mode == "CAPS_OSD" and self.caps_lock_state:
            border_col = QColor(255, 179, 0, 180)
        elif self.mode == "OSD_VOLUME":
            border_col = QColor(0, 212, 255, 180)
        elif self.mode == "NOTIFICATION":
            border_col = QColor(0, 230, 118, 140)
        elif self.mode == "PRAYER_ALERT":
            border_col = QColor(0, 180, 216, 200)
        elif self.mode == "BATTERY_ALERT":
            border_col = QColor(0, 230, 118, 180) if getattr(self, "battery_charging", True) else QColor(255, 68, 68, 180)
        elif self.mode == "CLIPBOARD_BUBBLE":
            border_col = QColor(0, 212, 255, 180)

        painter.strokePath(path, QPen(border_col, 1.2))

        # Unlocked position hint: subtle dashed cyan outline (drag is active)
        if (not self.cfg.get("pos_locked", False)) and self.mode in ("IDLE", "COMPACT_MEDIA"):
            painter.strokePath(path, QPen(QColor(0, 212, 255, 90), 1.0, Qt.PenStyle.DashLine))

        # Draw Content inside pill coordinate space (scaled)
        painter.save()
        painter.translate(pill_x, pill_y)
        painter.scale(scale, scale)

        w = self.curr_pill_w
        h = self.curr_pill_h

        if self.mode == "IDLE":
            self.paint_idle(painter, w, h)
        elif self.mode == "COMPACT_MEDIA":
            self.paint_compact_media(painter, w, h)
        elif self.mode == "EXPANDED_MEDIA":
            self.paint_expanded_media(painter, w, h)
        elif self.mode == "OSD_VOLUME":
            self.paint_osd_volume(painter, w, h)
        elif self.mode == "CAPS_OSD":
            self.paint_caps_osd(painter, w, h)
        elif self.mode == "NOTIFICATION":
            self.paint_notification(painter, w, h)
        elif self.mode == "PRAYER_ALERT":
            self.paint_prayer_alert(painter, w, h)
        elif self.mode == "BATTERY_ALERT":
            self.paint_battery_alert(painter, w, h)
        elif self.mode == "CLIPBOARD_BUBBLE":
            self.paint_clipboard_bubble(painter, w, h)

        # Draw Privacy Dots (Camera: Neon Green, Microphone: Neon Orange)
        if self.privacy_cam_active or self.privacy_mic_active:
            dot_r = 2.5
            dot_y = 7.0
            cur_dot_x = w - 10.0
            painter.setPen(Qt.PenStyle.NoPen)
            if self.privacy_cam_active:
                painter.setBrush(QBrush(QColor(0, 230, 118, 240)))
                painter.drawEllipse(QPointF(cur_dot_x, dot_y), dot_r, dot_r)
                cur_dot_x -= 8.0
            if self.privacy_mic_active:
                painter.setBrush(QBrush(QColor(255, 145, 0, 240)))
                painter.drawEllipse(QPointF(cur_dot_x, dot_y), dot_r, dot_r)

        painter.restore()

    def paint_idle(self, p, w, h):
        now = datetime.now()
        # 3-Phase Rotation: 0 = Time, 1 = Prayer, 2 = Interactive Mascot
        phase = (self.idle_view_counter // 5) % 3
        
        # Green status indicator dot
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor(0, 230, 118, 220)))
        p.drawEllipse(QPoint(16, int(h // 2)), 4, 4)

        if phase == 0:
            # Digital Clock
            p.setFont(QFont("Cantarell", 10, QFont.Weight.Bold))
            p.setPen(QColor(245, 245, 245))
            rect = QRect(26, 0, int(w - 36), int(h))
            p.drawText(rect, Qt.AlignmentFlag.AlignCenter, now.strftime("%H:%M:%S"))
        elif phase == 1:
            # Prayer Schedule
            now_mins = now.hour * 60 + now.minute
            next_prayer_name = "Subuh"
            next_prayer_time = "04:30"
            for name, t_str, t_mins in self.prayer_times:
                if t_mins > now_mins:
                    next_prayer_name = name
                    next_prayer_time = t_str
                    break
            p.setFont(QFont("Cantarell", 10, QFont.Weight.Bold))
            p.setPen(QColor(245, 245, 245))
            rect = QRect(26, 0, int(w - 36), int(h))
            p.drawText(rect, Qt.AlignmentFlag.AlignCenter, f"🕌 {next_prayer_name} {next_prayer_time}")
        else:
            if self.cfg.get("enable_mascot", True):
                # Interactive Robot Mascot (Gaze & Mouth follow cursor)
                self.paint_mascot(p, w, h)
            else:
                # Mascot disabled: fall back to digital clock
                p.setFont(QFont("Cantarell", 10, QFont.Weight.Bold))
                p.setPen(QColor(245, 245, 245))
                rect = QRect(26, 0, int(w - 36), int(h))
                p.drawText(rect, Qt.AlignmentFlag.AlignCenter, now.strftime("%H:%M:%S"))

    def paint_mascot(self, p, w, h):
        mid_x = w / 2.0
        mid_y = h / 2.0
        
        # Check hover proximity (scale-aware)
        scale = getattr(self, "scale", 1.0)
        island_cx = self.geometry().x() + (CANVAS_W * scale / 2.0)
        island_cy = self.geometry().y() + ((self.pill_y + (h / 2.0)) * scale)
        dist = math.hypot(self.cursor_x - island_cx, self.cursor_y - island_cy)
        is_hover = dist < (95.0 * scale)
        
        # Inactivity Sleep Check
        now = time.time()
        is_sleeping = (now - self.last_cursor_move_time) > 22.0
        
        # Natural Blink Engine (every 3.8s for 160ms)
        blink_cycle = (now % 3.8)
        is_blinking = blink_cycle < 0.16 and not is_sleeping and not is_hover

        eye_spacing = 17.0
        left_eye_x = mid_x - eye_spacing
        right_eye_x = mid_x + eye_spacing
        eye_y = mid_y - 2.0
        
        gx = self.curr_gaze_x
        gy = self.curr_gaze_y

        if is_sleeping:
            # Sleep state: eyes closed with floating zzZ
            p.setPen(QPen(QColor(0, 229, 255, 200), 2.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            for ex in (left_eye_x, right_eye_x):
                p.drawLine(QPointF(ex - 5, eye_y + 1), QPointF(ex + 5, eye_y + 1))
            # Resting mouth
            p.setPen(QPen(QColor(255, 255, 255, 180), 1.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.drawLine(QPointF(mid_x - 3, eye_y + 8), QPointF(mid_x + 3, eye_y + 8))
            # zzZ text
            p.setFont(QFont("Cantarell", 8, QFont.Weight.Bold))
            p.setPen(QColor(0, 229, 255, 180))
            p.drawText(QRect(int(mid_x + 28), int(eye_y - 8), 30, 20), Qt.AlignmentFlag.AlignLeft, "zZ")
            return

        if is_hover:
            # Hover Happy Joy: squinting eyes (^  ^) + blush + wide smile
            p.setPen(QPen(QColor(0, 229, 255, 255), 2.2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            for ex in (left_eye_x, right_eye_x):
                epath = QPainterPath()
                epath.moveTo(ex - 5.5, eye_y + 3)
                epath.quadTo(ex, eye_y - 4, ex + 5.5, eye_y + 3)
                p.drawPath(epath)
            
            # Pink Blush on Cheeks
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(QColor(255, 105, 180, 140)))
            p.drawEllipse(QPointF(left_eye_x - 8, eye_y + 5.5), 3.5, 2.2)
            p.drawEllipse(QPointF(right_eye_x + 8, eye_y + 5.5), 3.5, 2.2)
            
            # Wide smile
            p.setPen(QPen(QColor(255, 255, 255, 240), 2.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.setBrush(Qt.BrushStyle.NoBrush)
            mpath = QPainterPath()
            mpath.moveTo(mid_x - 5.5, eye_y + 7.5)
            mpath.quadTo(mid_x, eye_y + 12.0, mid_x + 5.5, eye_y + 7.5)
            p.drawPath(mpath)
            return

        if is_blinking:
            # Quick blink: horizontal sleek lines
            p.setPen(QPen(QColor(0, 229, 255, 240), 2.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            for ex in (left_eye_x, right_eye_x):
                p.drawLine(QPointF(ex - 5, eye_y), QPointF(ex + 5, eye_y))
        else:
            # Active OLED Eyes tracking cursor gaze
            for ex in (left_eye_x, right_eye_x):
                # Outer glow aura
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(QBrush(QColor(0, 229, 255, 60)))
                p.drawRoundedRect(QRectF(ex - 7, eye_y - 8, 14, 16), 5, 5)
                
                # Main Eye Capsule
                p.setBrush(QBrush(QColor(0, 229, 255, 240)))
                p.drawRoundedRect(QRectF(ex - 5.5, eye_y - 6.5, 11, 13), 4, 4)
                
                # Dynamic pupil shifted by gaze direction
                pupil_x = ex + (gx * 2.8)
                pupil_y = eye_y + (gy * 2.2)
                p.setBrush(QBrush(QColor(255, 255, 255, 255)))
                p.drawEllipse(QPointF(pupil_x, pupil_y), 3.0, 3.0)

        # Dynamic Mouth Expression tracking cursor
        mouth_x = mid_x + (gx * 2.2)
        mouth_y = eye_y + 8.5
        p.setPen(QPen(QColor(255, 255, 255, 230), 1.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.setBrush(Qt.BrushStyle.NoBrush)
        
        mpath = QPainterPath()
        if gx < -0.3:
            # Curiously smirking towards left cursor
            mpath.moveTo(mouth_x - 4, mouth_y + 1.2)
            mpath.quadTo(mouth_x, mouth_y + 2.8, mouth_x + 4, mouth_y)
        elif gx > 0.3:
            # Curiously smirking towards right cursor
            mpath.moveTo(mouth_x - 4, mouth_y)
            mpath.quadTo(mouth_x, mouth_y + 2.8, mouth_x + 4, mouth_y + 1.2)
        else:
            # Gentle cute smile
            mpath.moveTo(mouth_x - 4, mouth_y)
            mpath.quadTo(mouth_x, mouth_y + 2.8, mouth_x + 4, mouth_y)
            
        p.drawPath(mpath)

    def paint_compact_media(self, p, w, h):
        art = self.media_info.get("art_pixmap")
        art_rect = QRectF(7, (h - 26) / 2.0, 26, 26)
        if art and not art.isNull():
            p.save()
            clip = QPainterPath()
            clip.addRoundedRect(art_rect, 6, 6)
            p.setClipPath(clip)
            p.drawPixmap(art_rect.toRect(), art)
            p.restore()
        else:
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(QColor(40, 40, 48)))
            p.drawRoundedRect(art_rect, 6, 6)
            p.setFont(QFont("Cantarell", 11))
            p.setPen(QColor(200, 200, 200))
            p.drawText(art_rect, Qt.AlignmentFlag.AlignCenter, "🎵")

        # Equalizer bars
        eq_right = w - 12
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor(29, 185, 84)))
        for i, bar_h in enumerate(self.eq_bars):
            bx = eq_right - (4 - i) * 6
            by = (h - bar_h) / 2.0
            p.drawRoundedRect(QRectF(bx, by, 3.5, bar_h), 1.5, 1.5)

        title = self.media_info.get("title", "")
        artist = self.media_info.get("artist", "")
        text_rect_w = int(w - 42 - 34)

        if self.cfg.get("enable_marquee", True):
            draw_marquee_text(p, title, QRect(38, 4, text_rect_w, 16),
                              QFont("Cantarell", 9, QFont.Weight.Bold), QColor(255, 255, 255), self.marquee_offset)
            draw_marquee_text(p, artist, QRect(38, 20, text_rect_w, 14),
                              QFont("Cantarell", 8, QFont.Weight.Normal), QColor(160, 160, 165), self.marquee_offset * 0.8)
        else:
            p.setFont(QFont("Cantarell", 9, QFont.Weight.Bold))
            p.setPen(QColor(255, 255, 255))
            elided_title = p.fontMetrics().elidedText(title, Qt.TextElideMode.ElideRight, text_rect_w)
            p.drawText(QRect(38, 4, text_rect_w, 16), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, elided_title)

            p.setFont(QFont("Cantarell", 8, QFont.Weight.Normal))
            p.setPen(QColor(160, 160, 165))
            elided_artist = p.fontMetrics().elidedText(artist, Qt.TextElideMode.ElideRight, text_rect_w)
            p.drawText(QRect(38, 20, text_rect_w, 14), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, elided_artist)

    def paint_expanded_media(self, p, w, h):
        title = self.media_info.get("title", "")
        artist = self.media_info.get("artist", "")
        player = self.media_info.get("player", "Media")
        status = self.media_info.get("status", "Stopped")
        art = self.media_info.get("art_pixmap")

        art_rect = QRectF(16, 16, 54, 54)
        if art and not art.isNull():
            p.save()
            clip = QPainterPath()
            clip.addRoundedRect(art_rect, 10, 10)
            p.setClipPath(clip)
            p.drawPixmap(art_rect.toRect(), art)
            p.restore()
        else:
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(QColor(36, 36, 44)))
            p.drawRoundedRect(art_rect, 10, 10)
            p.setFont(QFont("Cantarell", 18))
            p.setPen(QColor(220, 220, 220))
            p.drawText(art_rect, Qt.AlignmentFlag.AlignCenter, "🎵")

        # Top-Right Action Buttons: Settings [⚙], Minimize [🗕], Close [✕]
        p.setFont(QFont("Cantarell", 11, QFont.Weight.Bold))
        p.setPen(QColor(170, 178, 195))
        p.drawText(QRect(int(w - 84), 12, 20, 20), Qt.AlignmentFlag.AlignCenter, "⚙")
        p.drawText(QRect(int(w - 58), 12, 20, 20), Qt.AlignmentFlag.AlignCenter, "🗕")
        p.setPen(QColor(160, 160, 170))
        p.drawText(QRect(int(w - 32), 12, 20, 20), Qt.AlignmentFlag.AlignCenter, "✕")

        info_x = 80
        info_w = max(60, int(w - info_x - 92))
        if self.cfg.get("enable_marquee", True):
            draw_marquee_text(p, title, QRect(info_x, 18, info_w, 20),
                              QFont("Cantarell", 11, QFont.Weight.Bold), QColor(255, 255, 255), self.marquee_offset)
            draw_marquee_text(p, artist, QRect(info_x, 38, info_w, 16),
                              QFont("Cantarell", 9, QFont.Weight.Normal), QColor(170, 170, 175), self.marquee_offset * 0.8)
        else:
            p.setFont(QFont("Cantarell", 11, QFont.Weight.Bold))
            p.setPen(QColor(255, 255, 255))
            elided_title = p.fontMetrics().elidedText(title, Qt.TextElideMode.ElideRight, info_w)
            p.drawText(QRect(info_x, 18, info_w, 20), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, elided_title)

            p.setFont(QFont("Cantarell", 9, QFont.Weight.Normal))
            p.setPen(QColor(170, 170, 175))
            elided_artist = p.fontMetrics().elidedText(artist, Qt.TextElideMode.ElideRight, info_w)
            p.drawText(QRect(info_x, 38, info_w, 16), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, elided_artist)

        p.setFont(QFont("Cantarell", 8, QFont.Weight.Bold))
        p.setPen(QColor(0, 180, 216))
        p.drawText(QRect(info_x, 56, info_w, 14), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, player.upper())

        # Progress Line
        pos = int(self.media_info.get("position", 0))
        length = int(self.media_info.get("length", 0))
        ratio = min(1.0, max(0.0, pos / float(length))) if length > 0 else 0.0

        bar_x = 18
        bar_y = 86
        bar_w = int(w - 36)
        bar_h = 5
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor(255, 255, 255, 40)))
        p.drawRoundedRect(QRectF(bar_x, bar_y, bar_w, bar_h), 2.5, 2.5)
        if ratio > 0:
            fill_w = max(4.0, bar_w * ratio)
            p.setBrush(QBrush(QColor(0, 212, 255)))
            p.drawRoundedRect(QRectF(bar_x, bar_y, fill_w, bar_h), 2.5, 2.5)

        p.setFont(QFont("Cantarell", 8, QFont.Weight.Medium))
        p.setPen(QColor(170, 170, 175))
        pos_str = f"{pos // 60}:{pos % 60:02d}"
        len_str = f"{length // 60}:{length % 60:02d}" if length > 0 else "--:--"
        p.drawText(QRect(bar_x, bar_y + 7, 50, 14), Qt.AlignmentFlag.AlignLeft, pos_str)
        p.drawText(QRect(bar_x + bar_w - 50, bar_y + 7, 50, 14), Qt.AlignmentFlag.AlignRight, len_str)

        # Controls
        mid_x = int(w // 2)
        ctrl_y = 108
        
        p.setFont(QFont("Cantarell", 14, QFont.Weight.Bold))
        p.setPen(QColor(220, 220, 225))
        p.drawText(QRect(mid_x - 55, ctrl_y, 30, 30), Qt.AlignmentFlag.AlignCenter, "⏮")
        
        play_icon = "⏸" if status == "Playing" else "▶"
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor(255, 255, 255, 30)))
        p.drawEllipse(QPoint(mid_x, ctrl_y + 15), 18, 18)
        p.setFont(QFont("Cantarell", 13, QFont.Weight.Bold))
        p.setPen(QColor(255, 255, 255))
        p.drawText(QRect(mid_x - 15, ctrl_y, 30, 30), Qt.AlignmentFlag.AlignCenter, play_icon)
        
        p.setFont(QFont("Cantarell", 14, QFont.Weight.Bold))
        p.setPen(QColor(220, 220, 225))
        p.drawText(QRect(mid_x + 25, ctrl_y, 30, 30), Qt.AlignmentFlag.AlignCenter, "⏭")

    def paint_osd_volume(self, p, w, h):
        vol_int = int(round(self.display_vol))
        if self.vol_muted or vol_int == 0:
            icon = "🔇"
        elif vol_int <= 33:
            icon = "🔈"
        elif vol_int <= 66:
            icon = "🔉"
        else:
            icon = "🔊"
            
        p.setFont(QFont("Cantarell", 12))
        p.setPen(QColor(255, 255, 255))
        p.drawText(QRect(12, 0, 24, int(h)), Qt.AlignmentFlag.AlignCenter, icon)

        bar_x = 42
        bar_y = (h - 6) / 2.0
        bar_w = int(w - 42 - 50)
        bar_h = 6

        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor(255, 255, 255, 45)))
        p.drawRoundedRect(QRectF(bar_x, bar_y, bar_w, bar_h), 3, 3)

        max_v = 150.0 if self.display_vol > 100.0 else 100.0
        ratio = min(1.0, max(0.0, self.display_vol / max_v))
        if ratio > 0 and not self.vol_muted:
            fill_w = max(4.0, bar_w * ratio)
            bar_color = QColor(0, 212, 255) if self.display_vol <= 100.0 else QColor(255, 179, 0)
            p.setBrush(QBrush(bar_color))
            p.drawRoundedRect(QRectF(bar_x, bar_y, fill_w, bar_h), 3, 3)

        text = "Mute" if self.vol_muted else f"{vol_int}%"
        p.setFont(QFont("Cantarell", 9, QFont.Weight.Bold))
        p.setPen(QColor(240, 240, 240))
        p.drawText(QRect(int(w - 46), 0, 40, int(h)), Qt.AlignmentFlag.AlignCenter, text)

    def paint_caps_osd(self, p, w, h):
        is_on = self.caps_lock_state
        icon = "🔠" if is_on else "🔤"
        text = "CAPS LOCK ON" if is_on else "CAPS LOCK OFF"
        color = QColor(255, 183, 77) if is_on else QColor(180, 180, 185)
        
        p.setFont(QFont("Cantarell", 11))
        p.setPen(QColor(255, 255, 255))
        p.drawText(QRect(14, 0, 24, int(h)), Qt.AlignmentFlag.AlignCenter, icon)
        
        p.setFont(QFont("Cantarell", 9, QFont.Weight.Bold))
        p.setPen(color)
        p.drawText(QRect(42, 0, int(w - 48), int(h)), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, text)

    def paint_notification(self, p, w, h):
        app = self.active_notif.get("app", "Notification")
        summary = self.active_notif.get("summary", "")
        body = self.active_notif.get("body", "")
        
        p.setFont(QFont("Cantarell", 8, QFont.Weight.Bold))
        p.setPen(QColor(0, 230, 118))
        header = f"💬 {app.upper()}"
        if summary:
            header += f" · {summary}"
        elided_header = p.fontMetrics().elidedText(header, Qt.TextElideMode.ElideRight, int(w - 28))
        p.drawText(QRect(14, 8, int(w - 28), 16), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, elided_header)

        p.setFont(QFont("Cantarell", 8, QFont.Weight.Normal))
        p.setPen(QColor(240, 240, 245))
        elided_body = p.fontMetrics().elidedText(body if body else "(Pesan baru)", Qt.TextElideMode.ElideRight, int(w - 28))
        p.drawText(QRect(14, 26, int(w - 28), 18), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, elided_body)

    def paint_prayer_alert(self, p, w, h):
        name = getattr(self, "active_prayer_alert", "Sholat")
        p.setFont(QFont("Cantarell", 9, QFont.Weight.Bold))
        p.setPen(QColor(0, 212, 255))
        p.drawText(QRect(14, 6, int(w - 28), 18), Qt.AlignmentFlag.AlignCenter, f"🕌 WAKTU {name.upper()} TELAH TIBA")
        
        p.setFont(QFont("Cantarell", 8, QFont.Weight.Normal))
        p.setPen(QColor(220, 220, 225))
        p.drawText(QRect(14, 26, int(w - 28), 16), Qt.AlignmentFlag.AlignCenter, "Mari tunaikan sholat tepat waktu")

    def paint_battery_alert(self, p, w, h):
        charging = getattr(self, "battery_charging", True)
        pct = getattr(self, "battery_pct", 100)
        p.setFont(QFont("Cantarell", 9, QFont.Weight.Bold))
        if charging:
            p.setPen(QColor(0, 230, 118))
            p.drawText(QRect(14, 6, int(w - 28), 18), Qt.AlignmentFlag.AlignCenter, f"⚡ PENGISIAN DAYA {pct}%")
            p.setFont(QFont("Cantarell", 8, QFont.Weight.Normal))
            p.setPen(QColor(220, 220, 225))
            p.drawText(QRect(14, 26, int(w - 28), 16), Qt.AlignmentFlag.AlignCenter, "Adaptor daya terhubung")
        else:
            p.setPen(QColor(255, 68, 68) if pct <= 20 else QColor(255, 179, 0))
            p.drawText(QRect(14, 6, int(w - 28), 18), Qt.AlignmentFlag.AlignCenter, f"🪫 BATERAI LEMAH {pct}%" if pct <= 20 else f"🔋 SISA BATERAI {pct}%")
            p.setFont(QFont("Cantarell", 8, QFont.Weight.Normal))
            p.setPen(QColor(220, 220, 225))
            p.drawText(QRect(14, 26, int(w - 28), 16), Qt.AlignmentFlag.AlignCenter, "Hubungkan ke charger sekarang" if pct <= 20 else "Berjalan pada daya baterai")

    def paint_clipboard_bubble(self, p, w, h):
        snippet = getattr(self, "clipboard_snippet", "")
        p.setFont(QFont("Cantarell", 8, QFont.Weight.Bold))
        p.setPen(QColor(0, 212, 255))
        p.drawText(QRect(14, 5, int(w - 28), 16), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, "📋 TEKS DISALIN")

        p.setFont(QFont("Cantarell", 8, QFont.Weight.Normal))
        p.setPen(QColor(240, 240, 245))
        elided = p.fontMetrics().elidedText(snippet, Qt.TextElideMode.ElideRight, int(w - 28))
        p.drawText(QRect(14, 23, int(w - 28), 16), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, elided)


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("ixsland")
    app.setDesktopFileName("ixsland")
    app.setQuitOnLastWindowClosed(False)

    media_ctrl = MediaController()

    cfg0 = load_config()
    # Default: layar utama. Nama layar lain (mis. DP-1) dipakai jika dipilih di Pengaturan.
    primary_target = cfg0.get("target_screen", "primary") or "primary"

    # Island tunggal — island sekunder dihapus
    island_screen2 = IxslandWidget(
        target_screen_name=primary_target,
        title_suffix="Screen 2",
        shared_media=media_ctrl,
        is_primary_instance=True
    )
    island_screen2.secondary_island = None

    if "--settings" in sys.argv:
        island_screen2.open_settings()

    def on_exit():
        island_screen2.cleanup()
    app.aboutToQuit.connect(on_exit)
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
