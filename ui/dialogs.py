"""
ui/dialogs.py — DisplaySettingsDialog, AddTestDialog, CommissioningDialog, FlashSettingsDialog, OTASettingsDialog.
"""

import sys
import os
import json

_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
_LIB  = os.path.join(_ROOT, "lib")
if _LIB not in sys.path:
    sys.path.insert(0, _LIB)

import tkinter as tk
from tkinter import ttk, messagebox

from config import DISPLAY_PRESETS, FONT_SCALE, COLORS, BASE_FONTS
from project import module_project
from test_loader import (
    discover_tests, load_test,
    load_flash_tests, flash_module_names,
    load_voltage_tests, voltage_module_names,
    load_tm81_tests, tm81_module_names,
    load_tm81_flash_tests, tm81_flash_module_names,
)


# ============================================================================
# DisplaySettingsDialog
# ============================================================================

class DisplaySettingsDialog(tk.Toplevel):
    """Popup to change display preset or enter a custom resolution."""

    def __init__(self, parent, current_preset: str, on_apply):
        super().__init__(parent)
        self.title("Display Settings")
        self.resizable(False, False)
        self.grab_set()

        self._on_apply   = on_apply
        self._preset_var = tk.StringVar(value=current_preset)
        self._w_var      = tk.IntVar()
        self._h_var      = tk.IntVar()

        self._build()
        self._update_custom_state()
        self.update_idletasks()
        px = parent.winfo_rootx() + parent.winfo_width() // 2 - self.winfo_width() // 2
        py = parent.winfo_rooty() + parent.winfo_height() // 2 - self.winfo_height() // 2
        self.geometry(f"+{px}+{py}")

    def _build(self):
        tk.Label(self, text="Display Preset",
                 font=("TkDefaultFont", 11, "bold")).grid(
            row=0, column=0, columnspan=2, pady=(12, 6), padx=16, sticky="w"
        )
        for i, (name, _) in enumerate(DISPLAY_PRESETS.items()):
            tk.Radiobutton(
                self, text=name, variable=self._preset_var, value=name,
                command=self._update_custom_state,
            ).grid(row=i + 1, column=0, columnspan=2, sticky="w", padx=20)

        ttk.Separator(self, orient="horizontal").grid(
            row=10, column=0, columnspan=2, sticky="ew", padx=16, pady=8)

        tk.Label(self, text="Custom Width:").grid(row=11, column=0, padx=16, sticky="e")
        self._w_entry = tk.Entry(self, textvariable=self._w_var, width=6)
        self._w_entry.grid(row=11, column=1, padx=4, sticky="w")

        tk.Label(self, text="Custom Height:").grid(row=12, column=0, padx=16, sticky="e")
        self._h_entry = tk.Entry(self, textvariable=self._h_var, width=6)
        self._h_entry.grid(row=12, column=1, padx=4, sticky="w")

        btn_frame = tk.Frame(self)
        btn_frame.grid(row=13, column=0, columnspan=2, pady=12)
        tk.Button(btn_frame, text="Apply", width=10, command=self._apply,
                  bg="#2c3e50", fg="white", relief="flat").pack(side="left", padx=4)
        tk.Button(btn_frame, text="Cancel", width=10, command=self.destroy,
                  relief="flat").pack(side="left", padx=4)

    def _update_custom_state(self):
        state = "normal" if self._preset_var.get() == "Custom" else "disabled"
        self._w_entry.config(state=state)
        self._h_entry.config(state=state)

    def _apply(self):
        preset = self._preset_var.get()
        if preset == "Custom":
            w = self._w_var.get() or 800
            h = self._h_var.get() or 480
        else:
            w, h = DISPLAY_PRESETS[preset]
        self._on_apply(preset, w, h)
        self.destroy()


# ============================================================================
# AddTestDialog
# ============================================================================

