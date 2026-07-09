"""
ui/dialogs.py — DisplaySettingsDialog dan AddTestDialog.
"""

import sys
import os

_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
_LIB  = os.path.join(_ROOT, "lib")
if _LIB not in sys.path:
    sys.path.insert(0, _LIB)

import tkinter as tk
from tkinter import ttk

from config import DISPLAY_PRESETS, FONT_SCALE
from project import module_project
from test_loader import (
    discover_tests, load_test,
    load_flash_tests, flash_module_names,
    load_voltage_tests, voltage_module_names,
    load_tm81_tests, tm81_module_names,
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
                "tm81":  "Project aktif: TM81  (flash tidak bisa ditambahkan)",
                "flash": "Project aktif: Flash  (tm81 tidak bisa ditambahkan)",
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
