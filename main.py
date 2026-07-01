"""
main.py — Test Point Application entry point.

Run:
    python main.py

Architecture
------------
  App          — root window, display-size settings, top bar
  TestListPanel — scrollable list of TestRowWidget (Tkinter RecycleView equivalent)
  TestController — orchestrates running tests, manages serial communication
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "lib"))

# Pastikan stdout tidak di-buffer agar debug print langsung muncul
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(line_buffering=True)
    except Exception:
        pass

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import threading
import json

from config import (
    DISPLAY_PRESETS, DEFAULT_PRESET, FONT_SCALE, BASE_FONTS,
    COLORS, ROW_HEIGHT,
)

from test_modules import TestItem, TestType, TestResult
from test_loader import (discover_tests, load_test,
                         load_flash_tests, flash_module_names,
                         load_voltage_tests, voltage_module_names,
                         load_tm81_tests, tm81_module_names)
from test_row_widget import TestRowWidget


# ============================================================================
# TestController
# ============================================================================

class TestController:
    """
    Orchestrates running individual tests or all tests in sequence.
    Communicates with serial_manager and updates the row widgets.
    """

    def __init__(self):
        self._serial       = None
        self._seq_running  = False   # True hanya saat sequential runner aktif

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def is_seq_running(self) -> bool:
        return self._seq_running

    def run_test(self, row: TestRowWidget, done_callback=None):
        """Run a single test row."""
        item = row.test_item
        row.set_running()

        # Jika modul punya run_fn sendiri, eksekusi langsung (bypass serial)
        if item.run_fn is not None:
            self._run_with_fn(row, done_callback)
            return

        t = item.test_type
        if t == TestType.PROGRESS:
            self._run_progress(row, done_callback)
        elif t == TestType.MANUAL:
            self._run_manual(row, done_callback)
        elif t == TestType.AUTO:
            self._run_auto(row, done_callback)

    def _run_with_fn(self, row: TestRowWidget, done_callback):
        """Jalankan run_fn() di thread, update UI setelah selesai."""
        item = row.test_item

        # Hubungkan progress bar ke row widget jika test mendukung
        def _progress(pct):
            row.master.after(0, lambda p=pct: row.advance_progress(p))

        # Set progress callback ke instance test (jika class-based)
        fn = item.run_fn
        if hasattr(fn, '__self__') and hasattr(fn.__self__, 'set_progress_cb'):
            fn.__self__.set_progress_cb(_progress)

        def worker():
            try:
                resp = item.run_fn()
            except Exception as e:
                import traceback
                traceback.print_exc()
                resp = f"NG:{e}"
            resp   = str(resp).strip()
            is_ok  = resp.upper() == "OK"
            result = TestResult.OK if is_ok else TestResult.NG
            error  = ""
            if not is_ok and ":" in resp:
                error = resp.split(":", 1)[1].strip()
            row.master.after(0, lambda r=result, e=error: _finish(r, e))

        def _finish(result, error=""):
            row.set_result(result, error)
            if done_callback:
                done_callback(row)

        threading.Thread(target=worker, daemon=True).start()

    def run_all(self, rows: list[TestRowWidget], done_callback=None):
        """Run all rows sequentially in a background thread."""
        if self._seq_running:
            return
        threading.Thread(
            target=self._seq_worker, args=(rows, done_callback), daemon=True
        ).start()

    def stop_seq(self):
        """Hentikan sequential runner setelah test yang sedang berjalan selesai."""
        self._seq_running = False

    def reset_all(self, rows: list[TestRowWidget]):
        self._seq_running = False
        for row in rows:
            row.reset()

    # ------------------------------------------------------------------
    # Progress test
    # ------------------------------------------------------------------

    def _run_progress(self, row: TestRowWidget, done_callback):
        item    = row.test_item
        steps   = item.steps
        step_ms = item.step_ms
        step    = [0]

        def tick():
            step[0] += 1
            pct = (step[0] / steps) * 90
            row.advance_progress(pct)
            if step[0] < steps:
                row.master.after(step_ms, tick)
            else:
                self._serial.send_command(
                    item.command,
                    callback=lambda resp: _finish(resp),
                    error_callback=lambda e: _finish("NG"),
                )

        def _finish(resp: str):
            result = TestResult.OK if resp.strip().upper() == "OK" else TestResult.NG
            row.advance_progress(100)
            row.set_result(result)
            if done_callback:
                done_callback(row)

        row.master.after(0, tick)

    # ------------------------------------------------------------------
    # Manual test
    # ------------------------------------------------------------------

    def _run_manual(self, row: TestRowWidget, done_callback):
        print(f"[manual] _run_manual: {row.test_item.title}", flush=True)

        def _poll():
            if row.test_item.is_done():
                print(f"[manual] done: {row.test_item.title} -> {row.test_item.result}", flush=True)
                if done_callback:
                    done_callback(row)
            else:
                row.master.after(200, _poll)

        def _show_buttons():
            print(f"[manual] enable buttons: {row.test_item.title}", flush=True)
            row.enable_manual_buttons()
            row.master.after(200, _poll)

        row.master.after(0, _show_buttons)

    # ------------------------------------------------------------------
    # Auto test
    # ------------------------------------------------------------------

    def _run_auto(self, row: TestRowWidget, done_callback):
        item = row.test_item

        def _on_response(resp: str):
            result = TestResult.OK if resp.strip().upper() == "OK" else TestResult.NG
            row.set_result(result)
            if done_callback:
                done_callback(row)

        self._serial.send_command(
            item.command,
            callback=_on_response,
            error_callback=lambda e: row.set_result(TestResult.NG),
        )

    # ------------------------------------------------------------------
    # Sequential runner
    # ------------------------------------------------------------------

    def _seq_worker(self, rows: list[TestRowWidget], done_callback):
        """
        Jalankan setiap row satu per satu.
        - Berhenti jika result NG.
        - Manual test: tunggu tanpa batas (operator klik OK/NG).
        - Auto / Progress: timeout 120 detik.
        """
        self._seq_running = True
        last_row = None

        for row in rows:
            if not self._seq_running:
                break
            if row.test_item.is_done():
                continue

            last_row = row
            is_manual = (row.test_item.test_type == TestType.MANUAL)

            event = threading.Event()
            row.master.after(
                0,
                lambda r=row, ev=event: self.run_test(
                    r, done_callback=lambda _r, ev=ev: ev.set()
                )
            )

            # Manual: tunggu operator tanpa batas waktu
            # Lainnya: max 120 detik (cukup untuk flash STM32)
            event.wait(timeout=None if is_manual else 120)

            # Berhenti jika NG atau seq dihentikan
            if not self._seq_running or row.test_item.result == TestResult.NG:
                self._seq_running = False
                break

        self._seq_running = False
        master = last_row.master if last_row else rows[0].master if rows else None
        if done_callback and master:
            master.after(0, lambda: done_callback(None))


# ============================================================================
# TestListPanel
# ============================================================================

class TestListPanel(tk.Frame):
    """
    Scrollable list of TestRowWidgets — Tkinter's answer to RecycleView.
    """

    def __init__(self, parent, scale: float, controller: TestController, **kwargs):
        super().__init__(parent, **kwargs)
        self.scale      = scale
        self.controller = controller
        self._rows: list[TestRowWidget] = []

        self._build()

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def _build(self):
        container = tk.Frame(self)
        container.pack(fill="both", expand=True)

        self._canvas = tk.Canvas(container, bg=COLORS["bg"], highlightthickness=0)
        scrollbar    = ttk.Scrollbar(container, orient="vertical", command=self._canvas.yview)
        self._canvas.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side="right", fill="y")
        self._canvas.pack(side="left", fill="both", expand=True)

        self._inner  = tk.Frame(self._canvas, bg=COLORS["bg"])
        self._window = self._canvas.create_window((0, 0), window=self._inner, anchor="nw")

        self._inner.bind("<Configure>", self._on_frame_configure)
        self._canvas.bind("<Configure>", self._on_canvas_configure)
        self._canvas.bind_all("<MouseWheel>", self._on_mousewheel)

    def _on_frame_configure(self, event=None):
        self._canvas.configure(scrollregion=self._canvas.bbox("all"))

    def _on_canvas_configure(self, event):
        self._canvas.itemconfig(self._window, width=event.width)

    def _on_mousewheel(self, event):
        self._canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def load_tests(self, tests: list[TestItem]):
        """Populate the list with a set of test items."""
        for w in self._inner.winfo_children():
            w.destroy()
        self._rows.clear()

        # Kolom bersama — header dan semua rows pakai grid yang sama
        self._inner.columnconfigure(0, minsize=40)    # #
        self._inner.columnconfigure(1, weight=2)      # title
        self._inner.columnconfigure(2, weight=1)      # command
        self._inner.columnconfigure(3, minsize=55)    # badge
        self._inner.columnconfigure(4, weight=1)      # control

        # ── Header row (baris 0 di _inner) ────────────────────────────
        fs_h = max(7, int(BASE_FONTS["small"] * self.scale))
        hdr_kw = dict(bg=COLORS["header_bg"], fg=COLORS["header_fg"],
                      font=("TkDefaultFont", fs_h, "bold"),
                      anchor="w", padx=6, pady=5)

        for col, text in [(0, "#"), (1, "Test Name"), (2, "Command"),
                          (3, "Result"), (4, "Control")]:
            tk.Label(self._inner, text=text, **hdr_kw).grid(
                row=0, column=col, sticky="ew")

        # Separator bawah header
        tk.Frame(self._inner, height=1, bg="#4a6278").grid(
            row=1, column=0, columnspan=5, sticky="ew")

        # ── Test rows mulai baris 2 ────────────────────────────────────
        for i, item in enumerate(tests):
            row = TestRowWidget(
                self._inner, item, i,
                grid_row=2 + i * 2,
                scale=self.scale,
                on_run_request=self._on_run_request,
            )
            self._rows.append(row)

    def get_rows(self) -> list[TestRowWidget]:
        return self._rows

    def reset_all(self):
        self.controller.reset_all(self._rows)

    # ------------------------------------------------------------------

    def _on_run_request(self, row: TestRowWidget):
        self.controller.run_test(row)


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

    def _build(self):
        tk.Label(self, text="Display Preset", font=("TkDefaultFont", 11, "bold")).grid(
            row=0, column=0, columnspan=2, pady=(12, 6), padx=16, sticky="w"
        )

        for i, (name, _) in enumerate(DISPLAY_PRESETS.items()):
            rb = tk.Radiobutton(
                self, text=name, variable=self._preset_var, value=name,
                command=self._update_custom_state,
            )
            rb.grid(row=i + 1, column=0, columnspan=2, sticky="w", padx=20)

        sep = ttk.Separator(self, orient="horizontal")
        sep.grid(row=10, column=0, columnspan=2, sticky="ew", padx=16, pady=8)

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
        is_custom = self._preset_var.get() == "Custom"
        state = "normal" if is_custom else "disabled"
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
    Bisa add module yang sama berkali-kali.
    """

    def __init__(self, parent, on_add):
        super().__init__(parent)
        self.title("Add Test")
        self.resizable(False, False)
        self.grab_set()

        self._on_add  = on_add
        self._modules = discover_tests()
        self._build()

    def _build(self):
        TYPE_COLORS = {"progress": "#3498db", "manual": "#8e44ad", "auto": "#27ae60"}

        tk.Label(self, text="Pilih test module:",
                 font=("TkDefaultFont", 10, "bold"), pady=8
                 ).grid(row=0, column=0, columnspan=4, padx=14, sticky="w")

        # ── Baris Flash (expand semua region dari flash.json) ──────────
        flash_names = flash_module_names()
        if flash_names:
            n_regions = len(flash_names)
            labels_str = ", ".join(n.split(":")[1] for n in flash_names)
            tk.Label(self, text=f"Flash ({labels_str})",
                     font=("TkDefaultFont", 10, "bold"), anchor="w", width=22
                     ).grid(row=1, column=0, sticky="w", padx=(12, 4), pady=4)
            tk.Label(self, text="progress",
                     bg=TYPE_COLORS["progress"], fg="white",
                     font=("TkDefaultFont", 8), padx=6, pady=2
                     ).grid(row=1, column=1, padx=4, sticky="w")
            tk.Label(self, text=f"{n_regions} region",
                     font=("Courier", 9), fg="#555", anchor="w", width=14
                     ).grid(row=1, column=2, sticky="w", padx=4)
            tk.Button(self, text="+ Add", width=7,
                      font=("TkDefaultFont", 9),
                      bg="#27ae60", fg="white", relief="flat",
                      cursor="hand2",
                      command=self._add_all_flash
                      ).grid(row=1, column=3, padx=(6, 12), pady=3, sticky="e")

        # ── Baris Voltage (expand semua entry dari voltage.json) ──────
        volt_names = voltage_module_names()
        if volt_names:
            n_volt     = len(volt_names)
            volt_labels = ", ".join(n.split(":")[1] for n in volt_names)
            tk.Label(self, text=f"Voltage ({volt_labels})",
                     font=("TkDefaultFont", 10, "bold"), anchor="w", width=22
                     ).grid(row=2, column=0, sticky="w", padx=(12, 4), pady=4)
            tk.Label(self, text="auto",
                     bg=TYPE_COLORS["auto"], fg="white",
                     font=("TkDefaultFont", 8), padx=6, pady=2
                     ).grid(row=2, column=1, padx=4, sticky="w")
            tk.Label(self, text=f"{n_volt} entry",
                     font=("Courier", 9), fg="#555", anchor="w", width=14
                     ).grid(row=2, column=2, sticky="w", padx=4)
            tk.Button(self, text="+ Add", width=7,
                      font=("TkDefaultFont", 9),
                      bg="#27ae60", fg="white", relief="flat",
                      cursor="hand2",
                      command=self._add_all_voltage
                      ).grid(row=2, column=3, padx=(6, 12), pady=3, sticky="e")

        # ── Baris TM81 (expand semua test dari tm81_test.json) ────────
        tm81_names = tm81_module_names()
        if tm81_names:
            n_tm81 = len(tm81_names)
            tk.Label(self, text=f"TM81 ({n_tm81} test)",
                     font=("TkDefaultFont", 10, "bold"), anchor="w", width=22
                     ).grid(row=3, column=0, sticky="w", padx=(12, 4), pady=4)
            tk.Label(self, text="auto",
                     bg=TYPE_COLORS["auto"], fg="white",
                     font=("TkDefaultFont", 8), padx=6, pady=2
                     ).grid(row=3, column=1, padx=4, sticky="w")
            tk.Label(self, text=f"{n_tm81} entry",
                     font=("Courier", 9), fg="#555", anchor="w", width=14
                     ).grid(row=3, column=2, sticky="w", padx=4)
            tk.Button(self, text="+ Add", width=7,
                      font=("TkDefaultFont", 9),
                      bg="#27ae60", fg="white", relief="flat",
                      cursor="hand2",
                      command=self._add_all_tm81
                      ).grid(row=3, column=3, padx=(6, 12), pady=3, sticky="e")

        # ── Modul lainnya ──────────────────────────────────────────────
        offset = 4  # baris flash=1, voltage=2, tm81=3
        for i, (name, label, mod) in enumerate(self._modules):
            r = i + offset
            ttype = getattr(mod, "TYPE", "auto")
            cmd   = getattr(mod, "COMMAND", "?")

            tk.Label(self, text=label,
                     font=("TkDefaultFont", 10, "bold"), anchor="w", width=22
                     ).grid(row=r, column=0, sticky="w", padx=(12, 4), pady=4)

            tk.Label(self, text=ttype,
                     bg=TYPE_COLORS.get(ttype, "#999"), fg="white",
                     font=("TkDefaultFont", 8), padx=6, pady=2
                     ).grid(row=r, column=1, padx=4, sticky="w")

            tk.Label(self, text=cmd,
                     font=("Courier", 9), fg="#555", anchor="w", width=14
                     ).grid(row=r, column=2, sticky="w", padx=4)

            tk.Button(self, text="+ Add", width=7,
                      font=("TkDefaultFont", 9),
                      bg="#27ae60", fg="white", relief="flat",
                      cursor="hand2",
                      command=lambda n=name: self._add(n)
                      ).grid(row=r, column=3, padx=(6, 12), pady=3, sticky="e")

        n_rows = len(self._modules) + offset
        ttk.Separator(self, orient="horizontal").grid(
            row=n_rows, column=0, columnspan=4, sticky="ew", pady=6, padx=8)
        tk.Button(self, text="Tutup", width=10, command=self.destroy,
                  relief="flat"
                  ).grid(row=n_rows+1, column=0, columnspan=4, pady=(0, 10))

    def _add(self, module_name: str):
        item = load_test(module_name)
        self._on_add(item, module_name)

    def _add_all_flash(self):
        """Tambahkan semua region flash dari flash.json sebagai task terpisah."""
        items = load_flash_tests()
        names = flash_module_names()
        for item, name in zip(items, names):
            self._on_add(item, name)

    def _add_all_voltage(self):
        """Tambahkan semua entry voltage dari voltage.json sebagai task terpisah."""
        items = load_voltage_tests()
        names = voltage_module_names()
        for item, name in zip(items, names):
            self._on_add(item, name)

    def _add_all_tm81(self):
        """Tambahkan semua test TM81 dari tm81_test.json sebagai task terpisah."""
        items = load_tm81_tests()
        names = tm81_module_names()
        for item, name in zip(items, names):
            self._on_add(item, name)


