"""
test_row_widget.py - One row in the test list.
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "lib"))

import tkinter as tk
from tkinter import ttk

from test_modules import TestType, TestResult
from config import COLORS, BASE_FONTS

BADGE_COLOR = {
    TestResult.PENDING: COLORS["pending"],
    TestResult.RUNNING: COLORS["running"],
    TestResult.OK:      COLORS["ok"],
    TestResult.NG:      COLORS["ng"],
}
BADGE_TEXT = {
    TestResult.PENDING: "---",
    TestResult.RUNNING: "...",
    TestResult.OK:      "OK",
    TestResult.NG:      "NG",
}

COL_NUM   = 0
COL_TITLE = 1
COL_CMD   = 2
COL_BADGE = 3
COL_CTRL  = 4

# Minimum pixel width of the left zone in control column (progressbar / ok-ng area)
# The action button (Run/Send) always starts after this zone.
CTRL_LEFT_MINW = 155
BTN_WIDTH = 6   # character width — makes Run and Send same size


class TestRowWidget:
    def __init__(self, master, test_item, index, grid_row, scale, on_run_request):
        self.master         = master
        self.test_item      = test_item
        self.index          = index
        self.grid_row       = grid_row
        self.scale          = scale
        self.on_run_request = on_run_request
        self._bg = COLORS["row_even"] if index % 2 == 0 else COLORS["row_odd"]
        self._progress_var = tk.DoubleVar(value=0)
        self._widgets = []
        self._build()

    def _fs(self, k):
        return max(7, int(BASE_FONTS[k] * self.scale))

    def _left_minw(self):
        return int(CTRL_LEFT_MINW * self.scale)

    # ------------------------------------------------------------------ build

    def _build(self):
        bg = self._bg
        r  = self.grid_row

        kw = dict(bg=bg, padx=6, pady=5)

        n = tk.Label(self.master, text=f"{self.index+1:02d}",
                     font=("Courier", self._fs("small"), "bold"),
                     width=3, anchor="center", **kw)
        n.grid(row=r, column=COL_NUM, sticky="nsew")

        t = tk.Label(self.master, text=self.test_item.title,
                     font=("TkDefaultFont", self._fs("label"), "bold"),
                     anchor="w", **kw)
        t.grid(row=r, column=COL_TITLE, sticky="nsew")

        c = tk.Label(self.master, text=self.test_item.command,
                     font=("Courier", self._fs("small")), fg="#666",
                     anchor="w", **kw)
        c.grid(row=r, column=COL_CMD, sticky="nsew")

        self._badge_var = tk.StringVar(value=BADGE_TEXT[self.test_item.result])
        self._badge = tk.Label(self.master, textvariable=self._badge_var,
                               bg=BADGE_COLOR[self.test_item.result],
                               font=("TkDefaultFont", self._fs("button"), "bold"),
                               width=4, anchor="center", pady=5)
        self._badge.grid(row=r, column=COL_BADGE, sticky="nsew", padx=4)

        # Control frame: col 0 = left zone (fixed min-width), col 1 = action button
        self._ctrl = tk.Frame(self.master, bg=bg)
        self._ctrl.grid(row=r, column=COL_CTRL, sticky="nsew", padx=4, pady=3)
        self._ctrl.columnconfigure(0, minsize=self._left_minw())
        self._build_control()

        sep = tk.Frame(self.master, height=1, bg="#d0d0d0")
        sep.grid(row=r+1, column=COL_NUM, columnspan=5, sticky="ew")

        self._widgets = [n, t, c, self._badge, self._ctrl, sep]

    def _build_control(self):
        t = self.test_item.test_type
        if t == TestType.PROGRESS:
            self._build_progress()
        elif t == TestType.MANUAL:
            self._build_manual()
        elif t == TestType.AUTO:
            self._build_auto()

    def _action_btn(self, text, bg_color, cmd):
        """Action button with fixed width so all rows align."""
        return tk.Button(
            self._ctrl, text=text, width=BTN_WIDTH,
            font=("TkDefaultFont", self._fs("button")),
            command=cmd, bg=bg_color, fg="white",
            relief="flat", padx=4, pady=2, cursor="hand2")

    def _build_progress(self):
        pbar_len = max(60, self._left_minw() - 10)
        self._progress_bar = ttk.Progressbar(
            self._ctrl, variable=self._progress_var,
            maximum=100, length=pbar_len, mode="determinate")
        self._progress_bar.grid(row=0, column=0, sticky="w", padx=(4, 0), pady=4)

        self._run_btn = self._action_btn("Run", "#3498db", self._request_run)
        self._run_btn.grid(row=0, column=1, sticky="w", padx=(8, 0))

        # Label error (tersembunyi, muncul saat NG)
        self._error_lbl = tk.Label(
            self._ctrl, text="", bg=self._bg,
            font=("TkDefaultFont", self._fs("small")),
            fg=COLORS["ng"], anchor="w", wraplength=280)
        self._error_lbl.grid(row=1, column=0, columnspan=2, sticky="w", padx=(4, 0))

    def _build_manual(self):
        # Manual tidak butuh zona kiri lebar — reset minsize
        self._ctrl.columnconfigure(0, minsize=0)
        btn_frame = tk.Frame(self._ctrl, bg=self._bg)
        btn_frame.grid(row=0, column=0, columnspan=2, sticky="w", padx=(4, 0), pady=4)

        self._ok_btn = tk.Button(
            btn_frame, text="OK", width=4,
            font=("TkDefaultFont", self._fs("button"), "bold"),
            command=lambda: self._manual_result(TestResult.OK),
            bg=COLORS["ok"], fg="white", relief="flat",
            padx=4, pady=2, cursor="hand2", state="disabled")
        self._ok_btn.pack(side="left", padx=(0, 6))

        self._ng_btn = tk.Button(
            btn_frame, text="NG", width=4,
            font=("TkDefaultFont", self._fs("button"), "bold"),
            command=lambda: self._manual_result(TestResult.NG),
            bg=COLORS["ng"], fg="white", relief="flat",
            padx=4, pady=2, cursor="hand2", state="disabled")
        self._ng_btn.pack(side="left")

    def _build_auto(self):
        self._status_lbl = tk.Label(
            self._ctrl, text="Waiting",
            bg=self._bg, font=("TkDefaultFont", self._fs("small")), fg="#888")
        self._status_lbl.grid(row=0, column=0, sticky="w", padx=(8, 0), pady=4)

        self._run_btn = self._action_btn("Run", "#27ae60", self._request_run)
        self._run_btn.grid(row=0, column=1, sticky="w", padx=(8, 0))

    # ------------------------------------------------------------------ state

    def set_running(self):
        self.test_item.result = TestResult.RUNNING
        self._update_badge()
        t = self.test_item.test_type
        if t == TestType.PROGRESS:
            self._progress_var.set(0)
            self._run_btn.config(state="disabled")
        elif t == TestType.MANUAL:
            self._ok_btn.config(state="disabled")
            self._ng_btn.config(state="disabled")
        elif t == TestType.AUTO:
            self._status_lbl.config(text="Running...", fg=COLORS["running"])
            self._run_btn.config(state="disabled")

    def set_result(self, result, error: str = ""):
        self.test_item.result = result
        if error:
            self.test_item.last_error = error
        self._update_badge()
        t = self.test_item.test_type
        if t == TestType.PROGRESS:
            self._progress_var.set(100 if result == TestResult.OK else 0)
            self._run_btn.config(state="normal")
            if result == TestResult.NG and (error or self.test_item.last_error):
                self._error_lbl.config(text=error or self.test_item.last_error)
            else:
                self._error_lbl.config(text="")
        elif t == TestType.MANUAL:
            pass  # tidak ada action button di manual
        elif t == TestType.AUTO:
            if result == TestResult.OK:
                self._status_lbl.config(text="OK", fg=COLORS["ok"])
            else:
                msg = error or self.test_item.last_error or "NG"
                self._status_lbl.config(text=msg, fg=COLORS["ng"])
            self._run_btn.config(state="normal")

    def advance_progress(self, percent):
        self._progress_var.set(min(percent, 100))

    def enable_manual_buttons(self):
        print(f"[widget] enable_manual_buttons: {self.test_item.title} type={self.test_item.test_type}", flush=True)
        if self.test_item.test_type == TestType.MANUAL:
            self._ok_btn.config(state="normal")
            self._ng_btn.config(state="normal")
            print(f"[widget] OK/NG buttons enabled for {self.test_item.title}", flush=True)
        else:
            print(f"[widget] SKIP — bukan MANUAL", flush=True)

    def reset(self):
        self.test_item.reset()
        self._update_badge()
        t = self.test_item.test_type
        if t == TestType.PROGRESS:
            self._progress_var.set(0)
            self._error_lbl.config(text="")
            self._run_btn.config(state="normal")
        elif t == TestType.MANUAL:
            self._ok_btn.config(state="disabled")
            self._ng_btn.config(state="disabled")
        elif t == TestType.AUTO:
            self._status_lbl.config(text="Waiting", fg="#888")
            self._run_btn.config(state="normal")

    def destroy(self):
        for w in self._widgets:
            w.destroy()

    def _update_badge(self):
        r = self.test_item.result
        self._badge_var.set(BADGE_TEXT[r])
        self._badge.config(bg=BADGE_COLOR[r])

    def _request_run(self):
        self.on_run_request(self)

    def _manual_result(self, result):
        print(f"[widget] _manual_result: {self.test_item.title} -> {result}", flush=True)
        self.set_result(result)
        self._ok_btn.config(state="disabled")
        self._ng_btn.config(state="disabled")
