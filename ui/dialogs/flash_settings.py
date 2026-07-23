"""
ui/dialogs/flash_settings.py — FlashSettingsDialog
"""

import sys, os, json
_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
_LIB  = os.path.join(_ROOT, "lib")
if _LIB not in sys.path:
    sys.path.insert(0, _LIB)

import tkinter as tk
from tkinter import messagebox
from config import COLORS


class FlashSettingsDialog(tk.Toplevel):
    """
    Dialog untuk memilih file firmware per region.
    Hanya menampilkan field 'file' — address diatur langsung di flash.json.
    Detect flash project dari module names yang aktif (flash:proj:region).
    Browse mengingat direktori terakhir per region.
    """

    _FLASH_JSON = os.path.join(_ROOT, "config", "flash.json")

    def __init__(self, parent, flash_project: str = None, on_save=None):
        super().__init__(parent)
        self.title("Flash Settings")
        self.resizable(False, False)
        self.transient(parent)
        self.configure(bg=COLORS["bg"])

        self._proj_name  = flash_project or ""
        self._on_save_cb = on_save
        self._flash_data = self._load()
        self._regions    = (
            self._flash_data.get("projects", {})
                            .get(self._proj_name, {})
                            .get("regions", [])
        )
        self._entries = {}   # {region_name: StringVar(file)}

        self._build()
        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width()  - self.winfo_width())  // 2
        y = parent.winfo_y() + (parent.winfo_height() - self.winfo_height()) // 2
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

    def _load(self) -> dict:
        try:
            with open(self._FLASH_JSON, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def _save(self):
        # Update file per region di project yang aktif
        regions = (
            self._flash_data.setdefault("projects", {})
                            .setdefault(self._proj_name, {})
                            .setdefault("regions", [])
        )
        for region in regions:
            name = region.get("name", "")
            if name in self._entries:
                region["file"] = self._entries[name].get().strip()

        with open(self._FLASH_JSON, "w", encoding="utf-8") as f:
            json.dump(self._flash_data, f, indent=2, ensure_ascii=False)

    # ------------------------------------------------------------------ UI

    def _build(self):
        C   = COLORS
        pad = {"padx": 12, "pady": 6}

        proj_label = (
            self._flash_data.get("projects", {})
                            .get(self._proj_name, {})
                            .get("label", self._proj_name.upper())
        )
        tk.Label(self, text=f"Flash Settings — {proj_label}",
                 bg=C["bg"], fg=C["text"],
                 font=("TkDefaultFont", 11, "bold")).pack(**pad)
        tk.Frame(self, height=1, bg=C["border"]).pack(fill="x", padx=12)

        if not self._regions:
            tk.Label(self, text="Tidak ada region untuk project ini.",
                     bg=C["bg"], fg=C.get("error", "red")).pack(**pad)
            tk.Button(self, text="Tutup", command=self.destroy).pack(pady=8)
            return

        flash_dir = os.path.join(_ROOT, self._flash_data.get("flash_dir", "firmware"))

        for region in self._regions:
            name     = region.get("name", "unknown")
            label    = region.get("description", name)
            cur_file = region.get("file", "").strip()

            file_var = tk.StringVar(value=cur_file)
            self._entries[name] = file_var

            card = tk.Frame(self, bg=C["card"],
                            highlightthickness=1, highlightbackground=C["border"])
            card.pack(fill="x", padx=12, pady=6)

            tk.Label(card, text=f"Region: {label}",
                     bg=C["card"], fg=C["text"],
                     font=("TkDefaultFont", 9, "bold"),
                     ).grid(row=0, column=0, columnspan=3, sticky="w", padx=8, pady=(6, 2))

            tk.Label(card, text="File:", bg=C["card"], fg=C["text"],
                     ).grid(row=1, column=0, sticky="w", padx=8, pady=(2, 8))
            tk.Entry(card, textvariable=file_var, width=36,
                     bg=C["surface"], fg=C["text"], relief="flat",
                     insertbackground=C["text"],
                     highlightthickness=1, highlightbackground=C["border"],
                     highlightcolor=C["running"],
                     ).grid(row=1, column=1, padx=4, pady=(2, 8))

            def _browse(var=file_var):
                from tkinter import filedialog
                # Suppress auto-close selama filedialog terbuka
                self._suppress_close = True
                cur = var.get().strip()
                if cur and os.path.isabs(cur) and os.path.isdir(os.path.dirname(cur)):
                    init_dir = os.path.dirname(cur)
                elif cur and os.path.isdir(os.path.join(flash_dir, os.path.dirname(cur))):
                    init_dir = os.path.join(flash_dir, os.path.dirname(cur))
                else:
                    init_dir = flash_dir if os.path.isdir(flash_dir) else _ROOT
                path = filedialog.askopenfilename(
                    parent=self, title="Pilih firmware",
                    filetypes=[("Binary", "*.bin *.hex"), ("All", "*.*")],
                    initialdir=init_dir,
                )
                if path:
                    var.set(path)
                # Resume auto-close setelah delay singkat
                self.after(300, lambda: setattr(self, '_suppress_close', False))

            tk.Button(card, text="Browse", command=_browse,
                      bg=C["border"], fg=C["text"], relief="flat", cursor="hand2",
                      ).grid(row=1, column=2, padx=(0, 8), pady=(2, 8))

        # Buttons
        tk.Frame(self, height=1, bg=C["border"]).pack(fill="x", padx=12, pady=(8, 0))
        btn_row = tk.Frame(self, bg=C["bg"])
        btn_row.pack(fill="x", padx=12, pady=8)

        tk.Button(btn_row, text="Batal", command=self.destroy,
                  bg=C["border"], fg=C["text"], relief="flat",
                  width=8, cursor="hand2").pack(side="right", padx=(4, 0))
        tk.Button(btn_row, text="Simpan", command=self._on_save,
                  bg=C["running"], fg="white", relief="flat",
                  width=8, cursor="hand2").pack(side="right")

    def _on_save(self):
        try:
            self._save()
            if self._on_save_cb:
                self._on_save_cb()
            self.destroy()
        except Exception as e:
            messagebox.showerror("Gagal simpan", str(e), parent=self)