class AddTestDialog(tk.Toplevel):
    """
    Picker dialog — tiap modul punya tombol Add sendiri.
    Project logic: hanya satu project (tm81/flash) aktif sekaligus.
    Universal tasks (voltage, dll.) selalu bisa ditambahkan.
    """

    def __init__(self, parent, on_add, current_project: "str | None" = None):
        super().__init__(parent)
        self.title("Add Test")
        self.resizable(False, False)
        self.grab_set()

        self._on_add          = on_add
        self._current_project = current_project
        self._modules         = discover_tests()
        self._build()
        self.update_idletasks()
        px = parent.winfo_rootx() + parent.winfo_width() // 2 - self.winfo_width() // 2
        py = parent.winfo_rooty() + parent.winfo_height() // 2 - self.winfo_height() // 2
        self.geometry(f"+{px}+{py}")

    def _btn_state(self, proj: "str | None") -> str:
        if proj is None:
            return "normal"
        if self._current_project is None or self._current_project == proj:
            return "normal"
        return "disabled"

    def _build(self):
        TYPE_COLORS = {"progress": "#3498db", "manual": "#8e44ad", "auto": "#27ae60"}
        row_idx = 0

        # Project aktif banner
        if self._current_project:
            msg = {
                "tm81":  "Project aktif: TM81  (flash / TM81 Flash tidak bisa ditambahkan)",
                "flash": "Project aktif: Flash  (tm81 / TM81 Flash tidak bisa ditambahkan)",
                "ota":   "Project aktif: TM81 Flash  (tm81 / flash tidak bisa ditambahkan)",
            }.get(self._current_project, f"Project aktif: {self._current_project}")
            tk.Label(self, text=msg, font=("TkDefaultFont", 9), fg="#888",
                     pady=4, anchor="w").grid(
                row=row_idx, column=0, columnspan=4, padx=12, sticky="ew")
            row_idx += 1
            ttk.Separator(self, orient="horizontal").grid(
                row=row_idx, column=0, columnspan=4, sticky="ew", padx=8, pady=(0, 4))
            row_idx += 1

        tk.Label(self, text="Pilih test module:",
                 font=("TkDefaultFont", 10, "bold"), pady=8).grid(
            row=row_idx, column=0, columnspan=4, padx=14, sticky="w")
        row_idx += 1

        def _row(label_text, type_tag, detail, state, cmd):
            fg = "gray" if state == "disabled" else "black"
            bg = TYPE_COLORS.get(type_tag, "#999")
            tk.Label(self, text=label_text, font=("TkDefaultFont", 10, "bold"),
                     anchor="w", width=22, fg=fg).grid(
                row=row_idx, column=0, sticky="w", padx=(12, 4), pady=4)
            tk.Label(self, text=type_tag, bg=bg, fg="white",
                     font=("TkDefaultFont", 8), padx=6, pady=2).grid(
                row=row_idx, column=1, padx=4, sticky="w")
            tk.Label(self, text=detail, font=("Courier", 9), fg="#555",
                     anchor="w", width=14).grid(
                row=row_idx, column=2, sticky="w", padx=4)
            tk.Button(self, text="+ Add", width=7, font=("TkDefaultFont", 9),
                      bg="#27ae60" if state == "normal" else "#bdc3c7",
                      fg="white", relief="flat",
                      cursor="hand2" if state == "normal" else "",
                      state=state, command=cmd).grid(
                row=row_idx, column=3, padx=(6, 12), pady=3, sticky="e")

        # Flash
        flash_names = flash_module_names()
        if flash_names:
            st = self._btn_state("flash")
            labels_str = ", ".join(n.split(":")[1] for n in flash_names)
            _row(f"Flash ({labels_str})", "progress",
                 f"{len(flash_names)} region", st, self._add_all_flash)
            row_idx += 1

        # Voltage (universal)
        volt_names = voltage_module_names()
        if volt_names:
            labels_str = ", ".join(n.split(":")[1] for n in volt_names)
            _row(f"Voltage ({labels_str})", "auto",
                 f"{len(volt_names)} entry", "normal", self._add_all_voltage)
            row_idx += 1

        # TM81
        tm81_names = tm81_module_names()
        if tm81_names:
            st = self._btn_state("tm81")
            _row(f"TM81 ({len(tm81_names)} test)", "auto",
                 f"{len(tm81_names)} entry", st, self._add_all_tm81)
            row_idx += 1

        # TM81 Flash
        tm81_flash_names = tm81_flash_module_names()
        if tm81_flash_names:
            st = self._btn_state("ota")
            _row(f"TM81 Flash ({len(tm81_flash_names)} step)", "progress",
                 f"{len(tm81_flash_names)} step", st, self._add_all_tm81_flash)
            row_idx += 1

        # Modul lainnya
        for name, label, mod in self._modules:
            mod_proj = module_project(name)
            st       = self._btn_state(mod_proj)
            ttype    = getattr(mod, "TYPE", "auto")
            cmd      = getattr(mod, "COMMAND", "?")
            _row(label, ttype, cmd, st, lambda n=name: self._add(n))
            row_idx += 1

        ttk.Separator(self, orient="horizontal").grid(
            row=row_idx, column=0, columnspan=4, sticky="ew", pady=6, padx=8)
        row_idx += 1
        tk.Button(self, text="Tutup", width=10, command=self.destroy,
                  relief="flat").grid(row=row_idx, column=0, columnspan=4, pady=(0, 10))

    def _add(self, module_name: str):
        self._on_add(load_test(module_name), module_name)

    def _add_all_flash(self):
        for item, name in zip(load_flash_tests(), flash_module_names()):
            self._on_add(item, name)

    def _add_all_voltage(self):
        for item, name in zip(load_voltage_tests(), voltage_module_names()):
            self._on_add(item, name)

    def _add_all_tm81(self):
        for item, name in zip(load_tm81_tests(), tm81_module_names()):
            self._on_add(item, name)

    def _add_all_tm81_flash(self):
        for item, name in zip(load_tm81_flash_tests(), tm81_flash_module_names()):
            self._on_add(item, name)


