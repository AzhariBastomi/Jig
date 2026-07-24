"""
ui/test_list_panel.py — Scrollable list of TestRowWidgets.
"""

import sys
import os

_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
_LIB  = os.path.join(_ROOT, "lib")
if _LIB not in sys.path:
    sys.path.insert(0, _LIB)

import tkinter as tk
from tkinter import ttk

from config import COLORS
from ui.test_row_widget import TestRowWidget


class TestListPanel(tk.Frame):
    """Scrollable list of TestRowWidgets."""

    def __init__(self, parent, scale: float, controller, **kwargs):
        super().__init__(parent, **kwargs)
        self.scale      = scale
        self.controller = controller
        self._rows: list[TestRowWidget] = []
        self._build()

    def _build(self):
        container = tk.Frame(self)
        container.pack(fill="both", expand=True)

        self._canvas    = tk.Canvas(container, bg=COLORS["bg"], highlightthickness=0)
        self._scrollbar = ttk.Scrollbar(container, orient="vertical",
                                        command=self._canvas.yview)
        self._canvas.configure(yscrollcommand=self._auto_scrollbar)
        self._canvas.pack(fill="both", expand=True)

        self._inner  = tk.Frame(self._canvas, bg=COLORS["bg"])
        self._window = self._canvas.create_window((0, 0), window=self._inner, anchor="nw")

        self._inner.bind("<Configure>",  self._on_frame_configure)
        self._canvas.bind("<Configure>", self._on_canvas_configure)
        self._canvas.bind_all("<MouseWheel>", self._on_mousewheel)

    def _auto_scrollbar(self, first, last):
        if float(first) <= 0.0 and float(last) >= 1.0:
            self._scrollbar.pack_forget()
        else:
            self._scrollbar.pack(side="right", fill="y")
            self._canvas.pack(side="left", fill="both", expand=True)
        self._scrollbar.set(first, last)

    def _on_frame_configure(self, event=None):
        self._canvas.configure(scrollregion=self._canvas.bbox("all"))

    def _on_canvas_configure(self, event):
        self._canvas.itemconfig(self._window, width=event.width)

    def _on_mousewheel(self, event):
        self._canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def load_tests(self, tests: list):
        for w in self._inner.winfo_children():
            w.destroy()
        self._rows.clear()
        tk.Frame(self._inner, bg=COLORS["bg"], height=int(6 * self.scale)).pack()
        for i, item in enumerate(tests):
            row = TestRowWidget(
                self._inner, item, i,
                scale=self.scale,
                on_run_request=self._on_run_request,
            )
            self._rows.append(row)

    def get_rows(self) -> list:
        return self._rows

    def reset_all(self):
        for row in self._rows:
            row.reset()

    def refresh_validations(self):
        """Panggil ulang validate_fn tiap row (mis. saat context device_id berubah)
        agar tombol Run ikut ter-enable/disable secara real-time."""
        for row in self._rows:
            row.refresh_validation()

    def scroll_to_row(self, row: TestRowWidget):
        self._inner.update_idletasks()
        try:
            row_y    = row.frame.winfo_y()
            total_h  = self._inner.winfo_height()
            canvas_h = self._canvas.winfo_height()
            if total_h <= canvas_h:
                return
            target_y = row_y - canvas_h * 0.3
            fraction = max(0.0, min(1.0, target_y / (total_h - canvas_h)))
            self._canvas.yview_moveto(fraction)
        except Exception:
            pass

    def _on_run_request(self, row: TestRowWidget):
        self.controller.run_test(row)
