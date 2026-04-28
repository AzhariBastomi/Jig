"""
RecycleView Tkinter — OOP Task Manager
Fullscreen 1024x600 (Waveshare 7" HDMI)
Tidak ada library eksternal — semua built-in Python
"""

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
import random
import math
import sys
import os

# Import BluetoothScanner dari folder Lib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from Lib.bluetooth_scan import BluetoothScanner

# ══════════════════════════════════════════════════════════════════
#  PALETTE
# ══════════════════════════════════════════════════════════════════
C = {
    "bg":        "#0F0F1A",
    "surface":   "#1A1A2E",
    "card":      "#22223A",
    "card_hov":  "#2C2C44",
    "border":    "#33334A",
    "accent":    "#7B68EE",
    "text":      "#E8E8F0",
    "sub":       "#8888AA",
    "ok":        "#3DD68C",
    "warn":      "#FFB347",
    "err":       "#FF6B6B",
    "bar_bg":    "#2E2E44",
}

# ══════════════════════════════════════════════════════════════════
#  BASE TASK
# ══════════════════════════════════════════════════════════════════
class BaseTask:
    NAME  = "Base Task"
    ICON  = "X"
    COLOR = "#7B68EE"

    def __init__(self, label=""):
        self.label    = label or self.NAME
        self.progress = 0
        self.running  = False
        self._stop    = False

    def _step_duration(self):
        return 0.1

    def _increment(self):
        return random.randint(2, 6)

    def detail_info(self):
        return (
            f"{self.ICON}  {self.label}\n"
            f"---------------------\n"
            f"Tipe     : {self.NAME}\n"
            f"Progress : {self.progress}%\n"
            f"Status   : {self._status_text()}"
        )

    def _status_text(self):
        if self.progress >= 100: return "Selesai"
        if self.running:         return "Berjalan"
        if self.progress > 0:    return "Dijeda"
        return "Belum mulai"

    def reset(self):
        self._stop    = True
        self.running  = False
        self.progress = 0

    def run(self, on_tick, on_done):
        if self.running or self.progress >= 100:
            return
        self._stop   = False
        self.running = True

        def _worker():
            while not self._stop and self.progress < 100:
                inc = self._increment()
                self.progress = min(self.progress + inc, 100)
                on_tick(self.progress)
                time.sleep(self._step_duration())
            self.running = False
            if self.progress >= 100:
                on_done()

        threading.Thread(target=_worker, daemon=True).start()


# ══════════════════════════════════════════════════════════════════
#  TASK 1 — DownloadTask
# ══════════════════════════════════════════════════════════════════
class DownloadTask(BaseTask):
    NAME  = "Download File"
    ICON  = "D"
    COLOR = "#3B9EFF"

    def __init__(self, filename=""):
        super().__init__(label=f"Download: {filename or 'data.zip'}")
        self.filename  = filename or "data.zip"
        self.file_size = random.randint(50, 500)
        self.speed     = round(random.uniform(5.0, 20.0), 1)

    def _step_duration(self):
        return 0.08 if self.progress <= 80 else 0.16

    def _increment(self):
        if self.progress < 60:   return random.randint(4, 9)
        elif self.progress < 85: return random.randint(2, 5)
        else:                    return random.randint(1, 3)

    def detail_info(self):
        dl = int(self.file_size * self.progress / 100)
        return (
            f"[{self.ICON}] {self.label}\n"
            f"---------------------\n"
            f"Tipe      : {self.NAME}\n"
            f"File      : {self.filename}\n"
            f"Ukuran    : {self.file_size} MB\n"
            f"Terunduh  : {dl} / {self.file_size} MB\n"
            f"Kecepatan : {self.speed} Mbps\n"
            f"Progress  : {self.progress}%\n"
            f"Status    : {self._status_text()}"
        )