# ============================================================================
# CommissioningDialog
# ============================================================================

class CommissioningDialog(tk.Toplevel):
    """
    Dialog untuk mengatur parameter commissioning per batch produksi.
    Membaca dan menyimpan ke json/commissioning.json.
    """

    _JSON_PATH = os.path.join(_ROOT, "commands", "tm81", "config", "commissioning.json")

    _JOIN_MODES  = ["0 — None", "1 — ABP", "2 — OTAA"]
    _DEV_CLASSES = ["0 — Class A", "1 — Class B", "2 — Class C"]
    _COUNTER_RES = ["0 — 1 L", "1 — 10 L", "2 — 100 L"]
    _SUBMIT_IDS  = [
        "0 — 30 menit", "1 — 1 jam", "2 — 3 jam",
        "3 — 12 jam",   "4 — 1 hari", "5 — 3 hari", "6 — 7 hari",
    ]
    _MSG_TYPES   = ["0 — Unconfirmed", "1 — Confirmed"]

    def __init__(self, parent):
        super().__init__(parent)
        self.title("Commissioning Settings")
        self.resizable(False, False)
        self.grab_set()

        self._data = self._load()
        self._vars: dict[str, tk.Variable] = {}
        self._build()
        self.update_idletasks()
        px = parent.winfo_rootx() + parent.winfo_width()  // 2 - self.winfo_width()  // 2
        py = parent.winfo_rooty() + parent.winfo_height() // 2 - self.winfo_height() // 2
        self.geometry(f"+{px}+{py}")

    # ------------------------------------------------------------------ I/O

    def _load(self) -> dict:
        try:
            with open(self._JSON_PATH, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def _save(self, data: dict):
        os.makedirs(os.path.dirname(self._JSON_PATH), exist_ok=True)
        with open(self._JSON_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    # ------------------------------------------------------------------ build

    def _build(self):
        C   = COLORS
        fs  = lambda k: max(7, int(BASE_FONTS[k]))
        bg  = C["bg"]
        surf = C["surface"]
        brd  = C["border"]

        self.configure(bg=bg)

        # Title bar
        hdr = tk.Frame(self, bg=C["header_bg"], pady=8)
        hdr.pack(fill="x")
        tk.Label(hdr, text="⚙  Commissioning Settings",
                 bg=C["header_bg"], fg="white",
                 font=("TkDefaultFont", fs("label"), "bold"),
                 padx=12).pack(side="left")
        tk.Label(hdr, text="simpan ke commissioning.json",
                 bg=C["header_bg"], fg=C["sub"],
                 font=("TkDefaultFont", fs("small")), padx=8).pack(side="left")

        # Notebook (tabs)
        style = ttk.Style()
        style.configure("Comm.TNotebook",        background=bg, borderwidth=0)
        style.configure("Comm.TNotebook.Tab",    padding=[10, 4])
        nb = ttk.Notebook(self, style="Comm.TNotebook")
        nb.pack(fill="both", expand=True, padx=8, pady=8)

        d = self._data
        def _get(path: str, default):
            keys = path.split(".")
            v = d
            for k in keys:
                v = v.get(k, {}) if isinstance(v, dict) else {}
            return v if v != {} else default

        def _tab(label: str) -> tk.Frame:
            f = tk.Frame(nb, bg=bg, padx=4, pady=4)
            nb.add(f, text=f"  {label}  ")
            return f

        def _entry(parent, key: str, label: str, default,
                   width: int = 20, mono: bool = False):
            var = tk.StringVar(value=str(default))
            row = tk.Frame(parent, bg=surf)
            row.pack(fill="x", pady=2)
            tk.Label(row, text=label, bg=surf, fg=C["sub"],
                     font=("TkDefaultFont", fs("small")),
                     width=17, anchor="w").pack(side="left", padx=(8, 4))
            font = ("Courier", fs("small")) if mono else ("TkDefaultFont", fs("small"))
            tk.Entry(row, textvariable=var, width=width, font=font,
                     bg=C["card"], fg=C["text"], insertbackground=C["text"],
                     relief="flat", highlightthickness=1,
                     highlightbackground=brd,
                     highlightcolor=C["running"]).pack(side="left", padx=(0, 8), pady=4)
            self._vars[key] = var

        def _combo(parent, key: str, label: str, choices: list[str], idx: int):
            var = tk.IntVar(value=idx)
            row = tk.Frame(parent, bg=surf)
            row.pack(fill="x", pady=2)
            tk.Label(row, text=label, bg=surf, fg=C["sub"],
                     font=("TkDefaultFont", fs("small")),
                     width=17, anchor="w").pack(side="left", padx=(8, 4))
            cb = ttk.Combobox(row, values=choices, state="readonly", width=22,
                              font=("TkDefaultFont", fs("small")))
            cb.current(idx if 0 <= idx < len(choices) else 0)
            cb.pack(side="left", padx=(0, 8), pady=4)
            cb.bind("<<ComboboxSelected>>",
                    lambda e, v=var, c=cb: v.set(int(c.get().split("—")[0].strip())))
            self._vars[key] = var

        def _sep(parent, title: str):
            tk.Frame(parent, height=1, bg=brd).pack(fill="x", padx=4, pady=(8, 2))
            tk.Label(parent, text=title.upper(), bg=bg, fg=C["sub"],
                     font=("TkDefaultFont", fs("small"), "bold"),
                     padx=4, pady=2).pack(anchor="w")

        # ── Tab 1: LoRa Keys ─────────────────────────────────────────
        t1 = _tab("LoRa Keys")
        lk = tk.Frame(t1, bg=surf)
        lk.pack(fill="x", pady=2)
        _entry(lk, "dev_eui",  "DevEUI",       _get("lora_set_dev_eui.dev_eui",   "0080E10101010104"),            width=20, mono=True)
        _entry(lk, "join_eui", "JoinEUI",      _get("lora_set_join_eui.join_eui", "0000000000000001"),            width=20, mono=True)
        _entry(lk, "app_key",  "AppKey",       _get("lora_set_app_key.app_key",   "8833E75406D203F48D1F6D2CCC2815D8"), width=36, mono=True)
        _entry(lk, "nw_key",   "NwKey (ABP)",  _get("lora_set_nw_key.nw_key",     "00000000000000000000000000000001"), width=36, mono=True)
        _entry(lk, "dev_addr", "DevAddr (ABP)", _get("lora_set_dev_addr.dev_addr", 1), width=10)

        # ── Tab 2: LoRa Settings ─────────────────────────────────────
        t2 = _tab("LoRa Settings")
        ls = tk.Frame(t2, bg=surf)
        ls.pack(fill="x", pady=2)
        _combo(ls, "join_mode", "Join Mode",    self._JOIN_MODES,  _get("lora_set_join_mode.join_mode", 2))
        _combo(ls, "dev_class", "Device Class", self._DEV_CLASSES, _get("lora_set_dev_class.dev_class", 0))

        _sep(t2, "LoRa Config")
        lc = tk.Frame(t2, bg=surf)
        lc.pack(fill="x", pady=2)
        _entry(lc, "tx_power",  "TX Power",      _get("lora_set_config.tx_power",  0), width=6)
        _entry(lc, "data_rate", "Data Rate",     _get("lora_set_config.data_rate", 2), width=6)
        _entry(lc, "rx1_delay", "RX1 Delay (s)", _get("lora_set_config.rx1_delay", 2), width=6)

        # ── Tab 3: User Config ───────────────────────────────────────
        t3 = _tab("User Config")
        uc = tk.Frame(t3, bg=surf)
        uc.pack(fill="x", pady=2)
        _combo(uc, "counter_res", "Counter Res",  self._COUNTER_RES, _get("user_set_config.counter_res", 1))
        _combo(uc, "submit_id",   "Submit Rate",  self._SUBMIT_IDS,  _get("user_set_config.submit_id",  0))
        _combo(uc, "msg_type",    "Message Type", self._MSG_TYPES,   _get("user_set_config.msg_type",   1))
        _entry(uc, "timezone",        "Timezone (GMT+)",  _get("user_set_config.timezone",        7), width=6)
        _entry(uc, "initial_counter", "Initial Counter",  _get("user_set_config.initial_counter", 0), width=10)

        # ── Buttons ──────────────────────────────────────────────────
        btn_frame = tk.Frame(self, bg=bg, pady=10)
        btn_frame.pack(fill="x")
        tk.Button(btn_frame, text="Batal", width=10, command=self.destroy,
                  bg=C["surface"], fg=C["text"], relief="flat",
                  font=("TkDefaultFont", fs("button")),
                  highlightthickness=1, highlightbackground=brd,
                  cursor="hand2").pack(side="right", padx=(4, 12))
        tk.Button(btn_frame, text="Simpan", width=10, command=self._on_save,
                  bg="#27ae60", fg="white", relief="flat",
                  font=("TkDefaultFont", fs("button")),
                  cursor="hand2").pack(side="right", padx=4)

    # ------------------------------------------------------------------ save

    def _on_save(self):
        v = self._vars

        def _hex(key: str, expected_bytes: int) -> "str | None":
            raw = v[key].get().strip().replace(":", "").replace(" ", "")
            if len(raw) != expected_bytes * 2:
                return None
            try:
                int(raw, 16)
            except ValueError:
                return None
            return raw.upper()

        def _int(key: str, default: int = 0) -> int:
            try:
                return int(v[key].get().strip())
            except ValueError:
                return default

        dev_eui  = _hex("dev_eui",  8)
        join_eui = _hex("join_eui", 8)
        app_key  = _hex("app_key",  16)
        nw_key   = _hex("nw_key",   16)

        errors = []
        if dev_eui  is None: errors.append("DevEUI harus 16 karakter hex (8 bytes)")
        if join_eui is None: errors.append("JoinEUI harus 16 karakter hex (8 bytes)")
        if app_key  is None: errors.append("AppKey harus 32 karakter hex (16 bytes)")
        if nw_key   is None: errors.append("NwKey harus 32 karakter hex (16 bytes)")

        if errors:
            messagebox.showerror("Validasi gagal", "\n".join(errors), parent=self)
            return

        data = {
            "_doc": "Parameter commissioning per batch produksi. Edit sesuai kebutuhan sebelum mulai test.",
            "set_id": {
                "_doc": "Device ID diambil dari field UI (Device ID / Serial No.)",
                "device_id": "@device_id",
            },
            "lora_set_join_mode": {
                "_doc": "0=None, 1=ABP, 2=OTAA",
                "join_mode": int(v["join_mode"].get()),
            },
            "lora_set_dev_class": {
                "_doc": "0=Class A, 1=Class B, 2=Class C",
                "dev_class": int(v["dev_class"].get()),
            },
            "lora_set_dev_eui": {
                "_doc": "8 bytes hex, unik per device",
                "dev_eui": dev_eui,
            },
            "lora_set_join_eui": {
                "_doc": "8 bytes hex, sama per batch",
                "join_eui": join_eui,
            },
            "lora_set_app_key": {
                "_doc": "16 bytes hex, sama per batch (OTAA)",
                "app_key": app_key,
            },
            "lora_set_nw_key": {
                "_doc": "16 bytes hex, sama per batch (ABP NwkSKey)",
                "nw_key": nw_key,
            },
            "lora_set_dev_addr": {
                "_doc": "4-byte integer (desimal), unik per device untuk ABP",
                "dev_addr": _int("dev_addr", 1),
            },
            "lora_set_config": {
                "_doc": "tx_power: 0-5, data_rate: 0-5 (DR2=SF10), rx1_delay: detik",
                "tx_power":  _int("tx_power",  0),
                "data_rate": _int("data_rate",  2),
                "rx1_delay": _int("rx1_delay",  2),
            },
            "user_set_config": {
                "_doc": "activation: 1=ACTIVATED. counter_res: 0=1L,1=10L,2=100L. submit_id: 0=30mnt,1=1jam,...",
                "activation":      1,
                "initial_counter": _int("initial_counter", 0),
                "counter_res":     int(v["counter_res"].get()),
                "alarm":           0,
                "submit_id":       int(v["submit_id"].get()),
                "timezone":        _int("timezone", 7),
                "msg_type":        int(v["msg_type"].get()),
            },
        }

        try:
            self._save(data)
            self.destroy()
        except Exception as e:
            messagebox.showerror("Gagal simpan", str(e), parent=self)


# ============================================================================
# FlashSettingsDialog
# ============================================================================

class FlashSettingsDialog(tk.Toplevel):
    """
    Dialog untuk mengatur file firmware dan alamat flash per region.
    Membaca default dari config/flash.json, menyimpan override ke config/flash_settings.json.
    """

    _FLASH_JSON    = os.path.join(_ROOT, "config", "flash.json")
    _SETTINGS_JSON = os.path.join(_ROOT, "config", "flash_settings.json")

    def __init__(self, parent):
        super().__init__(parent)
        self.title("Flash Settings")
        self.resizable(False, False)
        self.grab_set()
        self.configure(bg=COLORS["bg"])

        self._regions  = self._load_flash_json()
        self._saved    = self._load_settings()
        self._entries  = {}   # {region_name: {"file": StringVar, "address": StringVar}}

        self._build()
        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width()  - self.winfo_width())  // 2
        y = parent.winfo_y() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")

    # ------------------------------------------------------------------
    # Load / save helpers
    # ------------------------------------------------------------------

    def _load_flash_json(self) -> list:
        try:
            with open(self._FLASH_JSON, encoding="utf-8") as f:
                return json.load(f).get("regions", [])
        except Exception:
            return []

    def _load_settings(self) -> dict:
        try:
            with open(self._SETTINGS_JSON, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def _save_settings(self, data: dict):
        os.makedirs(os.path.dirname(self._SETTINGS_JSON), exist_ok=True)
        with open(self._SETTINGS_JSON, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build(self):
        pad = {"padx": 12, "pady": 6}

        # Header
        tk.Label(
            self, text="Flash Settings",
            bg=COLORS["bg"], fg=COLORS["text"],
            font=("TkDefaultFont", 11, "bold"),
        ).pack(**pad)

        tk.Frame(self, height=1, bg=COLORS["border"]).pack(fill="x", padx=12)

        if not self._regions:
            tk.Label(
                self, text="Tidak ada region di flash.json",
                bg=COLORS["bg"], fg=COLORS["error"],
            ).pack(**pad)
            tk.Button(self, text="Tutup", command=self.destroy).pack(pady=8)
            return

        # Satu card per region
        for region in self._regions:
            name    = region.get("name", "unknown")
            label   = region.get("description", name)
            def_file = region.get("file", "")
            def_addr = region.get("address", "0x08000000")

            saved_region = self._saved.get(name, {})

            file_var = tk.StringVar(value=saved_region.get("file", def_file))
            addr_var = tk.StringVar(value=saved_region.get("address", def_addr))
            self._entries[name] = {"file": file_var, "address": addr_var}

            card = tk.Frame(self, bg=COLORS["card"],
                            highlightthickness=1,
                            highlightbackground=COLORS["border"])
            card.pack(fill="x", padx=12, pady=6)

            tk.Label(
                card, text=f"Region: {label}",
                bg=COLORS["card"], fg=COLORS["text"],
                font=("TkDefaultFont", 9, "bold"),
            ).grid(row=0, column=0, columnspan=3, sticky="w", padx=8, pady=(6, 2))

            # File firmware
            tk.Label(card, text="File:", bg=COLORS["card"],
                     fg=COLORS["text"]).grid(row=1, column=0, sticky="w", padx=8, pady=2)
            tk.Entry(
                card, textvariable=file_var, width=36,
                bg=COLORS["surface"], fg=COLORS["text"],
                relief="flat", insertbackground=COLORS["text"],
                highlightthickness=1, highlightbackground=COLORS["border"],
                highlightcolor=COLORS["running"],
            ).grid(row=1, column=1, padx=4, pady=2)

            def _browse(var=file_var):
                from tkinter import filedialog
                path = filedialog.askopenfilename(
                    parent=self,
                    title="Pilih firmware",
                    filetypes=[("Binary", "*.bin *.hex"), ("All", "*.*")],
                )
                if path:
                    var.set(path)

            tk.Button(
                card, text="Browse", command=_browse,
                bg=COLORS["border"], fg=COLORS["text"], relief="flat",
                cursor="hand2",
            ).grid(row=1, column=2, padx=(0, 8), pady=2)

            # Address
            tk.Label(card, text="Address:", bg=COLORS["card"],
                     fg=COLORS["text"]).grid(row=2, column=0, sticky="w", padx=8, pady=(2, 6))
            tk.Entry(
                card, textvariable=addr_var, width=16,
                bg=COLORS["surface"], fg=COLORS["text"],
                font=("Courier", 9),
                relief="flat", insertbackground=COLORS["text"],
                highlightthickness=1, highlightbackground=COLORS["border"],
                highlightcolor=COLORS["running"],
            ).grid(row=2, column=1, sticky="w", padx=4, pady=(2, 6))

        # Buttons
        tk.Frame(self, height=1, bg=COLORS["border"]).pack(fill="x", padx=12, pady=(8, 0))
        btn_row = tk.Frame(self, bg=COLORS["bg"])
        btn_row.pack(fill="x", padx=12, pady=8)

        tk.Button(
            btn_row, text="Batal", command=self.destroy,
            bg=COLORS["border"], fg=COLORS["text"], relief="flat",
            width=8, cursor="hand2",
        ).pack(side="right", padx=(4, 0))

        tk.Button(
            btn_row, text="Simpan", command=self._on_save,
            bg=COLORS["running"], fg="white", relief="flat",
            width=8, cursor="hand2",
        ).pack(side="right")

    def _on_save(self):
        data = {}
        for name, vars_ in self._entries.items():
            file_val = vars_["file"].get().strip()
            addr_val = vars_["address"].get().strip()

            # Validasi address format
            if addr_val and not addr_val.startswith("0x"):
                messagebox.showerror(
                    "Format salah",
                    f"Region '{name}': Address harus diawali 0x (contoh: 0x08000000)",
                    parent=self,
                )
                return

            data[name] = {
                "file":    file_val,
                "address": addr_val,
            }

        try:
            self._save_settings(data)
            self.destroy()
        except Exception as e:
            messagebox.showerror("Gagal simpan", str(e), parent=self)


# ============================================================================
# OTASettingsDialog
# ============================================================================

class OTASettingsDialog(tk.Toplevel):
    """
    Dialog ringkas untuk mengatur firmware OTA TM81.
    Membaca dan menyimpan ke commands/tm81/config/tm81_flash.json.
    """

    _JSON_PATH = os.path.join(_ROOT, "commands", "tm81", "config", "tm81_flash.json")

    def __init__(self, parent):
        super().__init__(parent)
        self.title("OTA Flash Settings")
        self.resizable(False, False)
        self.grab_set()

        self._cfg = self._load()
        self._build()

        self.update_idletasks()
        px = parent.winfo_rootx() + parent.winfo_width()  // 2 - self.winfo_width()  // 2
        py = parent.winfo_rooty() + parent.winfo_height() // 2 - self.winfo_height() // 2
        self.geometry(f"+{px}+{py}")

    # ------------------------------------------------------------------ I/O

    def _load(self) -> dict:
        try:
            with open(self._JSON_PATH, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def _save(self, cfg: dict):
        os.makedirs(os.path.dirname(self._JSON_PATH), exist_ok=True)
        with open(self._JSON_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)

    # ------------------------------------------------------------------ UI

    def _build(self):
        C  = COLORS
        fs = lambda k: max(7, int(BASE_FONTS[k]))
        self.configure(bg=C["bg"])

        # Header
        hdr = tk.Frame(self, bg=C["header_bg"], pady=8)
        hdr.pack(fill="x")
        tk.Label(hdr, text="⚙  OTA Flash Settings",
                 bg=C["header_bg"], fg="white",
                 font=("TkDefaultFont", fs("label"), "bold"),
                 padx=12).pack(side="left")
        tk.Label(hdr, text="tm81_flash.json",
                 bg=C["header_bg"], fg=C["sub"],
                 font=("TkDefaultFont", fs("small")), padx=8).pack(side="left")

        body = tk.Frame(self, bg=C["bg"], padx=14, pady=10)
        body.pack(fill="x")

        surf = C["surface"]
        brd  = C["border"]

        def _field(label: str, key: str, default: str, width: int = 32, browse: bool = False):
            row = tk.Frame(body, bg=surf, pady=2)
            row.pack(fill="x", pady=3)
            tk.Label(row, text=label, bg=surf, fg=C["sub"],
                     font=("TkDefaultFont", fs("small")),
                     width=14, anchor="w").pack(side="left", padx=(8, 4))
            var = tk.StringVar(value=str(self._cfg.get(key, default)))
            ent = tk.Entry(row, textvariable=var, width=width,
                           bg=C["card"], fg=C["text"], insertbackground=C["text"],
                           relief="flat", font=("Courier", fs("small")),
                           highlightthickness=1, highlightbackground=brd)
            ent.pack(side="left", padx=(0, 4))
            if browse:
                def _browse(_var=var):
                    from tkinter import filedialog
                    fw_dir = os.path.join(_ROOT, self._cfg.get("fw_dir", "firmware/App"))
                    path = filedialog.askopenfilename(
                        title="Pilih file firmware",
                        initialdir=fw_dir if os.path.isdir(fw_dir) else _ROOT,
                        filetypes=[("Binary", "*.bin"), ("All files", "*.*")],
                        parent=self,
                    )
                    if path:
                        _var.set(os.path.basename(path))
                tk.Button(row, text="Browse", command=_browse,
                          bg="#2980b9", fg="white", relief="flat",
                          font=("TkDefaultFont", fs("small")),
                          padx=6, cursor="hand2").pack(side="left")
            return var

        self._v_fw_dir     = _field("FW Directory", "fw_dir",     "firmware/App")
        self._v_fw_version = _field("FW Version",   "fw_version", "",            browse=True)
        self._v_connection = _field("Connection",   "connection", "ch340",  width=10)
        self._v_chunk_size = _field("Chunk Size",   "chunk_size", "512",    width=6)

        # Tests info (read-only)
        tests = self._cfg.get("tests", [])
        if tests:
            tk.Label(body, text=f"Steps ({len(tests)} langkah):",
                     bg=C["bg"], fg=C["sub"],
                     font=("TkDefaultFont", fs("small"))).pack(anchor="w", pady=(6, 0))
            for i, s in enumerate(tests):
                tk.Label(body, text=f"  {i+1}. {s.get('label', '?')}",
                         bg=C["bg"], fg=C["text"],
                         font=("TkDefaultFont", fs("small"))).pack(anchor="w")

        # Buttons
        btn_row = tk.Frame(self, bg=C["bg"])
        btn_row.pack(pady=(4, 10))
        tk.Button(btn_row, text="Simpan", width=10,
                  bg="#27ae60", fg="white", relief="flat",
                  font=("TkDefaultFont", fs("button")),
                  command=self._on_save).pack(side="left", padx=6)
        tk.Button(btn_row, text="Batal", width=8,
                  relief="flat", font=("TkDefaultFont", fs("button")),
                  command=self.destroy).pack(side="left", padx=6)

    def _on_save(self):
        cfg = dict(self._cfg)
        cfg["fw_dir"]     = self._v_fw_dir.get().strip()
        cfg["fw_version"] = self._v_fw_version.get().strip()
        cfg["connection"] = self._v_connection.get().strip()
        try:
            cfg["chunk_size"] = int(self._v_chunk_size.get().strip())
        except ValueError:
            pass
        try:
            self._save(cfg)
            self.destroy()
        except Exception as e:
            messagebox.showerror("Gagal simpan", str(e), parent=self)
