"""
ui/dialogs/display_settings.py — DisplaySettingsDialog
"""

import sys, os
_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ))
_LIB  = os.path.join(_ROOT, "lib")
if _LIB not in sys.path:
    sys.path.insert(0, _LIB)

import tkinter as tk
from tkinter import ttk
from config import DISPLAY_PRESETS


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
