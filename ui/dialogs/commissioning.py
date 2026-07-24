"""
ui/dialogs/commissioning.py — CommissioningDialog
"""

import sys, os, json
_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
_LIB  = os.path.join(_ROOT, "lib")
if _LIB not in sys.path:
    sys.path.insert(0, _LIB)

import tkinter as tk
from tkinter import ttk, messagebox
from config import COLORS, BASE_FONTS


class CommissioningDialog(tk.Toplevel):
    """
    Dialog untuk mengatur parameter commissioning per batch produksi.
    Menyimpan ke commands/tm81/config/commissioning.json.
    """

    _JSON_PATH = os.path.join(_ROOT, "commands", "tm81", "config", "commissioning.json")

    _JOIN_MODES  = ["None", "ABP", "OTAA"]
    _DEV_CLASSES = ["Class A", "Class B", "Class C"]
    _COUNTER_RES = ["1 L", "10 L", "100 L"]
    _SUBMIT_IDS  = ["30 menit", "1 jam", "3 jam", "12 jam", "1 hari", "3 hari", "7 hari"]
    _MSG_TYPES   = ["Unconfirmed", "Confirmed"]
    _TIMEZONES   = ["WIB (GMT+7)", "WITA (GMT+8)", "WIT (GMT+9)"]
    _TZ_VALUES   = [7, 8, 9]

    def __init__(self, parent, on_save=None):
        super().__init__(parent)
        self.title("Commissioning Settings")
        self.resizable(False, False)
        self.grab_set()

        self._on_save_cb = on_save
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
        C    = COLORS
        fs   = lambda k: max(7, int(BASE_FONTS[k]))
        bg   = C["bg"]
        surf = C["surface"]
        brd  = C["border"]

        self.configure(bg=bg)

        hdr = tk.Frame(self, bg=C["header_bg"], pady=8)
        hdr.pack(fill="x")
        tk.Label(hdr, text="⚙  Commissioning Settings",
                 bg=C["header_bg"], fg="white",
                 font=("TkDefaultFont", fs("label"), "bold"),
                 padx=12).pack(side="left")
        tk.Label(hdr, text="simpan ke commissioning.json",
                 bg=C["header_bg"], fg=C["sub"],
                 font=("TkDefaultFont", fs("small")), padx=8).pack(side="left")

        style = ttk.Style()
        style.configure("Comm.TNotebook",     background=bg, borderwidth=0)
        style.configure("Comm.TNotebook.Tab", padding=[10, 4])
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

        def _entry(parent, key, label, default, width=20, mono=False):
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

        def _combo(parent, key, label, choices, idx):
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
                    lambda e, v=var, c=cb, ch=choices: v.set(ch.index(c.get())))
            self._vars[key] = var

        def _combo_val(parent, key, label, choices, values, current_value):
            """Combo yang menyimpan nilai aktual (values[i]), bukan index-nya —
            dipakai saat urutan pilihan tidak sama dengan 0,1,2,... (mis. timezone 7/8/9)."""
            idx = values.index(current_value) if current_value in values else 0
            var = tk.IntVar(value=values[idx])
            row = tk.Frame(parent, bg=surf)
            row.pack(fill="x", pady=2)
            tk.Label(row, text=label, bg=surf, fg=C["sub"],
                     font=("TkDefaultFont", fs("small")),
                     width=17, anchor="w").pack(side="left", padx=(8, 4))
            cb = ttk.Combobox(row, values=choices, state="readonly", width=22,
                              font=("TkDefaultFont", fs("small")))
            cb.current(idx)
            cb.pack(side="left", padx=(0, 8), pady=4)
            cb.bind("<<ComboboxSelected>>",
                    lambda e, v=var, c=cb, ch=choices, vals=values: v.set(vals[ch.index(c.get())]))
            self._vars[key] = var

        def _sep(parent, title):
            tk.Frame(parent, height=1, bg=brd).pack(fill="x", padx=4, pady=(8, 2))
            tk.Label(parent, text=title.upper(), bg=bg, fg=C["sub"],
                     font=("TkDefaultFont", fs("small"), "bold"),
                     padx=4, pady=2).pack(anchor="w")

        t1 = _tab("LoRa Keys")
        lk = tk.Frame(t1, bg=surf)
        lk.pack(fill="x", pady=2)
        _entry(lk, "dev_eui",  "DevEUI",        _get("lora_set_dev_eui.dev_eui",   "0080E10101010104"),             width=20, mono=True)
        _entry(lk, "join_eui", "JoinEUI",       _get("lora_set_join_eui.join_eui", "0000000000000001"),             width=20, mono=True)
        _entry(lk, "app_key",  "AppKey",        _get("lora_set_app_key.app_key",   "8833E75406D203F48D1F6D2CCC2815D8"), width=36, mono=True)
        _entry(lk, "nw_key",   "NwKey (ABP)",   _get("lora_set_nw_key.nw_key",     "00000000000000000000000000000001"), width=36, mono=True)
        _entry(lk, "dev_addr", "DevAddr (ABP)", _get("lora_set_dev_addr.dev_addr", "0x0100000B"), width=12, mono=True)

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

        t3 = _tab("User Config")
        uc = tk.Frame(t3, bg=surf)
        uc.pack(fill="x", pady=2)
        _combo(uc, "counter_res",  "Counter Res",   self._COUNTER_RES, _get("user_set_config.counter_res", 1))
        _combo(uc, "submit_id",    "Submit Rate",   self._SUBMIT_IDS,  _get("user_set_config.submit_id",  0))
        _combo(uc, "msg_type",     "Message Type",  self._MSG_TYPES,   _get("user_set_config.msg_type",   1))
        _combo_val(uc, "timezone", "Timezone", self._TIMEZONES, self._TZ_VALUES,
                   _get("user_set_config.timezone", 7))
        _entry(uc, "initial_counter", "Initial Counter", _get("user_set_config.initial_counter", 0), width=10)

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

        def _hex(key, expected_bytes):
            raw = v[key].get().strip().replace(":", "").replace(" ", "")
            if len(raw) != expected_bytes * 2:
                return None
            try:
                int(raw, 16)
            except ValueError:
                return None
            return raw.upper()

        def _int(key, default=0):
            try:
                return int(v[key].get().strip())
            except ValueError:
                return default

        dev_eui  = _hex("dev_eui",  8)
        join_eui = _hex("join_eui", 8)
        app_key  = _hex("app_key",  16)
        nw_key   = _hex("nw_key",   16)

        # DevAddr: terima "0x..." atau plain hex string → simpan sebagai "0xXXXXXXXX"
        try:
            _da_raw = v["dev_addr"].get().strip().replace(" ", "")
            if _da_raw.lower().startswith("0x"):
                dev_addr_int = int(_da_raw, 16)
            else:
                dev_addr_int = int(_da_raw, 16)
            dev_addr_str = f"0x{dev_addr_int:08X}"
        except (ValueError, AttributeError):
            dev_addr_int = None
            dev_addr_str = None

        errors = []
        if dev_eui      is None: errors.append("DevEUI harus 16 karakter hex (8 bytes)")
        if join_eui     is None: errors.append("JoinEUI harus 16 karakter hex (8 bytes)")
        if app_key      is None: errors.append("AppKey harus 32 karakter hex (16 bytes)")
        if nw_key       is None: errors.append("NwKey harus 32 karakter hex (16 bytes)")
        if dev_addr_str is None: errors.append("DevAddr harus hex 8 digit (contoh: 0x0100000B)")
        if errors:
            messagebox.showerror("Validasi gagal", "\n".join(errors), parent=self)
            return

        data = {
            "_doc": "Parameter commissioning per batch produksi.",
            "set_id": {"_doc": "Device ID dari field UI", "device_id": "@device_id"},
            "lora_set_join_mode":  {"_doc": "0=None,1=ABP,2=OTAA",             "join_mode":  int(v["join_mode"].get())},
            "lora_set_dev_class":  {"_doc": "0=ClassA,1=ClassB,2=ClassC",      "dev_class":  int(v["dev_class"].get())},
            "lora_set_dev_eui":    {"_doc": "8 bytes hex, unik per device",     "dev_eui":    dev_eui},
            "lora_set_join_eui":   {"_doc": "8 bytes hex, sama per batch",      "join_eui":   join_eui},
            "lora_set_app_key":    {"_doc": "16 bytes hex, OTAA",               "app_key":    app_key},
            "lora_set_nw_key":     {"_doc": "16 bytes hex, ABP NwkSKey",        "nw_key":     nw_key},
            "lora_set_dev_addr":   {"_doc": "hex string 4-byte, ABP",           "dev_addr":   dev_addr_str},
            "lora_set_config":     {"_doc": "tx_power/data_rate/rx1_delay",
                                    "tx_power": _int("tx_power", 0), "data_rate": _int("data_rate", 2), "rx1_delay": _int("rx1_delay", 2)},
            "user_set_config":     {"_doc": "counter_res/submit_id/timezone/msg_type",
                                    "activation": 1, "initial_counter": _int("initial_counter", 0),
                                    "counter_res": int(v["counter_res"].get()), "alarm": 0,
                                    "submit_id": int(v["submit_id"].get()), "timezone": int(v["timezone"].get()),
                                    "msg_type": int(v["msg_type"].get())},
        }

        try:
            self._save(data)
            self.destroy()
            if self._on_save_cb:
                self._on_save_cb()
        except Exception as e:
            messagebox.showerror("Gagal simpan", str(e), parent=self)
