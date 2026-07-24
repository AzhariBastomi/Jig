"""
ui/debug_console_manager.py — Mengelola window-window DebugConsole.

Diambil dari main.py.App, yang tadinya menyimpan dict self._debug_consoles dan
menaruh semua logic buka/fokus/tutup/menu langsung sebagai method App (bagian
dari God Object). DebugConsoleManager berdiri sendiri: App hanya perlu compose
satu instance dan panggil method publiknya — App tidak perlu tahu detail
window-tracking atau layout grid-nya.
"""

import json
import os
import sys
import tkinter as tk

_UI_DIR = os.path.dirname(os.path.abspath(__file__))
if _UI_DIR not in sys.path:
    sys.path.insert(0, _UI_DIR)

from debug_console import DebugConsole

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_APP_CONFIG_JSON = os.path.join(_ROOT, "config", "config.json")

# Grid layout window: 2 kolom, 868x348 per window (termasuk gap).
_WIN_W, _WIN_H, _COLS = 868, 348, 2

_EXTRA_WINDOWS = {
    "all":          ("Debug — All Logs",    ""),
    "commands":     ("Debug — TM81 Cmd",    "commands"),
    "flash":        ("Debug — Flash",       "flash"),
    "test_loader":  ("Debug — Test Loader", "test_loader"),
}


class DebugConsoleManager:
    """Buka/fokus/tutup satu atau lebih window DebugConsole, identitas per key."""

    def __init__(self, root, on_change=None):
        self._root      = root                 # App (Tk root) — parent utk Toplevel
        self._consoles: dict = {}
        self._on_change = on_change            # dipanggil tiap window dibuka/ditutup

    # ------------------------------------------------------------------ query

    def has_any_open(self) -> bool:
        return any(w.winfo_exists() for w in self._consoles.values())

    @staticmethod
    def load_config() -> dict:
        try:
            with open(_APP_CONFIG_JSON, encoding="utf-8") as f:
                return json.load(f).get("debug", {})
        except Exception:
            return {}

    @staticmethod
    def _read_serial_connections() -> dict:
        try:
            with open(_APP_CONFIG_JSON, encoding="utf-8") as f:
                return json.load(f).get("serial", {}).get("connections", {})
        except Exception:
            return {}

    # ------------------------------------------------------------------ actions

    def open_or_focus(self, key: str, title: str, name_filter: str = "",
                       level: str = "DEBUG", offset: tuple = None):
        existing = self._consoles.get(key)
        if existing and existing.winfo_exists():
            existing.lift()
            return existing

        win = DebugConsole(self._root, min_level=level, title=title, name_filter=name_filter)
        if offset:
            try:
                mx = self._root.winfo_rootx() + offset[0]
                my = self._root.winfo_rooty() + offset[1]
                win.geometry(f"+{mx}+{my}")
            except Exception:
                pass

        self._consoles[key] = win
        self._notify()

        orig_close = win._on_close

        def _on_close_hook(k=key, fn=orig_close):
            fn()
            self._consoles.pop(k, None)
            self._notify()

        win.protocol("WM_DELETE_WINDOW", _on_close_hook)
        return win

    def maybe_autostart(self):
        """Buka window debug otomatis saat startup jika config debug.enabled = 1."""
        cfg = self.load_config()
        if not cfg.get("enabled", 0):
            return
        level        = cfg.get("level", "DEBUG")
        serial_conns = self._read_serial_connections()

        grid_col, grid_row = 0, 0

        def _next_pos():
            nonlocal grid_col, grid_row
            pos = (40 + grid_col * _WIN_W, 40 + grid_row * _WIN_H)
            grid_col += 1
            if grid_col >= _COLS:
                grid_col = 0
                grid_row += 1
            return pos

        # 1. Satu window per serial connection (auto dari config.json)
        for conn_name, conn_def in serial_conns.items():
            desc  = conn_def.get("description", conn_name)
            key   = f"serial.{conn_name}"
            title = f"Debug — {conn_name.upper()}  ({desc})"
            self.open_or_focus(key, title, name_filter=f"serial_comm.{conn_name}",
                                level=level, offset=_next_pos())

        # 2. Window tambahan dari debug.windows (misal "all", "commands")
        for wid in cfg.get("windows", []):
            if wid in _EXTRA_WINDOWS:
                title, nf = _EXTRA_WINDOWS[wid]
                self.open_or_focus(wid, title, name_filter=nf, level=level,
                                    offset=_next_pos())

    def build_menu(self, anchor_btn):
        """Bangun & tampilkan menu popup pilihan window debug, anchor ke tombol."""
        menu = tk.Menu(self._root, tearoff=0,
                       bg="#161b22", fg="#c9d1d9",
                       activebackground="#264f78", activeforeground="white",
                       font=("Consolas", 9))
        cfg          = self.load_config()
        level        = cfg.get("level", "DEBUG")
        serial_conns = self._read_serial_connections()

        if serial_conns:
            menu.add_command(label="── Serial ports ──", state="disabled")
        for conn_name, conn_def in serial_conns.items():
            desc   = conn_def.get("description", conn_name)
            key    = f"serial.{conn_name}"
            title  = f"Debug — {conn_name.upper()}  ({desc})"
            nf     = f"serial_comm.{conn_name}"
            active = key in self._consoles and self._consoles[key].winfo_exists()
            prefix = "✓ " if active else "  "
            menu.add_command(
                label=f"{prefix}{conn_name.upper()}  —  {desc}",
                command=lambda k=key, t=title, f=nf, lv=level:
                    self.open_or_focus(k, t, f, lv),
            )

        menu.add_separator()
        extras = [
            ("all",         "All logs",       ""),
            ("commands",    "TM81 commands",  "commands"),
            ("flash",       "Flash / STM32",  "flash"),
            ("test_loader", "Test loader",    "test_loader"),
        ]
        for key, label, nf in extras:
            active = key in self._consoles and self._consoles[key].winfo_exists()
            prefix = "✓ " if active else "  "
            menu.add_command(
                label=f"{prefix}{label}",
                command=lambda k=key, t=f"Debug — {label}", f=nf, lv=level:
                    self.open_or_focus(k, t, f, lv),
            )
        try:
            menu.tk_popup(anchor_btn.winfo_rootx(),
                          anchor_btn.winfo_rooty() + anchor_btn.winfo_height())
        finally:
            menu.grab_release()

    # ------------------------------------------------------------------ internals

    def _notify(self):
        if self._on_change:
            self._on_change()
