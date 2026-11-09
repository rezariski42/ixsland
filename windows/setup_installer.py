#!/usr/bin/env python3
"""
ixsland Dynamic Island — Setup Wizard (Windows 10/11)

Installer gaya umum: Next/Next, pilih folder tujuan, pilihan
Pasang / Perbaiki (Repair) / Copot Pemasangan (Uninstall).

Mode penggunaan:
    Setup.exe                  -> wizard pemasangan / perbaikan
    Setup.exe --uninstall      -> wizard copot pemasangan
    Setup.exe --uninstall -q   -> copot tanpa jendela (quiet)

Terdaftar di "Apps & Features" Windows (HKCU Uninstall) sehingga
bisa Copot / Ubah langsung dari Pengaturan Windows.
Tidak membutuhkan Python: aplikasi ini dikompilasi dengan PyInstaller.
"""

import os
import sys
import shutil
import zipfile
import subprocess
import traceback
import tempfile

APP_NAME = "ixsland Dynamic Island"
PUBLISHER = "Reza Riski"
VERSION = "1.3.0"
DEFAULT_DIR = r"C:\ixsland"
UNINST_KEY = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\ixsland"
RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"

PAGE_WELCOME, PAGE_DIR, PAGE_MODE, PAGE_PROGRESS, PAGE_FINISH = range(5)


# ----------------------------------------------------------------------------
# Helper path / payload
# ----------------------------------------------------------------------------
def frozen_base():
    return getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))


def payload_path():
    p = os.path.join(frozen_base(), "payload.zip")
    if not os.path.exists(p):
        p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "payload.zip")
    return p


def desktop_dir():
    return os.path.join(os.environ.get("USERPROFILE", r"C:\Users\Administrator"), "Desktop")


def startmenu_dir():
    appdata = os.environ.get("APPDATA", "")
    if not appdata:
        return desktop_dir()
    return os.path.join(appdata, r"Microsoft\Windows\Start Menu\Programs")


def this_exe():
    return sys.executable if getattr(sys, "frozen", False) else os.path.abspath(__file__)


def stop_app():
    subprocess.run(["taskkill", "/f", "/im", "ixsland.exe"], capture_output=True)
    subprocess.run(["taskkill", "/f", "/im", "pythonw.exe"], capture_output=True)


def create_shortcut(lnk_path, target, workdir, desc=""):
    try:
        ps = (
            '$ws = New-Object -ComObject WScript.Shell; '
            f'$s = $ws.CreateShortcut("{lnk_path}"); '
            f'$s.TargetPath = "{target}"; '
            f'$s.WorkingDirectory = "{workdir}"; '
            f'$s.Description = "{desc}"; '
            f'$s.IconLocation = "{target},0"; '
            '$s.Save()'
        )
        subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps],
            capture_output=True,
        )
        return os.path.exists(lnk_path)
    except Exception:
        return False


def register_autostart(exe_path, enabled):
    try:
        import winreg
        try:
            key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, RUN_KEY)
        except Exception:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE)
        if enabled:
            winreg.SetValueEx(key, "ixsland", 0, winreg.REG_SZ, f'"{exe_path}"')
        else:
            try:
                winreg.DeleteValue(key, "ixsland")
            except FileNotFoundError:
                pass
        winreg.CloseKey(key)
        return True
    except Exception:
        return False


def register_uninstall(dest_dir, exe_path, uninstall_exe):
    """Daftarkan ke Apps & Features (per-user, tanpa admin)."""
    try:
        import winreg
        key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, UNINST_KEY)
        size_kb = 0
        try:
            for root, _dirs, files in os.walk(dest_dir):
                for f in files:
                    try:
                        size_kb += os.path.getsize(os.path.join(root, f))
                    except OSError:
                        pass
            size_kb //= 1024
        except OSError:
            pass
        winreg.SetValueEx(key, "DisplayName", 0, winreg.REG_SZ, APP_NAME)
        winreg.SetValueEx(key, "DisplayVersion", 0, winreg.REG_SZ, VERSION)
        winreg.SetValueEx(key, "Publisher", 0, winreg.REG_SZ, PUBLISHER)
        winreg.SetValueEx(key, "InstallLocation", 0, winreg.REG_SZ, dest_dir)
        winreg.SetValueEx(key, "DisplayIcon", 0, winreg.REG_SZ, exe_path)
        winreg.SetValueEx(key, "UninstallString", 0, winreg.REG_SZ, f'"{uninstall_exe}" --uninstall')
        winreg.SetValueEx(key, "QuietUninstallString", 0, winreg.REG_SZ, f'"{uninstall_exe}" --uninstall -q')
        winreg.SetValueEx(key, "ModifyPath", 0, winreg.REG_SZ, f'"{uninstall_exe}"')
        winreg.SetValueEx(key, "EstimatedSize", 0, winreg.REG_DWORD, int(size_kb))
        winreg.SetValueEx(key, "NoModify", 0, winreg.REG_DWORD, 0)
        winreg.SetValueEx(key, "NoRepair", 0, winreg.REG_DWORD, 0)
        winreg.CloseKey(key)
        return True
    except Exception:
        return False