# ══════════════════════════════════════════════════════════════════
#  TASK 2 — AITrainingTask
# ══════════════════════════════════════════════════════════════════
class AITrainingTask(BaseTask):
    NAME  = "AI Training"
    ICON  = "AI"
    COLOR = "#E040FB"

    def __init__(self, model_name=""):
        super().__init__(label=f"Training: {model_name or 'ResNet-50'}")
        self.model_name = model_name or "ResNet-50"
        self.epochs     = random.randint(3, 10)
        self.batch_size = random.choice([16, 32, 64])
        self.loss       = round(random.uniform(1.5, 3.0), 4)

    def _step_duration(self):
        return random.uniform(0.15, 0.28)

    def _increment(self):
        roll = random.random()
        if roll < 0.1:   return 0
        elif roll < 0.3: return random.randint(1, 2)
        else:            return random.randint(2, 5)

    def detail_info(self):
        epoch_now = max(1, math.ceil(self.progress * self.epochs / 100))
        self.loss = max(0.01, self.loss - random.uniform(0.005, 0.03))
        return (
            f"[{self.ICON}] {self.label}\n"
            f"---------------------\n"
            f"Tipe      : {self.NAME}\n"
            f"Model     : {self.model_name}\n"
            f"Epoch     : {epoch_now} / {self.epochs}\n"
            f"Batch Size: {self.batch_size}\n"
            f"Loss      : {self.loss:.4f}\n"
            f"Progress  : {self.progress}%\n"
            f"Status    : {self._status_text()}"
        )


# ══════════════════════════════════════════════════════════════════
#  TASK 3 — BackupTask
# ══════════════════════════════════════════════════════════════════
class BackupTask(BaseTask):
    NAME  = "Cloud Backup"
    ICON  = "BK"
    COLOR = "#3DD68C"

    def __init__(self, folder=""):
        super().__init__(label=f"Backup: {folder or '/home/user'}")
        self.folder      = folder or "/home/user"
        self.total_files = random.randint(200, 2000)
        self.total_size  = random.randint(1, 50)

    def _step_duration(self):
        return 0.07

    def _increment(self):
        return random.randint(3, 7)

    def detail_info(self):
        backed = int(self.total_files * self.progress / 100)
        return (
            f"[{self.ICON}] {self.label}\n"
            f"---------------------\n"
            f"Tipe       : {self.NAME}\n"
            f"Folder     : {self.folder}\n"
            f"Total File : {self.total_files:,}\n"
            f"Terbackup  : {backed:,} file\n"
            f"Ukuran     : {self.total_size} GB\n"
            f"Progress   : {self.progress}%\n"
            f"Status     : {self._status_text()}"
        )



# ══════════════════════════════════════════════════════════════════
#  TASK 4 — BluetoothScanTask
# ══════════════════════════════════════════════════════════════════

# ── Hardcode nama target di sini ──────────────────────────────────
BT_TARGET_NAME = "asdasd"   # ganti sesuai nama Bluetooth yang dicari
# ─────────────────────────────────────────────────────────────────

