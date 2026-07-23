"""
ui/dialogs/ota_settings.py — OTASettingsDialog
"""

import sys, os, json
_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
_LIB  = os.path.join(_ROOT, "lib")
if _LIB not in sys.path:
    sys.path.insert(0, _LIB)

import tkinter as tk
from tkinter import messagebox
from config import COLORS


class OTASettingsDialog(tk.Toplevel):
    """
    Dialog untuk memilih file firmware OTA TM81.
    Hanya mengatur fw_version di tm81_ota.json.
    Fixed params (connection, chunk_size, dll.) ada di commissioning.json["ota"].
    """

    _OTA_JSON   = os.path.join(_ROOT, "commands", "tm81", "config", "tm81_ota.json")
    _FLASH_JSON = os.path.join(_ROOT, "config", "flash.json")

    def __init__(self, parent, on_save=None):
        super().__init__(parent)
        self.title("OTA Settings")
        self.resizable(False, False)
        self.transient(parent)
        self.configure(bg=COLORS["bg"])

        self._on_save_cb = on_save
        self._ota_data   = self._load(self._OTA_JSON)
        self._flash_data = self._load(self._FLASH_JSON)
        self._fw_var     = tk.StringVar(value=self._ota_data.get("fw_version", ""))

        self._build()
        self.update_idletasks()
        x = parent.winfo_rootx() + (parent.winfo_width()  - self.winfo_width())  // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")
        self._suppress_close = False
        self.after(80, lambda: self.bind_all("<Button-1>", self._on_global_click, add="+"))

    def _on_global_click(self, event):
        if not self.winfo_exists() or self._suppress_close:
            return
        try:
            cx, cy = event.x_root, event.y_root
            dx, dy = self.winfo_rootx(), self.winfo_rooty()
            dw, dh = self.winfo_width(), self.winfo_height()
            if not (dx <= cx <= dx + dw and dy <= cy <= dy + dh):
                self.destroy()
        except Exception:
            pass

    # ------------------------------------------------------------------ I/O

    def _load(self, path: str) -> dict:
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def _save(self):
        self._ota_data["fw_version"] = self._fw_var.get().strip()
        with open(self._OTA_JSON, "w", encoding="utf-8") as f:
            json.dump(self._ota_data, f, indent=2, ensure_ascii=False)

    # ------------------------------------------------------------------ UI

    def _build(self):
        C   = COLORS
        pad = {"padx": 12, "pady": 6}

        tk.Label(self, text="OTA Settings",
                 bg=C["bg"], fg=C["text"],
                 font=("TkDefaultFont", 11, "bold")).pack(**pad)
        tk.Frame(self, height=1, bg=C["border"]).pack(fill="x", padx=12)

        card = tk.Frame(self, bg=C["card"],
                        highlightthickness=1, highlightbackground=C["border"])
        card.pack(fill="x", padx=12, pady=10)

        tk.Label(card, text="Firmware",
                 bg=C["card"], fg=C["text"],
                 font=("TkDefaultFont", 9, "bold"),
                 ).grid(row=0, column=0, columnspan=3, sticky="w", padx=8, pady=(6, 2))

        # File
        tk.Label(card, text="File:", bg=C["card"], fg=C["text"],
                 ).grid(row=1, column=0, sticky="w", padx=8, pady=2)
        fw_entry = tk.Entry(card, textvariable=self._fw_var, width=42,
                            bg=C["surface"], fg=C["text"], relief="flat",
                            insertbackground=C["text"],
                            highlightthickness=1, highlightbackground=C["border"],
                            highlightcolor=C["running"],
                            state="readonly",
                            )
        fw_entry.grid(row=1, column=1, padx=4, pady=2)
        # Scroll ke akhir agar nama file terlihat
        self._fw_var.trace_add("write", lambda *_: fw_entry.xview_moveto(1.0))

        def _browse():
            from tkinter import filedialog
            self._suppress_close = True
            # Prioritas init_dir: (1) folder file yang sudah dipilih, (2) flash_dir, (3) root
            cur = self._fw_var.get().strip()
            if cur and os.path.isabs(cur) and os.path.isdir(os.path.dirname(cur)):
                init_dir = os.path.dirname(cur)
            else:
                fw_dir   = os.path.join(_ROOT, self._flash_data.get("flash_dir", "firmware"))
                init_dir = fw_dir if os.path.isdir(fw_dir) else _ROOT
            path = filedialog.askopenfilename(
                parent=self, title="Pilih firmware OTA",
                filetypes=[("Binary", "*.bin"), ("All", "*.*")],
                initialdir=init_dir,
            )
            if path:
                # Simpan full absolute path agar test_loader bisa langsung pakai
                self._fw_var.set(os.path.normpath(os.path.abspath(path)))
            self.after(300, lambda: setattr(self, '_suppress_close', False))

        tk.Button(card, text="Browse", command=_browse,
                  bg=C["border"], fg=C["text"], relief="flat", cursor="hand2",
                  ).grid(row=1, column=2, padx=(0, 8), pady=2)

        # Buttons
        tk.Frame(self, height=1, bg=C["border"]).pack(fill="x", padx=12, pady=(4, 0))
        btn_row = tk.Frame(self, bg=C["bg"])
        btn_row.pack(fill="x", padx=12, pady=8)

        tk.Button(btn_row, text="Batal", command=self.destroy,
                  bg=C["border"], fg=C["text"], relief="flat",
                  width=8, cursor="hand2").pack(side="right", padx=(4, 0))
        tk.Button(btn_row, text="Simpan", command=self._on_save,
                  bg=C["running"], fg="white", relief="flat",
                  width=8, cursor="hand2").pack(side="right")

    def _on_save(self):
        if not self._fw_var.get().strip():
            messagebox.showwarning("File kosong",
                                   "Pilih file firmware terlebih dahulu.", parent=self)
            return
        try:
            self._save()
            self.destroy()
            if self._on_save_cb:
                self._on_save_cb()
        except Exception as e:
            messagebox.showerror("Gagal simpan", str(e), parent=self)