def unregister_uninstall():
    try:
        import winreg
        winreg.DeleteKey(winreg.HKEY_CURRENT_USER, UNINST_KEY)
    except Exception:
        pass


def installed_location():
    try:
        import winreg
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, UNINST_KEY, 0, winreg.KEY_READ)
        val, _ = winreg.QueryValueEx(key, "InstallLocation")
        winreg.CloseKey(key)
        if val and os.path.isdir(val):
            return val
    except Exception:
        pass
    return DEFAULT_DIR if os.path.isdir(DEFAULT_DIR) else ""


def is_installed():
    return bool(installed_location()) or os.path.exists(os.path.join(DEFAULT_DIR, "ixsland.exe"))


# ----------------------------------------------------------------------------
# Pekerjaan instalasi / copot (jalan di thread terpisah)
# ----------------------------------------------------------------------------
def run_install(dest_dir, make_desktop, make_startmenu, autostart, log, set_progress):
    stop_app()
    zp = payload_path()
    if not os.path.exists(zp):
        raise RuntimeError("Berkas paket payload.zip tidak ditemukan di dalam Setup.")

    os.makedirs(dest_dir, exist_ok=True)
    log(f"Mengekstrak paket ke {dest_dir} ...")
    with zipfile.ZipFile(zp, "r") as zf:
        names = zf.namelist()
        total = max(1, len(names))
        # extractall memberi progres per berkas
        done = 0
        for info in zf.infolist():
            zf.extract(info, dest_dir)
            done += 1
            if done % 10 == 0 or done == total:
                set_progress(done, total)
    log(f"Selesai mengekstrak {total} berkas.")

    exe = os.path.join(dest_dir, "ixsland.exe")
    if not os.path.exists(exe):
        raise RuntimeError("ixsland.exe tidak ditemukan setelah ekstraksi.")

    # Uninstall.exe: salinan Setup supaya bisa dicopot dari Apps & Features
    uninstall_exe = os.path.join(dest_dir, "Uninstall.exe")
    try:
        if os.path.abspath(this_exe()) != os.path.abspath(uninstall_exe):
            log("Menyalin uninstaller ...")
            shutil.copy2(this_exe(), uninstall_exe)
    except Exception as e:
        log(f"(peringatan) gagal menyalin uninstaller: {e}")

    if make_desktop:
        lnk = os.path.join(desktop_dir(), f"{APP_NAME}.lnk")
        log(f"Membuat pintasan desktop: {lnk}")
        create_shortcut(lnk, exe, dest_dir, APP_NAME)
    if make_startmenu:
        lnk = os.path.join(startmenu_dir(), f"{APP_NAME}.lnk")
        log(f"Membuat pintasan menu Mulai: {lnk}")
        create_shortcut(lnk, exe, dest_dir, APP_NAME)

    log("Mendaftarkan jalur mulai otomatis (Startup) ..." if autostart
        else "Menonaktifkan jalur mulai otomatis ...")
    register_autostart(exe, autostart)

    log("Mendaftarkan aplikasi ke Apps & Features ...")
    register_uninstall(dest_dir, exe, uninstall_exe)

    log("Instalasi selesai.")
    return exe


