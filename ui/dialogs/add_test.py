"""
ui/dialogs/add_test.py — AddTestDialog
"""

import sys, os
_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
_LIB  = os.path.join(_ROOT, "lib")
if _LIB not in sys.path:
    sys.path.insert(0, _LIB)

import tkinter as tk
from tkinter import ttk
from project import module_project
from test_loader import (
    discover_tests, load_test,
    flash_project_names, flash_project_label, flash_module_names,
    load_flash_tests_named,
    load_voltage_tests,   voltage_module_names,
    load_tm81_tests,      tm81_module_names,      tm81_label,
    load_tm81_ota_tests,  tm81_ota_module_names,  tm81_ota_label,
    load_bexa_tests,      bexa_module_names,      bexa_label,
)


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
        self.transient(parent)   # tetap di atas parent, tapi klik luar tidak diblokir

        self._on_add          = on_add
        self._current_project = current_project
        self._modules         = discover_tests()
        self._build()
        self.update_idletasks()
        px = parent.winfo_rootx() + parent.winfo_width() // 2 - self.winfo_width() // 2
        py = parent.winfo_rooty() + parent.winfo_height() // 2 - self.winfo_height() // 2
        self.geometry(f"+{px}+{py}")
        # Delay sedikit agar klik tombol yang membuka dialog ini tidak langsung menutupnya
        self.after(80, lambda: self.bind_all("<Button-1>", self._on_global_click, add="+"))

    def _on_global_click(self, event):
        """Tutup dialog saat klik di luar batas dialog."""
        if not self.winfo_exists():
            return
        try:
            cx, cy = event.x_root, event.y_root
            dx, dy = self.winfo_rootx(), self.winfo_rooty()
            dw, dh = self.winfo_width(), self.winfo_height()
            if not (dx <= cx <= dx + dw and dy <= cy <= dy + dh):
                self.destroy()
        except Exception:
            pass

    def _btn_state(self, proj: "str | None") -> str:
        if proj is None:
            return "normal"
        if self._current_project is None or self._current_project == proj:
            return "normal"
        return "disabled"

    def _build(self):
        TYPE_COLORS = {"progress": "#3498db", "manual": "#8e44ad", "auto": "#27ae60"}
        row_idx = 0

        if self._current_project:
            msg = {
                "tm81":  "Project aktif: TM81  (flash / OTA / BEXA tidak bisa ditambahkan)",
                "flash": "Project aktif: Flash  (tm81 / OTA / BEXA tidak bisa ditambahkan)",
                "ota":   "Project aktif: TM81 OTA  (tm81 / flash / BEXA tidak bisa ditambahkan)",
                "bexa":  "Project aktif: BEXA  (tm81 / flash / OTA tidak bisa ditambahkan)",
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

        for proj_name in flash_project_names():
            names = flash_module_names(proj_name)
            if names:
                st  = self._btn_state("flash")
                lbl = flash_project_label(proj_name)
                _row(f"Flash {lbl} ({len(names)} region)", "progress",
                     f"{len(names)} region", st,
                     lambda p=proj_name: self._add_all_flash(p))
                row_idx += 1

        volt_names = voltage_module_names()
        if volt_names:
            labels_str = ", ".join(n.split(":")[1] for n in volt_names)
            _row(f"Voltage ({labels_str})", "auto",
                 f"{len(volt_names)} entry", "normal", self._add_all_voltage)
            row_idx += 1

        tm81_names = tm81_module_names()
        if tm81_names:
            st  = self._btn_state("tm81")
            lbl = tm81_label()
            _row(f"{lbl} ({len(tm81_names)} test)", "auto",
                 f"{len(tm81_names)} entry", st, self._add_all_tm81)
            row_idx += 1

        # TM81 OTA — label derive dari nama file JSON
        tm81_ota_names = tm81_ota_module_names()
        if tm81_ota_names:
            st = self._btn_state("ota")
            lbl = tm81_ota_label()
            _row(f"{lbl} ({len(tm81_ota_names)} step)", "progress",
                 f"{len(tm81_ota_names)} step", st, self._add_all_tm81_ota)
            row_idx += 1

        # BEXA — via Bluetooth SPP
        bexa_names = bexa_module_names()
        if bexa_names:
            st  = self._btn_state("bexa")
            lbl = bexa_label()
            _row(f"{lbl} ({len(bexa_names)} test)", "auto",
                 f"{len(bexa_names)} entry", st, self._add_all_bexa)
            row_idx += 1

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
        self.destroy()

    def _add_all_flash(self, proj_name: str):
        for item, name in load_flash_tests_named(proj_name):
            self._on_add(item, name)
        self.destroy()

    def _add_all_voltage(self):
        for item, name in zip(load_voltage_tests(), voltage_module_names()):
            self._on_add(item, name)
        self.destroy()

    def _add_all_tm81(self):
        for item, name in zip(load_tm81_tests(), tm81_module_names()):
            self._on_add(item, name)
        self.destroy()

    def _add_all_tm81_ota(self):
        for item, name in zip(load_tm81_ota_tests(), tm81_ota_module_names()):
            self._on_add(item, name)
        self.destroy()

    def _add_all_bexa(self):
        for item, name in zip(load_bexa_tests(), bexa_module_names()):
            self._on_add(item, name)
        self.destroy()