# ============================================================================
# App (main window)
# ============================================================================

class App(tk.Tk):

    def __init__(self):
        super().__init__()
        self.title("Test Point")
        self.configure(bg=COLORS["bg"])

        # Tangkap exception dari Tkinter callback agar muncul di terminal
        self.report_callback_exception = self._on_tk_error

        self._preset       = DEFAULT_PRESET
        self._scale        = FONT_SCALE[DEFAULT_PRESET]
        self._test_names   : list[str]      = []
        self._tests        : list[TestItem] = []
        self._station      : str            = ""

        self._controller   = TestController()

        self._load_tasks()

        # Auto-connect + scan port saat startup
        self.after(500, self._auto_connect)

        w, h = DISPLAY_PRESETS[DEFAULT_PRESET]
        self.geometry(f"{w}x{h}")
        self.minsize(320, 240)

        self._build()

    # ------------------------------------------------------------------
    # Tkinter error handler — cetak ke terminal agar mudah debug
    # ------------------------------------------------------------------

    def _on_tk_error(self, exc_type, exc_val, exc_tb):
        import traceback
        print("\n[ERROR] Exception dalam Tkinter callback:", flush=True)
        traceback.print_exception(exc_type, exc_val, exc_tb)

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def _build(self):
        # ── Top bar ──────────────────────────────────────────────────
        top = tk.Frame(self, bg=COLORS["header_bg"], pady=4)
        top.pack(fill="x")

        fs = lambda k: max(7, int(BASE_FONTS[k] * self._scale))

        tk.Label(
            top, text="Test Point", bg=COLORS["header_bg"], fg="white",
            font=("TkDefaultFont", fs("title"), "bold"),
        ).pack(side="left", padx=10)

        tk.Button(
            top, text="⚙ Display", command=self._open_display_settings,
            bg=COLORS["header_bg"], fg="white", relief="flat",
            font=("TkDefaultFont", fs("button")), cursor="hand2",
        ).pack(side="right", padx=6)

        tk.Button(
            top, text="+ Add Test", command=self._open_add_test,
            bg="#27ae60", fg="white", relief="flat",
            font=("TkDefaultFont", fs("button")), cursor="hand2",
        ).pack(side="right", padx=6)

        # ── Input area ───────────────────────────────────────────────
        inp_frame = tk.Frame(self, bg=COLORS["bg"], pady=6)
        inp_frame.pack(fill="x", padx=10)

        tk.Label(
            inp_frame, text="Device ID / Serial No.:",
            bg=COLORS["bg"], font=("TkDefaultFont", fs("label")),
        ).pack(side="left")

        self._device_var = tk.StringVar()
        tk.Entry(
            inp_frame, textvariable=self._device_var,
            font=("TkDefaultFont", fs("label")), width=20,
        ).pack(side="left", padx=6)

        tk.Label(
            inp_frame, text="Station:",
            bg=COLORS["bg"], font=("TkDefaultFont", fs("label")),
        ).pack(side="left", padx=(12, 0))

        self._station_var = tk.StringVar(value=self._station)
        self._station_var.trace_add("write", self._on_station_change)
        tk.Entry(
            inp_frame, textvariable=self._station_var,
            font=("TkDefaultFont", fs("label")), width=28,
        ).pack(side="left", padx=6)

        # ── Action bar ───────────────────────────────────────────────
        act_frame = tk.Frame(self, bg=COLORS["bg"], pady=4)
        act_frame.pack(fill="x", padx=10)

        # Container Start/Stop — posisi tetap, hanya isinya yang swap
        _toggle = tk.Frame(act_frame, bg=COLORS["bg"])
        _toggle.pack(side="left")

        self._start_btn = tk.Button(
            _toggle, text="▶  Start",
            command=self._start_all,
            bg="#2980b9", fg="white", relief="flat",
            font=("TkDefaultFont", fs("button")),
            padx=10, pady=4, cursor="hand2",
        )
        self._start_btn.pack()

        self._stop_btn = tk.Button(
            _toggle, text="⏹  Stop",
            command=self._stop_seq,
            bg="#e67e22", fg="white", relief="flat",
            font=("TkDefaultFont", fs("button")),
            padx=10, pady=4, cursor="hand2",
        )
        # Stop tidak di-pack dulu

        # Separator visual
        tk.Frame(act_frame, width=1, bg="#cccccc").pack(side="left", fill="y",
                                                        padx=8, pady=4)

        tk.Button(
            act_frame, text="↺  Reset",
            command=self._reset_all,
            bg="#7f8c8d", fg="white", relief="flat",
            font=("TkDefaultFont", fs("button")),
            padx=8, pady=4, cursor="hand2",
        ).pack(side="left", padx=(0, 4))

        tk.Button(
            act_frame, text="🗑  Clear",
            command=self._clear_all,
            bg="#c0392b", fg="white", relief="flat",
            font=("TkDefaultFont", fs("button")),
            padx=8, pady=4, cursor="hand2",
        ).pack(side="left")

        # Status label
        self._status_var = tk.StringVar(value="Ready")
        tk.Label(
            act_frame, textvariable=self._status_var,
            bg=COLORS["bg"], font=("TkDefaultFont", fs("small")),
            fg="#555555",
        ).pack(side="right")

        # ── Test list ────────────────────────────────────────────────
        self._list_panel = TestListPanel(
            self, scale=self._scale, controller=self._controller,
            bg=COLORS["bg"],
        )
        self._list_panel.pack(fill="both", expand=True, padx=10, pady=(0, 8))
        self._list_panel.load_tests(self._tests)

        # ── Status bar (bottom) ───────────────────────────────────────
        status_bar = tk.Frame(self, bg="#dde", pady=2)
        status_bar.pack(fill="x", side="bottom")

        self._conn_label = tk.Label(
            status_bar,
            text="⏳ Mencari port...",
            bg="#dde", fg="#555",
            font=("TkDefaultFont", fs("small")),
        )
        self._conn_label.pack(side="left", padx=8)

        self._port_label = tk.Label(
            status_bar, text="",
            bg="#dde", fg="#555",
            font=("TkDefaultFont", fs("small")),
        )
        self._port_label.pack(side="left", padx=(0, 8))

    # ------------------------------------------------------------------
    # Sequential run
    # ------------------------------------------------------------------

    def _start_all(self):
        rows = self._list_panel.get_rows()
        if not rows:
            return

        # Reset semua dulu sebelum mulai
        self._list_panel.reset_all()
        self._status_var.set("Running…")

        # Tampilkan Stop, sembunyikan Start
        self._start_btn.pack_forget()
        self._stop_btn.pack(side="left")

        self._controller.run_all(rows, done_callback=self._on_seq_done)

    def _stop_seq(self):
        self._controller.stop_seq()
        self._status_var.set("Dihentikan")

    def _on_seq_done(self, _):
        """Dipanggil dari main thread saat sequential runner selesai."""
        # Cek apakah ada yang NG
        rows = self._list_panel.get_rows()
        ng_rows = [r for r in rows if r.test_item.result == TestResult.NG]
        ok_rows = [r for r in rows if r.test_item.result == TestResult.OK]

        if ng_rows:
            ng_names = ", ".join(r.test_item.title for r in ng_rows)
            self._status_var.set(f"STOP — NG: {ng_names}")
        elif len(ok_rows) == len(rows):
            self._status_var.set("✓ Semua test PASS")
        else:
            self._status_var.set("Selesai")

        # Kembalikan tombol ke kondisi awal
        self._stop_btn.pack_forget()
        self._start_btn.pack(side="left")

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _auto_connect(self):
        """
        Scan semua koneksi dari config.json, coba connect tiap-tiap port.
        App tetap berjalan meski ada yang tidak terpasang.
        """
        def _do():
            import serial_manager as sm
            import serial.tools.list_ports as lp

            # Ambil semua port yang ada
            try:
                all_ports = list(lp.comports())
            except Exception:
                all_ports = []

            def find_port(device_name: str) -> str:
                """Cari COM port yang cocok dengan device_name."""
                kw = device_name.lower()
                for p in all_ports:
                    if (kw in (p.description or "").lower() or
                            kw in (p.manufacturer or "").lower() or
                            kw in (p.product or "").lower()):
                        return p.device
                return ""

            # Coba connect setiap koneksi yang didefinisikan di config.json
            results = {}   # {name: {"port": str, "ok": bool}}
            for name, cfg in sm._CONN_DEFS.items():
                dev_name  = cfg.get("device_name", "")
                found     = find_port(dev_name)
                ok        = False
                try:
                    ok = sm.connect(name)
                except Exception as e:
                    print(f"[serial] connect({name!r}) error: {e}")
                results[name] = {"port": found, "ok": ok}
                status = f"OK [{found}]" if ok else f"NG (cari: {dev_name!r})"
                print(f"[serial] {name}: {status}")

            self.after(0, lambda r=results: self._update_conn_label(r))

        threading.Thread(target=_do, daemon=True).start()

    def _update_conn_label(self, results: dict):
        """Tampilkan status semua koneksi di status bar."""
        if not hasattr(self, "_conn_label"):
            return
        parts = []
        any_ok = False
        for name, info in results.items():
            if info["ok"]:
                port_str = f" [{info['port']}]" if info["port"] else ""
                parts.append(f"● {name}{port_str}")
                any_ok = False
        for name, info in results.items():
            if info["ok"]:
                port_str = f" [{info['port']}]" if info["port"] else ""
                parts.append(f"\u25cf {name}{port_str}")
                any_ok = True
            else:
                parts.append(f"\u2717 {name}")
        text = "  |  ".join(parts) if parts else "\u2717 Tidak ada port"
        fg   = "#27ae60" if any_ok else "red"
        self._conn_label.config(text=text, fg=fg)

    def _on_station_change(self, *_):
        self._station = self._station_var.get()
        self._save_tasks()

    def _reset_all(self):
        self._controller.stop_seq()
        self._list_panel.reset_all()
        self._status_var.set("Ready")
        if hasattr(self, "_stop_btn"):
            self._stop_btn.pack_forget()
            self._start_btn.pack(side="left")

    def _open_display_settings(self):
        DisplaySettingsDialog(self, self._preset, on_apply=self._apply_display)

    def _apply_display(self, preset: str, width: int, height: int):
        self._preset = preset
        self._scale  = FONT_SCALE.get(preset, 1.0)
        self.geometry(f"{width}x{height}")
        for child in self.winfo_children():
            child.destroy()
        self._build()
        self._list_panel.load_tests(self._tests)

    def _open_add_test(self):
        AddTestDialog(self, on_add=self._add_test)

    def _add_test(self, item, module_name: str = ""):
        self._tests.append(item)
        self._test_names.append(module_name)
        self._list_panel.load_tests(self._tests)
        self._save_tasks()

    def _clear_all(self):
        if not self._tests:
            return
        from tkinter import messagebox
        if messagebox.askyesno("Clear All", "Hapus semua test dari list?"):
            self._tests.clear()
            self._test_names.clear()
            self._list_panel.load_tests(self._tests)
            self._save_tasks()
            self._status_var.set("Ready")

    _TASKS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tasks.json")

    def _save_tasks(self):
        try:
            data = {
                "station": getattr(self, "_station", ""),
                "mode":    getattr(self, "_mode", "default"),
                "tests":   self._test_names,
            }
            with open(self._TASKS_FILE, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"[warn] Gagal simpan tasks.json: {e}")

    def _load_tasks(self):
        if not os.path.isfile(self._TASKS_FILE):
            return
        try:
            with open(self._TASKS_FILE) as f:
                data = json.load(f)
            if isinstance(data, list):
                names = data; self._station = ""; self._mode = "default"
            else:
                names = data.get("tests", [])
                self._station = data.get("station", "")
                self._mode    = data.get("mode", "default")
            for name in names:
                try:
                    item = load_test(name)
                    self._tests.append(item)
                    self._test_names.append(name)
                except Exception as e:
                    print(f"[warn] Gagal load test {name!r}: {e}")
        except Exception as e:
            print(f"[warn] Gagal load tasks.json: {e}")


if __name__ == "__main__":
    try:
        app = App()
        app.mainloop()
    except Exception as e:
        import traceback
        traceback.print_exc()
        input("Tekan Enter untuk keluar...")