def run_uninstall(dest_dir, remove_config, log, set_progress):
    stop_app()

    # Pintasan
    for folder in (desktop_dir(), startmenu_dir()):
        lnk = os.path.join(folder, f"{APP_NAME}.lnk")
        if os.path.exists(lnk):
            try:
                os.remove(lnk)
                log(f"Menghapus pintasan: {lnk}")
            except OSError as e:
                log(f"(peringatan) gagal menghapus {lnk}: {e}")

    # Startup
    register_autostart("", False)
    log("Menghapus entri Startup ...")

    # Berkas
    if dest_dir and os.path.isdir(dest_dir):
        total = 0
        for root, _d, files in os.walk(dest_dir):
            total += len(files)
        total = max(1, total)
        done = 0
        log(f"Menghapus {dest_dir} ...")
        shutil.rmtree(dest_dir, ignore_errors=True)
        set_progress(total, total)
        if os.path.isdir(dest_dir):
            try:
                cmd = f'cmd.exe /c "ping 127.0.0.1 -n 3 >nul & rmdir /s /q \\"{dest_dir}\\""'
                subprocess.Popen(cmd, shell=True)
            except Exception:
                pass
            log("(jadwal) berkas terkunci dijadwalkan hapus otomatis setelah uninstaller keluar.")
        else:
            log("Folder instalasi telah dihapus.")
    else:
        log("Folder instalasi tidak ditemukan (sudah bersih?).")

    unregister_uninstall()
    log("Menghapus entri Apps & Features ...")

    if remove_config:
        cfg_dir = os.path.join(
            os.environ.get("LOCALAPPDATA", ""), "ixsland"
        )
        if cfg_dir and os.path.isdir(cfg_dir):
            shutil.rmtree(cfg_dir, ignore_errors=True)
            log(f"Menghapus data pengguna: {cfg_dir}")
        cache_dir = os.path.join(os.environ.get("TEMP", ""), "ixsland_cache")
        if cache_dir and os.path.isdir(cache_dir):
            shutil.rmtree(cache_dir, ignore_errors=True)

    log("Copot pemasangan selesai.")
    return ""


