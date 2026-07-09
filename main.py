"""
main.py — Test Point Application entry point.

Run:
    python main.py

Architecture
------------
  App           — root window, display-size settings, top bar
  TestListPanel — scrollable list of TestRowWidget
  TestController — orchestrates running tests, manages serial communication
  KeepaliveManager — background ping for TM81 device (prevents sleep mode)
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "lib"))

# Pastikan stdout tidak di-buffer agar log langsung muncul
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(line_buffering=True)
    except Exception:
        pass

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import threading
import time
import json
import logging

from config import (
    DISPLAY_PRESETS, DEFAULT_PRESET, FONT_SCALE, BASE_FONTS,
    COLORS,
)

from test_modules import TestItem, TestType, TestResult
import test_loader
from test_loader import (discover_tests, load_test,
                         load_flash_tests, flash_module_names,
                         load_voltage_tests, voltage_module_names,
                         load_tm81_tests, tm81_module_names)
from test_row_widget import TestRowWidget

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("main")


# ---------------------------------------------------------------------------
# Project helpers
# ---------------------------------------------------------------------------

# Prefix modul yang termasuk project tertentu
_PROJECT_PREFIXES: dict[str, list[str]] = {
    "tm81":  ["tm81:"],
    "flash": ["flash:"],
}
# Modul individual (bukan prefix-based) yang dianggap project tertentu
_PROJECT_SINGLES: dict[str, list[str]] = {
    "flash": ["tm81_flash_test"],
}


def _module_project(module_name: str) -> "str | None":
    """Return project name jika modul bersifat project-specific, else None (universal)."""
    for proj, prefixes in _PROJECT_PREFIXES.items():
        if any(module_name.startswith(p) for p in prefixes):
            return proj
    for proj, singles in _PROJECT_SINGLES.items():
        if module_name in singles:
            return proj
    return None


def _detect_project(test_names: list) -> "str | None":
    """Deteksi project aktif dari daftar modul yang ada."""
    for name in test_names:
        proj = _module_project(name)
        if proj:
            return proj
    return None


# ============================================================================
# KeepaliveManager
# ============================================================================

class KeepaliveManager:
    """
    Mengirimkan ping ke TM81 secara periodik agar device tidak masuk sleep mode.
    Dikonfigurasi via json/config.json -> keepalive section.
    """

    # Error yang menandakan port serial rusak / perlu reconnect
    _SERIAL_ERR_KEYWORDS = (
        "writefile", "permissionerror", "access is denied",
        "getoverlappedresult", "broken pipe", "port is closed",
        "port not open", "device not found", "oserror",
    )

    def __init__(self):
        self._stop_evt = threading.Event()
        self._thread: threading.Thread | None = None
        self._cfg = self._load_cfg()
        self._log = logging.getLogger("keepalive")   # logger terpisah

    @staticmethod
    def _load_cfg() -> dict:
        try:
            path = os.path.join(os.path.dirname(__file__), "json", "config.json")
            with open(path) as f:
                return json.load(f).get("keepalive", {})
        except Exception:
            return {}

    @property
    def enabled(self) -> bool:
        return self._cfg.get("enabled", True)

    @property
    def interval(self) -> float:
        return self._cfg.get("interval_ms", 5000) / 1000.0

    @property
    def connection(self) -> str:
        return self._cfg.get("connection", "ch340")

    def _is_serial_error(self, result: str) -> bool:
        """True jika NG disebabkan port rusak (bukan timeout/NAK dari device)."""
        lower = result.lower()
        return any(kw in lower for kw in self._SERIAL_ERR_KEYWORDS)

    def start(self):
        """Mulai background ping. No-op jika sudah berjalan atau disabled."""
        if not self.enabled:
            return
        if self._thread and self._thread.is_alive():
            return
        self._stop_evt.clear()
        self._thread = threading.Thread(
            target=self._run, daemon=True, name="keepalive-ping"
        )
        self._thread.start()
        self._log.info("[PING] started — interval=%.1fs, conn=%r",
                       self.interval, self.connection)

    def stop(self):
        """Hentikan background ping."""
        self._stop_evt.set()
        self._log.info("[PING] stopped")

    def is_running(self) -> bool:
        return (
            self._thread is not None
            and self._thread.is_alive()
            and not self._stop_evt.is_set()
        )

    def _try_connect(self) -> bool:
        """Scan port, cari CH340, lalu connect. Return True jika berhasil."""
        try:
            import serial_manager as sm
            import serial.tools.list_ports as lp

            dev_name = sm._CONN_DEFS.get(self.connection, {}).get("device_name", "")
            kw       = dev_name.lower()

            found = ""
            for p in lp.comports():
                if (kw in (p.description  or "").lower()
                        or kw in (p.manufacturer or "").lower()
                        or kw in (p.product      or "").lower()):
                    found = p.device
                    break

            if not found:
                return False   # Port fisik belum ada — diam

            ok = sm.connect(self.connection)
            if ok:
                self._log.info("[PING] %r terhubung di %s", self.connection, found)
            return ok
        except Exception as e:
            self._log.debug("[PING] _try_connect error: %s", e)
            return False

    def _disconnect(self) -> None:
        """Tutup koneksi serial dan bersihkan state."""
        try:
            import serial_manager as sm
            sm.disconnect(self.connection)
            self._log.info("[PING] %r di-disconnect", self.connection)
        except Exception as e:
            self._log.debug("[PING] _disconnect error: %s", e)

    def _run(self):
        import serial_manager as sm
        from commands.tm81.ping import Ping

        _state = "unknown"   # "unknown" | "connected" | "disconnected"

        while not self._stop_evt.wait(self.interval):
            try:
                result = str(Ping().execute()).strip()

                if result.upper().startswith("OK"):
                    # ── Normal ───────────────────────────────────────
                    if _state != "connected":
                        self._log.info("[PING] aktif ke %r", self.connection)
                        _state = "connected"
                    self._log.debug("[PING] OK")

                elif "tidak terhubung" in result.lower():
                    # ── Port belum di-connect ────────────────────────
                    if _state != "disconnected":
                        self._log.info("[PING] %r belum terhubung, scan port...",
                                       self.connection)
                        _state = "disconnected"
                    if self._try_connect():
                        _state = "connected"

                elif self._is_serial_error(result):
                    # ── Serial error (PermissionError, WriteFile, dll.) ─
                    if _state != "disconnected":
                        self._log.warning("[PING] serial error → disconnect & reconnect: %s",
                                          result)
                        _state = "disconnected"
                    self._disconnect()
                    if self._stop_evt.wait(2.0):
                        break
                    if self._try_connect():
                        _state = "connected"

                else:
                    # ── Device NG (Timeout, NAK) — port masih OK, lanjutkan ─
                    self._log.debug("[PING] device NG: %s", result)

            except Exception as e:
                if _state != "disconnected":
                    self._log.warning("[PING] exception → disconnect & reconnect: %s", e)
                    _state = "disconnected"
                self._disconnect()


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
        self._seq_running  = False
        self._stop_event   = threading.Event()
        self._wf           = self._load_workflow()
        self._uploader     = None   # UploaderBase instance, set by App

    @staticmethod
    def _load_workflow() -> dict:
        try:
            path = os.path.join(os.path.dirname(__file__), "json", "config.json")
            with open(path) as f:
                return json.load(f).get("workflow", {})
        except Exception:
            return {}

    @property
    def _test_delay(self) -> float:
        return self._wf.get("test_delay_ms", 500) / 1000.0

    @property
    def _max_retries(self) -> int:
        return max(0, int(self._wf.get("max_retries", 3)))

    @property
    def _retry_delay(self) -> float:
        return self._wf.get("retry_delay_ms", 1000) / 1000.0

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def is_seq_running(self) -> bool:
        return self._seq_running

    def run_test(self, row: TestRowWidget, done_callback=None):
        """Run a single test row."""
        item = row.test_item
        row.set_running()

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

        def _progress(pct):
            row.master.after(0, lambda p=pct: row.advance_progress(p))

        fn = item.run_fn
        if hasattr(fn, "__self__") and hasattr(fn.__self__, "set_progress_cb"):
            fn.__self__.set_progress_cb(_progress)

        max_retries = 0 if item.no_retry else self._max_retries
        retry_delay = self._retry_delay

        def _try_once():
            try:
                resp = item.run_fn()
            except Exception as e:
                log.exception("Exception saat run_fn '%s':", item.title)
                resp = f"NG:{e}"
            resp   = str(resp).strip()
            is_ok  = resp.upper() == "OK" or resp.upper().startswith("OK:")
            ok_msg = resp[3:].strip() if resp.upper().startswith("OK:") else ""
            error  = resp.split(":", 1)[1].strip() if not is_ok and ":" in resp else ""
            return is_ok, error, ok_msg

        def worker():
            t_start = time.monotonic()
            is_ok, error, ok_msg = _try_once()
            for attempt in range(1, max_retries + 1):
                if is_ok or self._stop_event.is_set():
                    break
                row.master.after(0, lambda a=attempt, n=max_retries:
                    row._status_lbl.config(
                        text=f"Retry {a}/{n}...", fg=COLORS["running"]))
                for _ in range(int(retry_delay / 0.05)):
                    if self._stop_event.is_set():
                        break
                    time.sleep(0.05)
                if self._stop_event.is_set():
                    break
                row.master.after(0, row.set_running)
                is_ok, error, ok_msg = _try_once()

            if self._stop_event.is_set():
                return

            duration_ms = int((time.monotonic() - t_start) * 1000)
            result = TestResult.OK if is_ok else TestResult.NG
            row.master.after(
                0, lambda r=result, e=error, m=ok_msg, d=duration_ms:
                _finish(r, e, m, d)
            )

        def _finish(result, error="", ok_msg="", duration_ms=0):
            row.set_result(result, error, ok_msg)
            if done_callback:
                done_callback(row)
            # Upload hasil ke DB (non-blocking)
            if self._uploader:
                try:
                    from db_uploader import TestResultRecord
                    rec = TestResultRecord(
                        station=test_loader.context.get("station", ""),
                        device_id=test_loader.context.get("device_id", ""),
                        test_name=row.test_item.title,
                        command=getattr(row.test_item, "command", ""),
                        result="OK" if result == TestResult.OK else "NG",
                        duration_ms=duration_ms,
                        notes=error or ok_msg,
                    )
                    threading.Thread(
                        target=self._uploader.upload,
                        args=(rec,),
                        daemon=True,
                    ).start()
                except Exception as e:
                    log.warning("Gagal upload ke DB: %s", e)

        threading.Thread(target=worker, daemon=True).start()

    def run_all(self, rows: list, done_callback=None, scroll_fn=None):
        """Run all rows sequentially in a background thread."""
        if self._seq_running:
            return
        self._stop_event.clear()
        threading.Thread(
            target=self._seq_worker, args=(rows, done_callback, scroll_fn), daemon=True
        ).start()

    def stop_now(self, rows: list):
        """Hentikan seketika dan reset semua rows."""
        self._stop_event.set()
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
        log.debug("_run_manual: %s", row.test_item.title)

        def _poll():
            if row.test_item.is_done():
                log.debug("manual done: %s -> %s", row.test_item.title, row.test_item.result)
                if done_callback:
                    done_callback(row)
            else:
                row.master.after(200, _poll)

        def _show_buttons():
            log.debug("enable buttons: %s", row.test_item.title)
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

    def _seq_worker(self, rows: list, done_callback, scroll_fn=None):
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

            if scroll_fn:
                row.master.after(0, lambda r=row: scroll_fn(r))

            event = threading.Event()
            row.master.after(
                0,
                lambda r=row, ev=event: self.run_test(
                    r, done_callback=lambda _r, ev=ev: ev.set()
                )
            )

            deadline = None if is_manual else (time.time() + 120)
            while not event.is_set() and not self._stop_event.is_set():
                if deadline and time.time() > deadline:
                    break
                time.sleep(0.05)

            if self._stop_event.is_set():
                break

            if row.test_item.result == TestResult.NG:
                self._seq_running = False
                break

            for _ in range(int(self._test_delay / 0.05)):
                if self._stop_event.is_set():
                    break
                time.sleep(0.05)

        self._seq_running = False
        master = last_row.master if last_row else rows[0].master if rows else None
        if done_callback and master:
            master.after(0, lambda: done_callback(None))


# ============================================================================
# TestListPanel
# ============================================================================

class TestListPanel(tk.Frame):
    """Scrollable list of TestRowWidgets."""

    def __init__(self, parent, scale: float, controller: TestController, **kwargs):
        super().__init__(parent, **kwargs)
        self.scale      = scale
        self.controller = controller
        self._rows: list[TestRowWidget] = []

        self._build()

    def _build(self):
        container = tk.Frame(self)
        container.pack(fill="both", expand=True)

        self._canvas = tk.Canvas(container, bg=COLORS["bg"], highlightthickness=0)
        self._scrollbar = ttk.Scrollbar(container, orient="vertical", command=self._canvas.yview)
        self._canvas.configure(yscrollcommand=self._auto_scrollbar)

        self._canvas.pack(fill="both", expand=True)

        self._inner  = tk.Frame(self._canvas, bg=COLORS["bg"])
        self._window = self._canvas.create_window((0, 0), window=self._inner, anchor="nw")

        self._inner.bind("<Configure>", self._on_frame_configure)
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

    def scroll_to_row(self, row: TestRowWidget):
        self._inner.update_idletasks()
        try:
            row_y    = row.frame.winfo_y()
            row_h    = row.frame.winfo_height()
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

    Project logic:
      - Hanya satu "project" (tm81 / flash) yang aktif sekaligus.
      - Task universal (voltage, connect_test, dsb.) selalu bisa ditambahkan.
      - Jika project sudah aktif, tombol project lain akan di-disable.
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

    # ----------------------------------------------------------------

    def _btn_state(self, module_project: "str | None") -> str:
        """
        Return "normal" jika tombol boleh diklik, "disabled" jika konflik.
        module_project=None berarti universal — selalu normal.
        """
        if module_project is None:
            return "normal"
        if self._current_project is None:
            return "normal"
        if self._current_project == module_project:
            return "normal"
        return "disabled"

    def _build(self):
        TYPE_COLORS = {"progress": "#3498db", "manual": "#8e44ad", "auto": "#27ae60"}

        row_idx = 0

        # ── Header project aktif ────────────────────────────────────────
        if self._current_project:
            proj_label = {
                "tm81":  "🔵 Project aktif: TM81  (flash tidak bisa ditambahkan)",
                "flash": "🟠 Project aktif: Flash  (tm81 tidak bisa ditambahkan)",
            }.get(self._current_project, f"Project aktif: {self._current_project}")
            tk.Label(
                self, text=proj_label,
                font=("TkDefaultFont", 9), fg="#888", pady=4, anchor="w",
            ).grid(row=row_idx, column=0, columnspan=4, padx=12, sticky="ew")
            row_idx += 1
            ttk.Separator(self, orient="horizontal").grid(
                row=row_idx, column=0, columnspan=4, sticky="ew", padx=8, pady=(0, 4)
            )
            row_idx += 1

        tk.Label(self, text="Pilih test module:",
                 font=("TkDefaultFont", 10, "bold"), pady=8,
                 ).grid(row=row_idx, column=0, columnspan=4, padx=14, sticky="w")
        row_idx += 1

        # ── Flash ───────────────────────────────────────────────────────
        flash_names = flash_module_names()
        flash_proj  = "flash"
        flash_state = self._btn_state(flash_proj)
        if flash_names:
            n_regions  = len(flash_names)
            labels_str = ", ".join(n.split(":")[1] for n in flash_names)
            tk.Label(self, text=f"Flash ({labels_str})",
                     font=("TkDefaultFont", 10, "bold"), anchor="w", width=22,
                     fg="gray" if flash_state == "disabled" else "black",
                     ).grid(row=row_idx, column=0, sticky="w", padx=(12, 4), pady=4)
            tk.Label(self, text="progress",
                     bg=TYPE_COLORS["progress"], fg="white",
                     font=("TkDefaultFont", 8), padx=6, pady=2,
                     ).grid(row=row_idx, column=1, padx=4, sticky="w")
            tk.Label(self, text=f"{n_regions} region",
                     font=("Courier", 9), fg="#555", anchor="w", width=14,
                     ).grid(row=row_idx, column=2, sticky="w", padx=4)
            tk.Button(self, text="+ Add", width=7,
                      font=("TkDefaultFont", 9),
                      bg="#27ae60" if flash_state == "normal" else "#bdc3c7",
                      fg="white", relief="flat",
                      cursor="hand2" if flash_state == "normal" else "",
                      state=flash_state,
                      command=self._add_all_flash,
                      ).grid(row=row_idx, column=3, padx=(6, 12), pady=3, sticky="e")
            row_idx += 1

        # ── Voltage (universal) ─────────────────────────────────────────
        volt_names = voltage_module_names()
        if volt_names:
            n_volt      = len(volt_names)
            volt_labels = ", ".join(n.split(":")[1] for n in volt_names)
            tk.Label(self, text=f"Voltage ({volt_labels})",
                     font=("TkDefaultFont", 10, "bold"), anchor="w", width=22,
                     ).grid(row=row_idx, column=0, sticky="w", padx=(12, 4), pady=4)
            tk.Label(self, text="auto",
                     bg=TYPE_COLORS["auto"], fg="white",
                     font=("TkDefaultFont", 8), padx=6, pady=2,
                     ).grid(row=row_idx, column=1, padx=4, sticky="w")
            tk.Label(self, text=f"{n_volt} entry",
                     font=("Courier", 9), fg="#555", anchor="w", width=14,
                     ).grid(row=row_idx, column=2, sticky="w", padx=4)
            tk.Button(self, text="+ Add", width=7,
                      font=("TkDefaultFont", 9),
                      bg="#27ae60", fg="white", relief="flat",
                      cursor="hand2",
                      command=self._add_all_voltage,
                      ).grid(row=row_idx, column=3, padx=(6, 12), pady=3, sticky="e")
            row_idx += 1

        # ── TM81 ────────────────────────────────────────────────────────
        tm81_names  = tm81_module_names()
        tm81_proj   = "tm81"
        tm81_state  = self._btn_state(tm81_proj)
        if tm81_names:
            n_tm81 = len(tm81_names)
            tk.Label(self, text=f"TM81 ({n_tm81} test)",
                     font=("TkDefaultFont", 10, "bold"), anchor="w", width=22,
                     fg="gray" if tm81_state == "disabled" else "black",
                     ).grid(row=row_idx, column=0, sticky="w", padx=(12, 4), pady=4)
            tk.Label(self, text="auto",
                     bg=TYPE_COLORS["auto"], fg="white",
                     font=("TkDefaultFont", 8), padx=6, pady=2,
                     ).grid(row=row_idx, column=1, padx=4, sticky="w")
            tk.Label(self, text=f"{n_tm81} entry",
                     font=("Courier", 9), fg="#555", anchor="w", width=14,
                     ).grid(row=row_idx, column=2, sticky="w", padx=4)
            tk.Button(self, text="+ Add", width=7,
                      font=("TkDefaultFont", 9),
                      bg="#27ae60" if tm81_state == "normal" else "#bdc3c7",
                      fg="white", relief="flat",
                      cursor="hand2" if tm81_state == "normal" else "",
                      state=tm81_state,
                      command=self._add_all_tm81,
                      ).grid(row=row_idx, column=3, padx=(6, 12), pady=3, sticky="e")
            row_idx += 1

        # ── Modul lainnya ───────────────────────────────────────────────
        for name, label, mod in self._modules:
            mod_proj  = _module_project(name)
            mod_state = self._btn_state(mod_proj)
            ttype = getattr(mod, "TYPE", "auto")
            cmd   = getattr(mod, "COMMAND", "?")

            tk.Label(self, text=label,
                     font=("TkDefaultFont", 10, "bold"), anchor="w", width=22,
                     fg="gray" if mod_state == "disabled" else "black",
                     ).grid(row=row_idx, column=0, sticky="w", padx=(12, 4), pady=4)
            tk.Label(self, text=ttype,
                     bg=TYPE_COLORS.get(ttype, "#999"), fg="white",
                     font=("TkDefaultFont", 8), padx=6, pady=2,
                     ).grid(row=row_idx, column=1, padx=4, sticky="w")
            tk.Label(self, text=cmd,
                     font=("Courier", 9), fg="#555", anchor="w", width=14,
                     ).grid(row=row_idx, column=2, sticky="w", padx=4)
            tk.Button(self, text="+ Add", width=7,
                      font=("TkDefaultFont", 9),
                      bg="#27ae60" if mod_state == "normal" else "#bdc3c7",
                      fg="white", relief="flat",
                      cursor="hand2" if mod_state == "normal" else "",
                      state=mod_state,
                      command=lambda n=name: self._add(n),
                      ).grid(row=row_idx, column=3, padx=(6, 12), pady=3, sticky="e")
            row_idx += 1

        ttk.Separator(self, orient="horizontal").grid(
            row=row_idx, column=0, columnspan=4, sticky="ew", pady=6, padx=8)
        row_idx += 1
        tk.Button(self, text="Tutup", width=10, command=self.destroy,
                  relief="flat",
                  ).grid(row=row_idx, column=0, columnspan=4, pady=(0, 10))

    def _add(self, module_name: str):
        item = load_test(module_name)
        self._on_add(item, module_name)

    def _add_all_flash(self):
        items = load_flash_tests()
        names = flash_module_names()
        for item, name in zip(items, names):
            self._on_add(item, name)

    def _add_all_voltage(self):
        items = load_voltage_tests()
        names = voltage_module_names()
        for item, name in zip(items, names):
            self._on_add(item, name)

    def _add_all_tm81(self):
        items = load_tm81_tests()
        names = tm81_module_names()
        for item, name in zip(items, names):
            self._on_add(item, name)


# ============================================================================
# App (main window)
# ============================================================================

class App(tk.Tk):

    _TASKS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tasks.json")
    _TASKS_VERSION = 2   # increment saat format berubah

    def __init__(self):
        super().__init__()
        self.title("Test Point")
        self.configure(bg=COLORS["bg"])

        # Tangkap exception dari Tkinter callback agar muncul di log
        self.report_callback_exception = self._on_tk_error

        self._preset       = DEFAULT_PRESET
        self._scale        = FONT_SCALE[DEFAULT_PRESET]
        self._display_w, self._display_h = DISPLAY_PRESETS[DEFAULT_PRESET]
        self._test_names   : list[str]      = []
        self._tests        : list[TestItem] = []
        self._station      : str            = ""
        self._project      : "str | None"   = None   # "tm81" | "flash" | None

        self._controller   = TestController()
        self._keepalive    = KeepaliveManager()

        self._load_tasks()

        self.geometry(f"{self._display_w}x{self._display_h}")
        self.minsize(320, 240)
        self.resizable(self._preset == "Custom", self._preset == "Custom")

        self._build()

        # Auto-connect setelah UI siap
        self.after(500, self._auto_connect)

    # ------------------------------------------------------------------
    # Tkinter error handler
    # ------------------------------------------------------------------

    def _on_tk_error(self, exc_type, exc_val, exc_tb):
        import traceback
        log.error("Exception dalam Tkinter callback:")
        log.error("".join(traceback.format_exception(exc_type, exc_val, exc_tb)))

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

        # Project badge
        proj_text = f"  [{self._project.upper()}]" if self._project else ""
        self._proj_lbl = tk.Label(
            top, text=proj_text,
            bg=COLORS["header_bg"], fg="#f39c12",
            font=("TkDefaultFont", fs("small"), "bold"),
        )
        self._proj_lbl.pack(side="left")

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
            bg=COLORS["bg"], fg=COLORS["text"], font=("TkDefaultFont", fs("label")),
        ).pack(side="left")

        self._device_var = tk.StringVar()
        # Update context tiap karakter, reset session saat focus out (SN selesai diketik)
        self._device_var.trace_add(
            "write",
            lambda *_: test_loader.context.update({"device_id": self._device_var.get()}),
        )
        _dev_entry = tk.Entry(
            inp_frame, textvariable=self._device_var,
            font=("TkDefaultFont", fs("label")), width=20,
        )
        _dev_entry.pack(side="left", padx=6)
        _dev_entry.bind("<FocusOut>", lambda _: self._on_device_change())
        _dev_entry.bind("<Return>",   lambda _: self._on_device_change())

        tk.Label(
            inp_frame, text="Station:",
            bg=COLORS["bg"], fg=COLORS["text"], font=("TkDefaultFont", fs("label")),
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

        self._toggle_btn = tk.Button(
            act_frame, text="▶  Start",
            command=self._toggle_run,
            bg="#2980b9", fg="white", relief="flat",
            font=("TkDefaultFont", fs("button")),
            padx=10, pady=4, cursor="hand2",
        )
        self._toggle_btn.pack(side="left")

        tk.Frame(act_frame, width=1, bg="#cccccc").pack(side="left", fill="y", padx=8, pady=4)

        tk.Button(
            act_frame, text="🗑  Clear",
            command=self._clear_all,
            bg="#c0392b", fg="white", relief="flat",
            font=("TkDefaultFont", fs("button")),
            padx=8, pady=4, cursor="hand2",
        ).pack(side="left")

        self._status_var = tk.StringVar(value="Ready")
        tk.Label(
            act_frame, textvariable=self._status_var,
            bg=COLORS["bg"], fg=COLORS["text"], font=("TkDefaultFont", fs("small")),
        ).pack(side="right")

        # ── Test list ────────────────────────────────────────────────
        self._list_panel = TestListPanel(
            self, scale=self._scale, controller=self._controller,
            bg=COLORS["bg"],
        )
        self._list_panel.pack(fill="both", expand=True, padx=10, pady=(0, 8))
        self._list_panel.load_tests(self._tests)

    def _refresh_project_label(self):
        """Update project badge di top bar."""
        if hasattr(self, "_proj_lbl"):
            proj_text = f"  [{self._project.upper()}]" if self._project else ""
            self._proj_lbl.config(text=proj_text)

    # ------------------------------------------------------------------
    # Sequential run
    # ------------------------------------------------------------------

    def _toggle_run(self):
        if not self._controller.is_seq_running():
            self._do_start()
        else:
            self._do_stop()

    def _do_start(self):
        rows = self._list_panel.get_rows()
        if not rows:
            return
        for row in rows:
            row.reset()
        # Buat sesi baru di DB untuk sequential run ini
        self._reset_db_session()
        self._status_var.set("Running…")
        self._toggle_btn.config(text="⏹  Stop", bg="#e67e22")
        self._controller.run_all(
            rows,
            done_callback=self._on_seq_done,
            scroll_fn=self._list_panel.scroll_to_row,
        )

    def _do_stop(self):
        rows = self._list_panel.get_rows()
        self._controller.stop_now(rows)
        self._toggle_btn.config(text="▶  Start", bg="#2980b9")
        self._status_var.set("Dihentikan")

    def _on_seq_done(self, _):
        rows    = self._list_panel.get_rows()
        ng_rows = [r for r in rows if r.test_item.result == TestResult.NG]
        ok_rows = [r for r in rows if r.test_item.result == TestResult.OK]

        if ng_rows:
            ng_names = ", ".join(r.test_item.title for r in ng_rows)
            self._status_var.set(f"STOP — NG: {ng_names}")
            self._finalize_db_session("NG")
        elif len(ok_rows) == len(rows):
            self._status_var.set("✓ Semua test PASS")
            self._finalize_db_session("OK")
        else:
            self._status_var.set("Selesai")
            self._finalize_db_session(None)

        self._toggle_btn.config(text="▶  Start", bg="#2980b9")

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _auto_connect(self):
        """
        Scan semua koneksi dari config.json, coba connect tiap-tiap port.
        Semua UI update di-schedule via self.after() agar aman dari background thread.
        """
        def _do():
            import serial_manager as sm
            import serial.tools.list_ports as lp

            try:
                all_ports = list(lp.comports())
            except Exception:
                all_ports = []

            def find_port(device_name: str) -> str:
                kw = device_name.lower()
                for p in all_ports:
                    if (kw in (p.description or "").lower() or
                            kw in (p.manufacturer or "").lower() or
                            kw in (p.product or "").lower()):
                        return p.device
                return ""

            for name, cfg in sm._CONN_DEFS.items():
                dev_name = cfg.get("device_name", "")
                found    = find_port(dev_name)
                ok       = False
                try:
                    ok = sm.connect(name)
                except Exception as e:
                    # Log hanya — UI update via after()
                    self.after(0, lambda n=name, e=e:
                        log.warning("[serial] connect(%r) error: %s", n, e))
                status = f"OK [{found}]" if ok else f"NG (cari: {dev_name!r})"
                # Log dari main thread (setelah after) untuk thread safety
                self.after(0, lambda n=name, s=status:
                    log.info("[serial] %s: %s", n, s))

        threading.Thread(target=_do, daemon=True).start()

    def _on_device_change(self, *_):
        """Dipanggil saat device_id berubah — buat session baru untuk device baru."""
        test_loader.context["device_id"] = self._device_var.get()
        # Reset session: session lama ditutup, session baru dibuat lazy saat test pertama
        self._new_db_session()

    def _on_station_change(self, *_):
        self._station = self._station_var.get()
        test_loader.context["station"] = self._station
        self._save_tasks()

    def _reset_all(self):
        rows = self._list_panel.get_rows()
        self._controller.stop_now(rows)
        self._toggle_btn.config(text="▶  Start", bg="#2980b9")
        self._status_var.set("Ready")

    def _open_display_settings(self):
        DisplaySettingsDialog(self, self._preset, on_apply=self._apply_display)

    def _apply_display(self, preset: str, width: int, height: int):
        self._preset    = preset
        self._scale     = FONT_SCALE.get(preset, 1.0)
        self._display_w = width
        self._display_h = height
        self.geometry(f"{width}x{height}")
        self.resizable(preset == "Custom", preset == "Custom")
        self._save_tasks()
        for child in self.winfo_children():
            child.destroy()
        self._build()
        self._list_panel.load_tests(self._tests)

    def _open_add_test(self):
        AddTestDialog(self, on_add=self._add_test, current_project=self._project)

    def _add_test(self, item, module_name: str = ""):
        # Cek konflik project
        new_proj = _module_project(module_name)
        if new_proj and self._project and new_proj != self._project:
            messagebox.showwarning(
                "Konflik Project",
                f"Project aktif: {self._project.upper()}\n"
                f"Tidak bisa menambahkan modul project {new_proj.upper()}.\n"
                f"Hapus semua test {self._project.upper()} terlebih dahulu."
            )
            return

        self._tests.append(item)
        self._test_names.append(module_name)

        # Update project
        if new_proj and self._project != new_proj:
            self._project = new_proj
            self._refresh_project_label()
            # Start keepalive jika project TM81
            if new_proj == "tm81":
                self._keepalive.start()
            else:
                self._keepalive.stop()

        self._list_panel.load_tests(self._tests)
        self._save_tasks()

    def _clear_all(self):
        if not self._tests:
            return
        if messagebox.askyesno("Clear All", "Hapus semua test dari list?"):
            self._tests.clear()
            self._test_names.clear()
            self._project = None
            self._keepalive.stop()
            self._refresh_project_label()
            self._list_panel.load_tests(self._tests)
            self._save_tasks()
            self._status_var.set("Ready")

    # ------------------------------------------------------------------
    # Database session
    # ------------------------------------------------------------------

    def _reset_db_session(self):
        """Tutup session lama (jika ada) lalu buat session baru untuk sequential run."""
        uploader = self._controller._uploader
        if uploader and getattr(uploader, "_session_id", None):
            self._finalize_db_session(None)
        self._new_db_session(force_new=True)

    @staticmethod
    def _load_db_config() -> dict:
        try:
            path = os.path.join(os.path.dirname(__file__), "json", "config.json")
            with open(path, encoding="utf-8") as f:
                return json.load(f).get("database", {})
        except Exception:
            return {}

    def _new_db_session(self, force_new: bool = False):
        """
        Siapkan uploader untuk device saat ini.

        force_new=False (default — saat SN berubah):
          Cari session terbuka untuk SN ini → resume jika ada, buat baru jika tidak.

        force_new=True (saat Start ditekan):
          Selalu buat session baru (fresh run), langsung INSERT ke DB.
        """
        db_cfg = self._load_db_config()
        if not db_cfg.get("enabled", True):
            self._controller._uploader = None
            return

        device_id = self._device_var.get() if hasattr(self, "_device_var") else ""
        backend   = db_cfg.get("backend", "sqlite")

        try:
            if backend == "server":
                from db_uploader import LocalServerUploader, LocalServerConfig
                url     = db_cfg.get("server_url", "http://localhost:5001")
                uploader = LocalServerUploader(
                    config=LocalServerConfig(base_url=url),
                    station=self._station,
                    device_id=device_id,
                    project=self._project,
                )
                if force_new:
                    sid = uploader.new_session()
                    if sid:
                        log.info("DB: session baru #%d (server, device=%r)", sid, device_id)
                    else:
                        log.warning("DB: gagal buat session di %s", url)
                else:
                    sid = self._find_open_session_server(url, device_id)
                    if sid:
                        uploader.set_session_id(sid)
                        log.info("DB: resume session #%d (device=%r)", sid, device_id)
                    # else: lazy — dibuat saat test pertama

            else:  # sqlite
                from db_uploader import SQLiteUploader
                from server.db import init_db, db_conn, now_iso
                uploader = SQLiteUploader()
                init_db(uploader.cfg.db_path)

                if force_new:
                    with db_conn(uploader.cfg.db_path) as conn:
                        cur = conn.execute(
                            "INSERT INTO sessions (created_at, station, device_id, project) "
                            "VALUES (?, ?, ?, ?)",
                            (now_iso(), self._station, device_id, self._project),
                        )
                        uploader.set_session_id(cur.lastrowid)
                    log.info("DB: session baru #%d (sqlite, device=%r)",
                             uploader._session_id, device_id)
                else:
                    sid = self._find_open_session_sqlite(uploader.cfg.db_path, device_id)
                    if sid:
                        uploader.set_session_id(sid)
                        log.info("DB: resume session #%d (device=%r)", sid, device_id)
                    # else: lazy — dibuat saat test pertama

            self._controller._uploader = uploader

        except Exception as e:
            log.warning("Gagal init DB uploader: %s", e)
            self._controller._uploader = None

    @staticmethod
    def _find_open_session_sqlite(db_path: str, device_id: str) -> "int | None":
        """Cari session yang belum ditutup (finished_at IS NULL) untuk device_id ini."""
        if not device_id:
            return None
        try:
            from server.db import db_conn
            with db_conn(db_path) as conn:
                row = conn.execute(
                    "SELECT id FROM sessions "
                    "WHERE device_id=? AND finished_at IS NULL "
                    "ORDER BY id DESC LIMIT 1",
                    (device_id,)
                ).fetchone()
            return row["id"] if row else None
        except Exception:
            return None

    @staticmethod
    def _find_open_session_server(base_url: str, device_id: str) -> "int | None":
        """Cari session yang belum ditutup via Flask API."""
        if not device_id:
            return None
        try:
            import urllib.request, urllib.parse, json as _json
            url = f"{base_url}/api/v1/devices/{urllib.parse.quote(device_id)}"
            with urllib.request.urlopen(url, timeout=3) as resp:
                sessions = _json.loads(resp.read())
            for s in sessions:
                if not s.get("finished_at"):
                    return s["id"]
            return None
        except Exception:
            return None

    def _finalize_db_session(self, result: "str | None"):
        """
        Tandai sesi selesai dengan result "OK" / "NG" / None.
        Dipanggil di _on_seq_done().
        """
        uploader = self._controller._uploader
        if not uploader or not getattr(uploader, "_session_id", None):
            return
        try:
            from server.db import db_conn, now_iso
            with db_conn(uploader.cfg.db_path) as conn:
                conn.execute(
                    "UPDATE sessions SET finished_at=?, result=? WHERE id=?",
                    (now_iso(), result, uploader._session_id),
                )
            log.info("DB session #%d selesai: %s", uploader._session_id, result or "?")
        except Exception as e:
            log.warning("Gagal finalize DB session: %s", e)

    # ------------------------------------------------------------------
    # Persist tasks
    # ------------------------------------------------------------------

    def _save_tasks(self):
        try:
            data = {
                "version":   self._TASKS_VERSION,
                "station":   getattr(self, "_station", ""),
                "project":   getattr(self, "_project", None),
                "tests":     self._test_names,
                "preset":    getattr(self, "_preset", ""),
                "display_w": getattr(self, "_display_w", 0),
                "display_h": getattr(self, "_display_h", 0),
            }
            with open(self._TASKS_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            log.warning("Gagal simpan tasks.json: %s", e)

    def _load_tasks(self):
        if not os.path.isfile(self._TASKS_FILE):
            return
        try:
            with open(self._TASKS_FILE, encoding="utf-8") as f:
                data = json.load(f)

            # Handle format lama (list) dan format baru (dict)
            if isinstance(data, list):
                names = data
            else:
                # Cek version agar tidak salah baca format lama
                ver = data.get("version", 1)
                if ver > self._TASKS_VERSION:
                    log.warning(
                        "tasks.json version %d lebih baru dari yang didukung (%d), skip.",
                        ver, self._TASKS_VERSION
                    )
                    return

                names             = data.get("tests", [])
                self._station     = data.get("station", "")
                self._project     = data.get("project", None)

                saved_preset = data.get("preset", "")
                if saved_preset and (saved_preset in DISPLAY_PRESETS or saved_preset == "Custom"):
                    self._preset    = saved_preset
                    self._scale     = FONT_SCALE.get(saved_preset, 1.0)
                    self._display_w = data.get("display_w", self._display_w)
                    self._display_h = data.get("display_h", self._display_h)

            for name in names:
                try:
                    item = load_test(name)
                    self._tests.append(item)
                    self._test_names.append(name)
                except Exception as e:
                    log.warning("Gagal load test %r: %s", name, e)

            # Re-detect project dari test names (safety check)
            if not self._project:
                self._project = _detect_project(self._test_names)

            # Mulai keepalive jika project TM81
            if self._project == "tm81":
                self._keepalive.start()

        except Exception as e:
            log.warning("Gagal load tasks.json: %s", e)


if __name__ == "__main__":
    try:
        app = App()
        app.mainloop()
    except Exception as e:
        import traceback
        traceback.print_exc()
        input("Tekan Enter untuk keluar...")
