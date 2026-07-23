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
    Dialog untuk mengatur file firmware dan alamat flash per region.
    Baca dan tulis langsung ke config/flash.json.
    """

    _FLASH_JSON = os.path.join(_ROOT, "config", "flash.json")

    def __init__(self, parent):
        super().__init__(parent)
        self.title("Flash Settings")
        self.resizable(False, False)
        self.grab_set()
        self.configure(bg=COLORS["bg"])

        self._flash_data = self._load()
        self._regions    = self._flash_data.get("regions", [])
        self._entries    = {}   # {region_name: {"file": StringVar, "address": StringVar}}

        self._build()
        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width()  - self.winfo_width())  // 2
        y = parent.winfo_y() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")

    # ------------------------------------------------------------------ I/O

    def _load(self) -> dict:
        try:
            with open(self._FLASH_JSON, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def _save(self, data: dict):
        with open(self._FLASH_JSON, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    # ------------------------------------------------------------------ UI

    def _build(self):
        C   = COLORS
        pad = {"padx": 12, "pady": 6}

        tk.Label(self, text="Flash Settings",
                 bg=C["bg"], fg=C["text"],
                 font=("TkDefaultFont", 11, "bold")).pack(**pad)
        tk.Frame(self, height=1, bg=C["border"]).pack(fill="x", padx=12)

        if not self._regions:
            tk.Label(self, text="Tidak ada region di flash.json",
                     bg=C["bg"], fg=C.get("error", "red")).pack(**pad)
            tk.Button(self, text="Tutup", command=self.destroy).pack(pady=8)
            return

        for region in self._regions:
            name     = region.get("name", "unknown")
            label    = region.get("description", name)
            def_file = region.get("file", "")
            def_addr = region.get("address", "0x08000000")

            file_var = tk.StringVar(value=def_file)
            addr_var = tk.StringVar(value=def_addr)
            self._entries[name] = {"file": file_var, "address": addr_var}

            card = tk.Frame(self, bg=C["card"],
                            highlightthickness=1, highlightbackground=C["border"])
            card.pack(fill="x", padx=12, pady=6)

            tk.Label(card, text=f"Region: {label}",
                     bg=C["card"], fg=C["text"],
                     font=("TkDefaultFont", 9, "bold"),
                     ).grid(row=0, column=0, columnspan=3, sticky="w", padx=8, pady=(6, 2))

            # File
            tk.Label(card, text="File:", bg=C["card"], fg=C["text"],
                     ).grid(row=1, column=0, sticky="w", padx=8, pady=2)
            tk.Entry(card, textvariable=file_var, width=36,
                     bg=C["surface"], fg=C["text"], relief="flat",
                     insertbackground=C["text"],
                     highlightthickness=1, highlightbackground=C["border"],
                     highlightcolor=C["running"],
                     ).grid(row=1, column=1, padx=4, pady=2)

            def _browse(var=file_var):
                from tkinter import filedialog
                flash_dir = os.path.join(_ROOT, self._flash_data.get("flash_dir", "firmware"))
                path = filedialog.askopenfilename(
                    parent=self, title="Pilih firmware",
                    filetypes=[("Binary", "*.bin *.hex"), ("All", "*.*")],
                    initialdir=flash_dir if os.path.isdir(flash_dir) else _ROOT,
                )
                if path:
                    var.set(path)

            tk.Button(card, text="Browse", command=_browse,
                      bg=C["border"], fg=C["text"], relief="flat", cursor="hand2",
                      ).grid(row=1, column=2, padx=(0, 8), pady=2)

            # Address
            tk.Label(card, text="Address:", bg=C["card"], fg=C["text"],
                     ).grid(row=2, column=0, sticky="w", padx=8, pady=(2, 6))
            tk.Entry(card, textvariable=addr_var, width=16,
                     bg=C["surface"], fg=C["text"], font=("Courier", 9),
                     relief="flat", insertbackground=C["text"],
                     highlightthickness=1, highlightbackground=C["border"],
                     highlightcolor=C["running"],
                     ).grid(row=2, column=1, sticky="w", padx=4, pady=(2, 6))

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
        # Validasi address
        for name, vars_ in self._entries.items():
            addr_val = vars_["address"].get().strip()
            if addr_val and not addr_val.startswith("0x"):
                messagebox.showerror(
                    "Format salah",
                    f"Region '{name}': Address harus diawali 0x (contoh: 0x08000000)",
                    parent=self)
                return

        # Update file & address langsung ke flash_data["regions"]
        for region in self._flash_data.get("regions", []):
            name = region.get("name", "")
            if name in self._entries:
                region["file"]    = self._entries[name]["file"].get().strip()
                region["address"] = self._entries[name]["address"].get().strip()

        try:
            self._save(self._flash_data)
            self.destroy()
        except Exception as e:
            messagebox.showerror("Gagal simpan", str(e), parent=self)