# ----------------------------------------------------------------------------
# Wizard
# ----------------------------------------------------------------------------
def build_wizard(mode, quiet):
    from PyQt6.QtCore import Qt, QThread, pyqtSignal
    from PyQt6.QtWidgets import (
        QApplication, QWizard, QWizardPage, QWidget, QVBoxLayout, QHBoxLayout,
        QLabel, QLineEdit, QPushButton, QFileDialog, QRadioButton, QCheckBox,
        QProgressBar, QTextEdit,
    )
    from PyQt6.QtGui import QPixmap

    dark = """
        QWidget { background-color: #101218; color: #EDEDED; font-family: 'Segoe UI', Arial; font-size: 12px; }
        QLabel { color: #E0E2EC; }
        QLabel#title { color: #FFFFFF; font-size: 17px; font-weight: bold; }
        QLabel#subtitle { color: #8F9BB3; font-size: 12px; }
        QLabel#accent { color: #00D4FF; font-weight: bold; }
        QLineEdit, QTextEdit {
            background: #1E2332; color: #FFFFFF; border: 1px solid rgba(255,255,255,0.15);
            border-radius: 6px; padding: 7px 10px; selection-background-color: #0078D7;
        }
        QPushButton {
            background: #202636; color: #FFFFFF; border: 1px solid rgba(255,255,255,0.15);
            border-radius: 6px; padding: 7px 16px; font-weight: bold;
        }
        QPushButton:hover { background: #2B3348; border-color: #00D4FF; }
        QPushButton:disabled { color: #6C7280; background: #171B24; }
        QCheckBox, QRadioButton { color: #E0E2EC; spacing: 8px; padding: 3px; }
        QCheckBox::indicator, QRadioButton::indicator { width: 16px; height: 16px; }
        QProgressBar { background: #252A38; border: 1px solid rgba(255,255,255,0.12);
                       border-radius: 6px; height: 18px; text-align: center; color: #FFFFFF; }
        QProgressBar::chunk { background: #00D4FF; border-radius: 5px; }
        QWizard { background-color: #101218; }
        QWizard QLabel#title { font-size: 18px; }
        QWizard QWidget#side { background: #0B0D12; }
        QToolButton { color: #E0E2EC; background: transparent; border: none; }
    """

    class Worker(QThread):
        log_sig = pyqtSignal(str)
        prog_sig = pyqtSignal(int, int)
        done_sig = pyqtSignal(bool, str)

        def __init__(self, kind, dest, opts):
            super().__init__()
            self.kind = kind
            self.dest = dest
            self.opts = opts

        def run(self):
            try:
                if self.kind == "uninstall":
                    run_uninstall(self.dest, self.opts.get("remove_config", False),
                                  self.log_sig.emit, self._prog)
                else:
                    exe = run_install(
                        self.dest,
                        self.opts.get("desktop", True),
                        self.opts.get("startmenu", True),
                        self.opts.get("autostart", True),
                        self.log_sig.emit, self._prog,
                    )
                    self.done_sig.emit(True, exe)
                    return
                self.done_sig.emit(True, "")
            except Exception as e:
                traceback.print_exc()
                self.log_sig.emit(f"ERROR: {e}")
                self.done_sig.emit(False, str(e))

        def _prog(self, done, total):
            self.prog_sig.emit(int(done), int(total))

    class WelcomePage(QWizardPage):
        def __init__(self):
            super().__init__()
            self.setTitle("Selamat Datang di Pemasang ixsland")
            self.setSubTitle("Dynamic Island untuk Windows 10 & 11")
            lay = QVBoxLayout(self)
            lbl = QLabel(
                f"<b>{APP_NAME}</b> versi {VERSION}<br><br>"
                "Wizard ini akan memasang Dynamic Island ke komputer Anda. "
                "Disarankan menutup semua aplikasi lain sebelum melanjutkan.<br><br>"
                "Klik <b>Berikutnya</b> untuk melanjutkan, atau <b>Batal</b> untuk keluar."
            )
            lbl.setWordWrap(True)
            lay.addWidget(lbl)
            lay.addStretch()

    class DirPage(QWizardPage):
        def __init__(self, initial):
            super().__init__()
            self.setTitle("Pilih Lokasi Pemasangan")
            self.setSubTitle("Dynamic Island akan dipasang ke folder berikut")
            lay = QVBoxLayout(self)
            lay.addWidget(QLabel("Folder tujuan:"))
            row = QHBoxLayout()
            self.edit = QLineEdit(initial)
            self.edit.textChanged.connect(self.completeChanged)
            row.addWidget(self.edit, 1)
            btn = QPushButton("Jelajahi ...")
            btn.clicked.connect(self.browse)
            row.addWidget(btn)
            lay.addLayout(row)
            tip = QLabel(
                "Ubah folder jika ingin menyimpan di lokasi lain. "
                "Jika pemasangan terpasang, gunakan tombol berikutnya untuk memperbarui."
            )
            tip.setWordWrap(True)
            tip.setStyleSheet("color: #8C92A4; font-size: 11px;")
            lay.addWidget(tip)
            lay.addStretch()

        def browse(self):
            d = QFileDialog.getExistingDirectory(self, "Pilih folder tujuan", self.edit.text())
            if d:
                self.edit.setText(d)

        def initializePage(self):
            loc = installed_location()
            if loc:
                self.edit.setText(loc)

        def isComplete(self):
            return bool(self.edit.text().strip())

        def destination(self):
            return self.edit.text().strip().strip('"')

    class ModePage(QWizardPage):
        def __init__(self, initial_mode):
            super().__init__()
            self.setTitle("Opsi Pemasangan")
            self.setSubTitle("Pilih tindakan dan opsi tambahan")
            lay = QVBoxLayout(self)

            self.grp_label = QLabel("Tindakan:")
            self.grp_label.setObjectName("accent")
            lay.addWidget(self.grp_label)

            self.rb_install = QRadioButton("Pasang / Perbarui (instalasi baru atau versi terbaru)")
            self.rb_repair = QRadioButton("Perbaiki (Repair) — pasang ulang berkas tanpa menghapus pengaturan)")
            self.rb_uninstall = QRadioButton("Copot Pemasangan (Uninstall) — hapus ixsland dari komputer")
            lay.addWidget(self.rb_install)
            lay.addWidget(self.rb_repair)
            lay.addWidget(self.rb_uninstall)

            if initial_mode == "uninstall":
                self.rb_uninstall.setChecked(True)
            elif initial_mode == "repair" or is_installed():
                self.rb_repair.setChecked(True)
            else:
                self.rb_install.setChecked(True)

            lay.addSpacing(8)
            lay.addWidget(QLabel("Opsi:"))
            self.cb_desktop = QCheckBox("Buat pintasan di Desktop")
            self.cb_desktop.setChecked(True)
            self.cb_start = QCheckBox("Buat pintasan di Menu Mulai (Start)")
            self.cb_start.setChecked(True)
            self.cb_auto = QCheckBox("Jalankan otomatis saat Windows Startup")
            self.cb_auto.setChecked(True)
            self.cb_cfg = QCheckBox("Hapus juga data & pengaturan pengguna (%LOCALAPPDATA%\\ixsland)")
            self.cb_cfg.setChecked(False)
            lay.addWidget(self.cb_desktop)
            lay.addWidget(self.cb_start)
            lay.addWidget(self.cb_auto)
            lay.addWidget(self.cb_cfg)

            self._btns = [self.rb_install, self.rb_repair, self.rb_uninstall]
            for b in self._btns:
                b.toggled.connect(self._sync)
            self._sync()

        def _sync(self):
            un = self.rb_uninstall.isChecked()
            for w in (self.cb_desktop, self.cb_start, self.cb_auto):
                w.setEnabled(not un)
            self.cb_cfg.setEnabled(un)
            self.setTitle(
                "Copot Pemasangan ixsland" if un else "Opsi Pemasangan"
            )

        def mode(self):
            if self.rb_uninstall.isChecked():
                return "uninstall"
            if self.rb_repair.isChecked():
                return "repair"
            return "install"

        def options(self):
            return {
                "desktop": self.cb_desktop.isChecked(),
                "startmenu": self.cb_start.isChecked(),
                "autostart": self.cb_auto.isChecked(),
                "remove_config": self.cb_cfg.isChecked(),
            }

    class ProgressPage(QWizardPage):
        def __init__(self):
            super().__init__()
            self._done = False
            self.setTitle("Sedang Memasang")
            self.setSubTitle("Harap tunggu, proses sedang berjalan ...")
            lay = QVBoxLayout(self)
            self.bar = QProgressBar()
            self.bar.setRange(0, 100)
            lay.addWidget(self.bar)
            self.log = QTextEdit()
            self.log.setReadOnly(True)
            lay.addWidget(self.log, 1)
            self.setCommitPage(True)
            self.setButtonText(QWizard.WizardButton.CommitButton, "Berikutnya >")

        def isComplete(self):
            return self._done

        def append(self, text):
            self.log.append(text)
            self.log.verticalScrollBar().setValue(self.log.verticalScrollBar().maximum())

        def set_value(self, done, total):
            if total > 0:
                self.bar.setValue(int(done * 100 / total))

        def finish(self, ok, msg):
            self._done = True
            if not ok:
                self.bar.setValue(0)
                self.append(f"GAGAL: {msg}")
            else:
                self.bar.setValue(100)
            self.completeChanged.emit()

    class FinishPage(QWizardPage):
        def __init__(self):
            super().__init__()
            self.setTitle("Pemasangan Selesai")
            self.setSubTitle("Wizard telah menyelesaikan pemasangan ixsland")
            lay = QVBoxLayout(self)
            self.lbl = QLabel("")
            self.lbl.setWordWrap(True)
            lay.addWidget(self.lbl)
            self.cb_launch = QCheckBox("Luncurkan ixsland Dynamic Island sekarang")
            self.cb_launch.setChecked(True)
            lay.addWidget(self.cb_launch)
            lay.addStretch()

        def set_result(self, kind, msg):
            if kind == "uninstall":
                self.setTitle("Copot Pemasangan Selesai")
                self.lbl.setText(
                    "ixsland Dynamic Island telah dicopot dari komputer Anda.<br><br>"
                    + (msg or "")
                )
                self.cb_launch.hide()
            else:
                self.setTitle("Pemasangan Selesai")
                self.lbl.setText(
                    "🎉 <b>Instalasi berhasil!</b><br><br>"
                    "ixsland terpasang dan siap dipakai. Lihat bagian atas tengah layar "
                    "untuk menikmati Dynamic Island.<br><br>"
                    "Pengaturan bisa dibuka lewat ikon ⚙ di island atau lewat pintasan Desktop."
                )
                self.cb_launch.show()

    # --- Wizard ---
    wizard = QWizard()
    wizard.setWindowTitle(f"{APP_NAME} — Pemasang")
    wizard.setWizardStyle(QWizard.WizardStyle.ClassicStyle)
    wizard.setButtonText(QWizard.WizardButton.NextButton, "Berikutnya >")
    wizard.setButtonText(QWizard.WizardButton.BackButton, "< Kembali")
    wizard.setButtonText(QWizard.WizardButton.CancelButton, "Batal")
    wizard.setButtonText(QWizard.WizardButton.FinishButton, "Selesai")
    wizard.setMinimumSize(640, 440)

    p_welcome = WelcomePage()
    p_dir = DirPage(DEFAULT_DIR)
    p_mode = ModePage(mode)
    p_prog = ProgressPage()
    p_fin = FinishPage()
    wizard.addPage(p_welcome)
    wizard.addPage(p_dir)
    wizard.addPage(p_mode)
    wizard.addPage(p_prog)
    wizard.addPage(p_fin)

    state = {"kind": mode, "worker": None, "dest": DEFAULT_DIR, "opts": {}, "result": ""}

    def on_current(id_):
        if id_ == PAGE_PROGRESS and state["worker"] is None:
            kind = p_mode.mode()
            dest = p_dir.destination() or DEFAULT_DIR
            opts = p_mode.options()
            state.update(kind=kind, dest=dest, opts=opts)
            if kind == "uninstall":
                p_prog.setTitle("Sedang Mencopot Pemasangan")
            else:
                p_prog.setTitle("Sedang Memasang")
            p_prog.append(f"Mode: {kind} | Tujuan: {dest}")
            worker = Worker(kind, dest, opts)
            worker.log_sig.connect(p_prog.append)
            worker.prog_sig.connect(p_prog.set_value)
            worker.done_sig.connect(on_done)
            state["worker"] = worker
            worker.start()

        if id_ == PAGE_FINISH:
            p_fin.set_result(state["kind"], state["result"])

    def on_done(ok, msg):
        state["result"] = "" if ok else msg
        p_prog.finish(ok, msg or "")
        if ok and state["kind"] != "uninstall" and msg:
            p_fin.cb_launch.setChecked(True)

    wizard.currentIdChanged.connect(on_current)
    wizard.setOption(QWizard.WizardOption.NoBackButtonOnLastPage, True)

    app = QApplication.instance()
    app.setStyleSheet(dark)
    wizard.setStyleSheet(dark)

    if quiet:
        p_prog.append("Mode sunyi (-q)")
    wizard._pages = {"welcome": p_welcome, "dir": p_dir, "mode": p_mode,
                     "progress": p_prog, "finish": p_fin}
    return wizard