class BluetoothScanTask(BaseTask):
    """
    Scan perangkat Bluetooth menggunakan hcitool scan --flush.
    Mencari target BT_TARGET_NAME — stop otomatis saat ketemu.
    """
    NAME  = "Bluetooth Scan"
    ICON  = "BT"
    COLOR = "#00BCD4"

    def __init__(self, label=""):
        super().__init__(label=label or f"BT Scan: cari '{BT_TARGET_NAME}'")
        self.found_devices  = []   # semua device yang terdeteksi
        self.target_device  = None # device yang cocok dengan target
        self.error_msg      = ""
        self._scanner       = None
        self.scan_duration  = 10

    def run(self, on_tick, on_done):
        if self.running or self.progress >= 100:
            return
        self._stop          = False
        self.running        = True
        self.found_devices  = []
        self.target_device  = None
        self.error_msg      = ""

        print(f"[BT] ══════════════════════════════════════", flush=True)
        print(f"[BT] Memulai scan Bluetooth (hcitool scan --flush)", flush=True)
        print(f"[BT] Target  : '{BT_TARGET_NAME}'", flush=True)
        print(f"[BT] Mode    : Stop otomatis jika target ditemukan", flush=True)
        print(f"[BT] ══════════════════════════════════════", flush=True)

        def _on_device(mac, name):
            self.found_devices.append({"mac": mac, "name": name})
            print(f"[BT] Ditemukan  : {mac}  —  {name}", flush=True)

            # Cek apakah ini target yang dicari (case-insensitive)
            if BT_TARGET_NAME.lower() in name.lower():
                self.target_device = {"mac": mac, "name": name}
                print(f"[BT] ✓ TARGET KETEMU! Menghentikan scan...", flush=True)
                print(f"[BT]   Nama : {name}", flush=True)
                print(f"[BT]   MAC  : {mac}", flush=True)
                # Stop scanner segera
                if self._scanner:
                    self._scanner.stop()

        def _on_progress(pct, found):
            if self._stop:
                return
            self.progress = min(pct, 99)
            on_tick(self.progress)
            bar = "█" * (pct // 5) + "░" * (20 - pct // 5)
            print(f"\r[BT] [{bar}] {pct:3d}%  ({found} device)", end="", flush=True)

        def _on_done(devices):
            self.found_devices = devices
            self.progress      = 100
            self.running       = False
            on_tick(100)
            on_done()
            print(f"\n[BT] ══ Hasil Scan ══════════════════════", flush=True)
            if self.target_device:
                print(f"[BT] STATUS  : ✓ TARGET DITEMUKAN", flush=True)
                print(f"[BT] Nama    : {self.target_device['name']}", flush=True)
                print(f"[BT] MAC     : {self.target_device['mac']}", flush=True)
            else:
                print(f"[BT] STATUS  : ✗ Target '{BT_TARGET_NAME}' tidak ditemukan", flush=True)
            print(f"[BT] Total scan : {len(devices)} perangkat", flush=True)
            if devices:
                print(f"[BT] Semua device:", flush=True)
                for i, d in enumerate(devices, 1):
                    mark = " ← TARGET" if d['mac'] == (self.target_device or {}).get('mac') else ""
                    print(f"[BT]   {i:2d}. {d['mac']}  —  {d['name']}{mark}", flush=True)
            print(f"[BT] ══════════════════════════════════════", flush=True)

        def _on_error(msg):
            self.error_msg = msg
            self.running   = False
            self.progress  = 100
            on_tick(100)
            on_done()
            print(f"\n[BT] ERROR: {msg}", flush=True)

        self._scanner = BluetoothScanner(
            on_device=_on_device,
            on_progress=_on_progress,
            on_done=_on_done,
            on_error=_on_error,
            flush=True,
            scan_duration=self.scan_duration,
        )
        self._scanner.start()

    def reset(self):
        if self._scanner:
            self._scanner.stop()
            print(f"[BT] Scan direset.", flush=True)
        self._scanner      = None
        self.found_devices = []
        self.target_device = None
        self.error_msg     = ""
        self._stop         = True
        self.running       = False
        self.progress      = 0

    def detail_info(self):
        if self.error_msg:
            return (
                f"[{self.ICON}] {self.label}\n"
                f"---------------------\n"
                f"Status : ERROR\n\n"
                f"{self.error_msg}"
            )
        n = len(self.found_devices)
        lines = [
            f"[{self.ICON}] {self.label}",
            f"---------------------",
            f"Target    : {BT_TARGET_NAME}",
            f"Progress  : {self.progress}%",
            f"Status    : {self._status_text()}",
            f"Scan      : {n} perangkat ditemukan",
            f"",
        ]
        if self.target_device:
            lines += [
                f"✓ TARGET DITEMUKAN:",
                f"  Nama : {self.target_device['name']}",
                f"  MAC  : {self.target_device['mac']}",
                f"",
            ]
        elif self.progress >= 100:
            lines.append(f"✗ Target '{BT_TARGET_NAME}' tidak ditemukan.")

        if self.found_devices:
            lines.append("Semua Perangkat Terdeteksi:")
            for i, d in enumerate(self.found_devices, 1):
                mark = " ← TARGET" if self.target_device and d['mac'] == self.target_device['mac'] else ""
                lines.append(f"  {i:2d}. {d['mac']}  —  {d['name']}{mark}")
        return "\n".join(lines)

# ══════════════════════════════════════════════════════════════════
#  REGISTRY
# ══════════════════════════════════════════════════════════════════
TASK_REGISTRY = [DownloadTask, AITrainingTask, BackupTask, BluetoothScanTask]

TASK_DEFAULTS = {
    DownloadTask:   ["model_weights.pt", "dataset.zip", "checkpoint.bin", "pretrained.h5"],
    AITrainingTask: ["ResNet-50", "BERT-base", "YOLOv8", "GPT-2-small"],
    BackupTask:     ["/home/user/docs", "/var/www", "/etc/config", "/home/user/projects"],
    BluetoothScanTask: ["BT Scan Area 1", "BT Scan Area 2", "BT Scan Lab", "BT Scan Ruangan"],
}

TASK_DESC = {
    DownloadTask:   "Unduh file dari server / internet",
    AITrainingTask: "Latih model machine learning",
    BackupTask:     "Backup data ke penyimpanan cloud",
    BluetoothScanTask: "Scan perangkat Bluetooth via hcitool --flush",
}


# ══════════════════════════════════════════════════════════════════
#  DIALOG — Pilih Task
# ══════════════════════════════════════════════════════════════════
class TaskPickerDialog(tk.Toplevel):
    """Modal dialog untuk memilih jenis task."""

    def __init__(self, parent):
        super().__init__(parent)
        self.result = None
        self._parent = parent

        W, H = 480, 380
        px = parent.winfo_rootx() + (parent.winfo_width()  - W) // 2
        py = parent.winfo_rooty() + (parent.winfo_height() - H) // 2
        self.geometry(f"{W}x{H}+{px}+{py}")
        self.resizable(False, False)
        self.configure(bg=C["surface"])

        # Kunci agar taskbar tidak muncul:
        self.transient(parent)          # dialog terikat ke parent window
        self.overrideredirect(True)     # hilangkan title bar & taskbar entry
        self.attributes("-topmost", True)  # selalu di atas

        self._build()
        self._add_drag()                # supaya bisa digeser walau tanpa title bar
        self.update_idletasks()
        self.deiconify()
        self.lift()
        self.after(10, self._safe_grab)

    def _safe_grab(self):
        try:
            self.grab_set()
            self.bind("<Escape>", lambda e: self.destroy())  # Esc = tutup dialog
        except Exception:
            self.after(50, self._safe_grab)

    def _add_drag(self):
        """Drag dihandle lewat titlebar, tidak perlu bind ke seluruh window."""
        self._drag_x = 0
        self._drag_y = 0

    def _drag_start(self, e):
        self._drag_x = e.x
        self._drag_y = e.y

    def _drag_move(self, e):
        dx = e.x - self._drag_x
        dy = e.y - self._drag_y
        x  = self.winfo_x() + dx
        y  = self.winfo_y() + dy
        self.geometry(f"+{x}+{y}")

    def _build(self):
        # ── Title bar custom dengan tombol X ──────────────────
        titlebar = tk.Frame(self, bg=C["accent"], pady=0)
        titlebar.pack(fill="x")

        tk.Label(titlebar, text="  Tambah Task Baru",
                 bg=C["accent"], fg="white",
                 font=("Segoe UI", 11, "bold"), pady=10,
                 anchor="w").pack(side="left", fill="x", expand=True)

        # Tombol X pojok kanan atas
        btn_close = tk.Label(titlebar, text=" ✕ ",
                             bg=C["accent"], fg="white",
                             font=("Segoe UI", 12, "bold"),
                             padx=10, pady=10, cursor="hand2")
        btn_close.pack(side="right")
        btn_close.bind("<Button-1>", lambda e: self.destroy())
        btn_close.bind("<Enter>",    lambda e: btn_close.config(bg=C["err"]))
        btn_close.bind("<Leave>",    lambda e: btn_close.config(bg=C["accent"]))

        # Drag hanya dari titlebar (lebih natural)
        titlebar.bind("<ButtonPress-1>",  lambda e: self._drag_start(e))
        titlebar.bind("<B1-Motion>",      lambda e: self._drag_move(e))

        # ── Subjudul ──────────────────────────────────────────
        tk.Label(self, text="Pilih jenis task:",
                 bg=C["surface"], fg=C["sub"],
                 font=("Segoe UI", 10), pady=6).pack()

        tk.Frame(self, bg=C["border"], height=1).pack(fill="x", padx=20, pady=(0, 6))

        for cls in TASK_REGISTRY:
            self._card(cls)

        tk.Frame(self, bg=C["border"], height=1).pack(fill="x", padx=20, pady=(8, 6))

        # Tombol Batal di bawah
        btn = tk.Label(self, text="✕  Batal",
                       bg=C["card"], fg=C["sub"],
                       font=("Segoe UI", 10, "bold"), pady=8, cursor="hand2")
        btn.pack(fill="x", padx=20, pady=(0, 10))
        btn.bind("<Button-1>", lambda e: self.destroy())
        btn.bind("<Enter>",    lambda e: btn.config(bg=C["card_hov"]))
        btn.bind("<Leave>",    lambda e: btn.config(bg=C["card"]))

    def _card(self, cls):
        color = cls.COLOR

        card = tk.Frame(self, bg=C["card"], cursor="hand2")
        card.pack(fill="x", padx=20, pady=3)

        badge = tk.Label(card, text=cls.ICON,
                         bg=color, fg="white",
                         font=("Segoe UI", 10, "bold"),
                         width=5, pady=12)
        badge.pack(side="left")

        info = tk.Frame(card, bg=C["card"])
        info.pack(side="left", fill="x", expand=True, padx=12, pady=10)

        tk.Label(info, text=cls.NAME,
                 bg=C["card"], fg=C["text"],
                 font=("Segoe UI", 11, "bold"), anchor="w").pack(fill="x")

        tk.Label(info, text=TASK_DESC.get(cls, ""),
                 bg=C["card"], fg=C["sub"],
                 font=("Segoe UI", 9), anchor="w").pack(fill="x")

        tk.Label(card, text=">",
                 bg=C["card"], fg=C["sub"],
                 font=("Segoe UI", 15), padx=12).pack(side="right")

        def _hover(on, f=card):
            bg = C["card_hov"] if on else C["card"]
            f.config(bg=bg)
            for w in f.winfo_children():
                try:
                    if w.cget("cursor") != "hand2":
                        w.config(bg=bg)
                except Exception:
                    pass
                for w2 in w.winfo_children():
                    try: w2.config(bg=bg)
                    except Exception: pass

        def _pick(c=cls):
            param = random.choice(TASK_DEFAULTS[c])
            self.result = c(param)
            self.destroy()

        for w in [card, badge, info] + list(info.winfo_children()):
            w.bind("<Button-1>", lambda e, fn=_pick: fn())
            w.bind("<Enter>",   lambda e, on=True:  _hover(on))
            w.bind("<Leave>",   lambda e, on=False: _hover(on))


# ══════════════════════════════════════════════════════════════════
#  RecycleView ITEM — disesuaikan untuk 1024x600
# ══════════════════════════════════════════════════════════════════
class RecycleViewItem(tk.Frame):
    """
    Layout 2 kolom: kiri (info + bar) | kanan (tombol vertikal)
    Cocok untuk layar lebar 1024px.
    """

    def __init__(self, parent, task, app_ref, **kwargs):
        super().__init__(parent, bg=C["card"], **kwargs)
        self.task    = task
        self.app_ref = app_ref
        self._build()

    def _build(self):
        self.config(padx=14, pady=10)

        # ── KIRI: info + progress bar ──────────────────────────
        left = tk.Frame(self, bg=C["card"])
        left.pack(side="left", fill="both", expand=True)

        # Baris 1: badge + judul + persen
        r1 = tk.Frame(left, bg=C["card"])
        r1.pack(fill="x")

        tk.Label(r1, text=f" {self.task.ICON} ",
                 bg=self.task.COLOR, fg="white",
                 font=("Segoe UI", 10, "bold"),
                 padx=6, pady=3).pack(side="left")

        self.lbl_title = tk.Label(r1, text=self.task.label,
                                  bg=C["card"], fg=C["text"],
                                  font=("Segoe UI", 10, "bold"), anchor="w")
        self.lbl_title.pack(side="left", fill="x", expand=True, padx=(10, 0))

        self.lbl_pct = tk.Label(r1, text="0%",
                                bg=C["card"], fg=C["err"],
                                font=("Segoe UI", 11, "bold"), width=5)
        self.lbl_pct.pack(side="right")

        # Baris 2: tipe task
        tk.Label(left, text=self.task.NAME,
                 bg=C["card"], fg=C["sub"],
                 font=("Segoe UI", 8), anchor="w").pack(fill="x", padx=2, pady=(2, 4))

        # Progress bar
        self.cv = tk.Canvas(left, height=8, bg=C["card"],
                            highlightthickness=0, bd=0)
        self.cv.pack(fill="x", pady=(0, 4))
        self.cv.bind("<Configure>", self._draw)

        # ── KANAN: tombol vertikal ──────────────────────────────
        right = tk.Frame(self, bg=C["card"])
        right.pack(side="right", padx=(12, 0))

        self.btn_start = self._btn(right, "  Start  ", self.task.COLOR, self._do_start)
        self.btn_start.pack(pady=(0, 4))
        self._btn(right, "  Reset  ", C["warn"], self._do_reset).pack(pady=(0, 4))
        self._btn(right, "  Info   ", C["sub"],  self._do_info ).pack()

    def _btn(self, parent, text, color, cmd):
        b = tk.Label(parent, text=text, bg=color, fg="white",
                     font=("Segoe UI", 9, "bold"),
                     padx=8, pady=6, cursor="hand2", width=8)
        b.bind("<Button-1>", lambda e: cmd())
        b.bind("<Enter>",    lambda e: b.config(bg=_lighten(color)))
        b.bind("<Leave>",    lambda e: b.config(bg=color))
        return b

    def _draw(self, _=None):
        self.cv.delete("all")
        w = self.cv.winfo_width()
        h = self.cv.winfo_height()
        r = h // 2
        _pill(self.cv, 0, 0, w, h, r, C["bar_bg"])
        fw = max(int(w * self.task.progress / 100), 0)
        if fw:
            _pill(self.cv, 0, 0, fw, h, r, _pcolor(self.task.progress))

    def _do_start(self):
        self.task.run(
            on_tick=lambda v: self.app_ref.after(0, self._tick, v),
            on_done=lambda:   self.app_ref.after(0, self._done),
        )
        self.app_ref.refresh_status()

    def _do_reset(self):
        self.task.reset()
        self._tick(0)

    def _do_info(self):
        messagebox.showinfo("Detail Task", self.task.detail_info())

    def _tick(self, v):
        self.task.progress = v
        self.lbl_pct.config(text=f"{v}%", fg=_pcolor(v))
        self._draw()
        self.app_ref.refresh_status()

    def _done(self):
        self.lbl_pct.config(text="100%", fg=C["ok"])
        self._draw()
        self.app_ref.refresh_status()


# ══════════════════════════════════════════════════════════════════
#  RECYCLE VIEW
# ══════════════════════════════════════════════════════════════════
class RecycleView(tk.Frame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg=C["bg"], **kwargs)
        self._items = []
        self._build_ui()

    def _build_ui(self):
        sb = ttk.Scrollbar(self, orient="vertical")
        sb.pack(side="right", fill="y")

        self.cv = tk.Canvas(self, bg=C["bg"], highlightthickness=0,
                            yscrollcommand=sb.set)
        self.cv.pack(side="left", fill="both", expand=True)
        sb.config(command=self.cv.yview)

        self.inner = tk.Frame(self.cv, bg=C["bg"])
        self._wid  = self.cv.create_window((0, 0), window=self.inner, anchor="nw")

        self.inner.bind("<Configure>",
            lambda e: self.cv.configure(scrollregion=self.cv.bbox("all")))
        self.cv.bind("<Configure>",
            lambda e: self.cv.itemconfig(self._wid, width=e.width))

        self.cv.bind_all("<MouseWheel>", self._scroll)
        self.cv.bind_all("<Button-4>",   self._scroll)
        self.cv.bind_all("<Button-5>",   self._scroll)

    def _scroll(self, e):
        if   e.num == 4: self.cv.yview_scroll(-1, "units")
        elif e.num == 5: self.cv.yview_scroll( 1, "units")
        else:            self.cv.yview_scroll(int(-e.delta / 120), "units")

    def add(self, w):
        self._items.append(w)
        w.pack(in_=self.inner, fill="x", padx=14, pady=(0, 8))
        # Force render agar widget langsung tampil tanpa harus scroll dulu
        self.inner.update_idletasks()
        self.cv.configure(scrollregion=self.cv.bbox("all"))

    def items(self):
        return self._items

    def clear(self):
        for w in self._items: w.destroy()
        self._items.clear()


# ══════════════════════════════════════════════════════════════════
#  MAIN APP — Fullscreen 1024x600
# ══════════════════════════════════════════════════════════════════
class App(tk.Tk):
    W, H = 1024, 600

    def __init__(self):
        super().__init__()
        self.title("Task Manager")
        self.configure(bg=C["bg"])

        # Fullscreen untuk Waveshare 7" HDMI 1024x600
        self.geometry(f"{self.W}x{self.H}+0+0")
        self.resizable(False, False)

        # Tekan Escape untuk keluar fullscreen (opsional)
        self.bind("<Escape>", lambda e: self.destroy())
        self.bind("<F11>",    lambda e: self.attributes("-fullscreen",
                                not self.attributes("-fullscreen")))

        # Coba fullscreen penuh (override jika perlu)
        self.attributes("-fullscreen", True)

        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("Vertical.TScrollbar",
                        background=C["card"], troughcolor=C["bg"],
                        bordercolor=C["bg"], arrowcolor=C["sub"])

        self._build()
        self._load_defaults()

    def _build(self):
        self._header()
        self._toolbar()
        self.rv = RecycleView(self)
        self.rv.pack(fill="both", expand=True)
        self._statusbar()

    def _header(self):
        hdr = tk.Frame(self, bg=C["surface"], pady=10)
        hdr.pack(fill="x")

        # Judul kiri
        left = tk.Frame(hdr, bg=C["surface"])
        left.pack(side="left", padx=20)

        tk.Label(left, text="Task Manager",
                 bg=C["surface"], fg=C["text"],
                 font=("Segoe UI", 16, "bold")).pack(anchor="w")
        tk.Label(left, text="RecycleView  Tkinter OOP  —  1024×600",
                 bg=C["surface"], fg=C["sub"],
                 font=("Segoe UI", 8)).pack(anchor="w")

        # Info ringkas kanan
        self.lbl_summary = tk.Label(hdr, text="",
                                    bg=C["surface"], fg=C["sub"],
                                    font=("Segoe UI", 9), padx=20)
        self.lbl_summary.pack(side="right")

    def _toolbar(self):
        bar = tk.Frame(self, bg=C["bg"], pady=8)
        bar.pack(fill="x", padx=16)

        self._tbtn(bar, "+  Tambah Task",   C["accent"], self._open_picker).pack(side="left")
        self._tbtn(bar, "  Jalankan Semua", "#3B9EFF",   self._start_all  ).pack(side="left", padx=(8, 0))
        self._tbtn(bar, "  Reset Semua",    C["warn"],   self._reset_all  ).pack(side="left", padx=(8, 0))
        self._tbtn(bar, "  Hapus Semua",    C["err"],    self._clear_all  ).pack(side="left", padx=(8, 0))

        # Tombol keluar pojok kanan
        self._tbtn(bar, "  Keluar  [Esc]",  "#444466",   self.destroy     ).pack(side="right")

    def _tbtn(self, parent, text, color, cmd):
        b = tk.Label(parent, text=text, bg=color, fg="white",
                     font=("Segoe UI", 9, "bold"),
                     padx=14, pady=7, cursor="hand2")
        b.bind("<Button-1>", lambda e: cmd())
        b.bind("<Enter>",    lambda e: b.config(bg=_lighten(color)))
        b.bind("<Leave>",    lambda e: b.config(bg=color))
        return b

    def _statusbar(self):
        self._sv = tk.StringVar(value="Siap.")
        bar = tk.Frame(self, bg="#0A0A14", pady=4)
        bar.pack(fill="x", side="bottom")

        tk.Label(bar, textvariable=self._sv,
                 bg="#0A0A14", fg=C["sub"],
                 font=("Segoe UI", 8), padx=14).pack(side="left")

        tk.Label(bar, text="F11: Toggle Fullscreen  |  Esc: Keluar",
                 bg="#0A0A14", fg="#44445A",
                 font=("Segoe UI", 8), padx=14).pack(side="right")

    def _load_defaults(self):
        defaults = [
            DownloadTask("model_weights.pt"),
            AITrainingTask("ResNet-50"),
            BackupTask("/home/user/docs"),
            DownloadTask("dataset_v2.zip"),
            AITrainingTask("BERT-base"),
            BackupTask("/var/www"),
            DownloadTask("checkpoint.bin"),
        ]
        for t in defaults:
            t.progress = random.randint(0, 55)
            self._add_task(t)
        self.refresh_status()
        # Force redraw semua progress bar setelah semua item selesai di-load
        self.after(200, self._force_redraw_all)

    def _force_redraw_all(self):
        """Paksa semua progress bar dan canvas untuk re-render."""
        self.update_idletasks()
        for w in self.rv.items():
            w._draw()
        self.rv.cv.configure(scrollregion=self.rv.cv.bbox("all"))

    def _add_task(self, task):
        w = RecycleViewItem(self.rv.inner, task, app_ref=self)
        self.rv.add(w)
        # Pastikan widget sudah terrender sebelum draw progress bar
        self.update_idletasks()
        w._tick(task.progress)
        # Redraw canvas progress bar setelah ukuran widget diketahui
        self.after(50, w._draw)

    def _open_picker(self):
        dlg = TaskPickerDialog(self)
        self.wait_window(dlg)
        # Pastikan fullscreen kembali setelah dialog tutup
        self.attributes("-fullscreen", True)
        self.lift()
        self.focus_force()
        if dlg.result:
            self._add_task(dlg.result)
            self.refresh_status()
            self.after(100, self._force_redraw_all)

    def _start_all(self):
        for w in self.rv.items():
            if w.task.progress < 100:
                w._do_start()

    def _reset_all(self):
        for w in self.rv.items():
            w._do_reset()

    def _clear_all(self):
        if messagebox.askyesno("Konfirmasi", "Hapus semua task?"):
            self.rv.clear()
            self.refresh_status()

    def refresh_status(self):
        items = self.rv.items()
        total = len(items)
        done  = sum(1 for i in items if i.task.progress >= 100)
        run   = sum(1 for i in items if i.task.running)
        antri = total - done - run
        txt = f"Total: {total}  |  Selesai: {done}  |  Berjalan: {run}  |  Antri: {antri}"
        self._sv.set(txt)
        self.lbl_summary.config(
            text=f"Selesai {done}/{total}  |  {run} berjalan"
        )


# ══════════════════════════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════════════════════════
def _pill(cv, x1, y1, x2, y2, r, fill):
    cv.create_arc(x1,     y1, x1+2*r, y2, start=90,  extent=180, fill=fill, outline="")
    cv.create_arc(x2-2*r, y1, x2,     y2, start=270, extent=180, fill=fill, outline="")
    cv.create_rectangle(x1+r, y1, x2-r, y2, fill=fill, outline="")

def _pcolor(p):
    if p < 30:   return C["err"]
    elif p < 70: return C["warn"]
    else:        return C["ok"]

def _lighten(h):
    h = h.lstrip("#")
    r, g, b = (int(h[i:i+2], 16) for i in (0, 2, 4))
    return "#{:02x}{:02x}{:02x}".format(min(r+35,255), min(g+35,255), min(b+35,255))


# ══════════════════════════════════════════════════════════════════
#  ENTRY POINT
# ══════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    app = App()
    app.mainloop()