def main():
    args = [a.lower() for a in sys.argv[1:]]
    quiet = ("-q" in args) or ("--quiet" in args)
    if "--uninstall" in args or "-u" in args:
        mode = "uninstall"
    elif "--repair" in args:
        mode = "repair"
    else:
        mode = "install"

    # Jika uninstaller dijalankan langsung dari dalam folder target (C:\ixsland\Uninstall.exe),
    # salin dirinya ke %TEMP% lalu spawn runner baru agar folder target tidak terkunci.
    if mode == "uninstall" and "--spawned" not in args:
        inst = installed_location()
        me = os.path.abspath(this_exe())
        if inst and os.path.isdir(inst) and me.lower().startswith(os.path.abspath(inst).lower()):
            tmp_runner = os.path.join(tempfile.gettempdir(), "ixsland_uninstall_runner.exe")
            try:
                shutil.copy2(me, tmp_runner)
                cmd = [tmp_runner] + sys.argv[1:] + ["--spawned"]
                subprocess.Popen(cmd)
                sys.exit(0)
            except Exception:
                pass

    from PyQt6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    app.setApplicationName("ixsland Setup")
    app.setStyle("Fusion")

    if mode == "uninstall" and quiet:
        # Jalankan langsung tanpa jendela
        try:
            run_uninstall(installed_location(), True, lambda s: print(s),
                          lambda d, t: None)
        except Exception:
            traceback.print_exc()
        return

    wizard = build_wizard(mode, quiet)
    pages = wizard._pages

    def on_finished(result):
        try:
            if int(result) != 1:            # 1 = QDialog.Accepted
                return
            if pages["mode"].mode() == "uninstall":
                return
            if not pages["finish"].cb_launch.isChecked():
                return
            dest = pages["dir"].destination() or DEFAULT_DIR
            exe = os.path.join(dest, "ixsland.exe")
            if os.path.exists(exe):
                subprocess.Popen([exe], cwd=dest)
        except Exception:
            pass

    wizard.finished.connect(on_finished)
    wizard.show()
    wizard.resize(700, 470)
    sys.exit(wizard.exec())


if __name__ == "__main__":
    main()