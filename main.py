"""
main.py — Test Point Application entry point.

Run:
    python main.py

Architecture
------------
  App                 — root window, display-size settings, top bar
  ui.TestListPanel    — scrollable list of TestRowWidget (ui/test_list_panel.py)
  ui.DisplaySettingsDialog / AddTestDialog — dialogs (ui/dialogs.py)
  controllers.TestController   — orchestrates running tests (controllers/test_controller.py)
  controllers.KeepaliveManager — background TM81 ping (controllers/keepalive.py)
  lib.project         — module_project / detect_project helpers (lib/project.py)
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "lib"))

APP_VERSION = "0.5.0"

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(line_buffering=True)
    except Exception:
        pass

import tkinter as tk
from tkinter import messagebox
import threading
import json
import logging

from config import (
    DISPLAY_PRESETS, DEFAULT_PRESET, FONT_SCALE, BASE_FONTS, COLORS,
)
from test_modules import TestItem, TestResult
import test_loader
from test_loader import load_test

from project import module_project, detect_project

# ── New packages ──────────────────────────────────────────────────────────────
# Tambah root ke path agar sub-package bisa import lib/
_ROOT = os.path.dirname(os.path.abspath(__file__))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from controllers.keepalive   import KeepaliveManager
from controllers.test_controller import TestController
from ui.test_list_panel      import TestListPanel
from ui.dialogs              import DisplaySettingsDialog, AddTestDialog, CommissioningDialog

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("main")


# ============================================================================
# App (main window)
# ============================================================================

class App(tk.Tk):

    _TASKS_FILE    = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tasks.json")
    _TASKS_VERSION = 2

    def __init__(self):
        super().__init__()
        self.title(f"Test Point  v{APP_VERSION}")
        self.configure(bg=COLORS["bg"])
        self.report_callback_exception = self._on_tk_error

        self._preset       = DEFAULT_PRESET
        self._scale        = FONT_SCALE[DEFAULT_PRESET]
        self._display_w, self._display_h = DISPLAY_PRESETS[DEFAULT_PRESET]
        self._test_names   : list[str]      = []
        self._tests        : list[TestItem] = []
        self._station      : str            = ""
        self._project      : "str | None"   = None

        self._controller = TestController()
        self._keepalive  = KeepaliveManager()

        self._load_tasks()

        self.geometry(f"{self._display_w}x{self._display_h}")
        self.minsize(320, 240)
        self.resizable(self._preset == "Custom", self._preset == "Custom")

        self._build()
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
        fs = lambda k: max(7, int(BASE_FONTS[k] * self._scale))

        # ── Top bar ──────────────────────────────────────────────────
        top = tk.Frame(self, bg=COLORS["header_bg"], pady=4)
        top.pack(fill="x")

        tk.Label(
            top, text="Test Point", bg=COLORS["header_bg"], fg="white",
            font=("TkDefaultFont", fs("title"), "bold"),
        ).pack(side="left", padx=10)

        proj_text = f"  [{self._project.upper()}]" if self._project else ""
        self._proj_lbl = tk.Label(
            top, text=proj_text,
            bg=COLORS["header_bg"], fg="#f39c12",
            font=("TkDefaultFont", fs("small"), "bold"),
        )
        self._proj_lbl.pack(side="left")

        tk.Button(
            top, text="⚙ Commissioning", command=self._open_commissioning,
            bg=COLORS["header_bg"], fg="#f39c12", relief="flat",
            font=("TkDefaultFont", fs("button")), cursor="hand2",
        ).pack(side="right", padx=6)

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

        # ── Input area (surface bg + bottom border) ───────────────────
        _inp_wrap = tk.Frame(self, bg=COLORS["surface"])
        _inp_wrap.pack(fill="x")
        inp_frame = tk.Frame(_inp_wrap, bg=COLORS["surface"], pady=6)
        inp_frame.pack(fill="x", padx=10)
        tk.Frame(_inp_wrap, height=1, bg=COLORS["border"]).pack(fill="x")

        tk.Label(
            inp_frame, text="Device ID / Serial No.:",
            bg=COLORS["surface"], fg=COLORS["text"],
            font=("TkDefaultFont", fs("label")),
        ).pack(side="left")

        self._device_var = tk.StringVar()
        # Update context setiap keystroke + update state tombol Start
        self._device_var.trace_add(
            "write",
            lambda *_: (
                test_loader.update_context({"device_id": self._device_var.get()}),
                self._update_start_btn(),
            ),
        )
        _dev_entry = tk.Entry(
            inp_frame, textvariable=self._device_var,
            font=("TkDefaultFont", fs("label")), width=20,
            bg=COLORS["card"], fg=COLORS["text"],
            insertbackground=COLORS["text"], relief="flat",
            highlightthickness=1, highlightbackground=COLORS["border"],
            highlightcolor=COLORS["running"],
        )
        _dev_entry.pack(side="left", padx=6)
        # FocusOut dan Return → pindah device, siapkan DB session (background)
        _dev_entry.bind("<FocusOut>", lambda _: self._on_device_change())
        _dev_entry.bind("<Return>",   lambda _: self._on_device_change())

        tk.Label(
            inp_frame, text="Station:",
            bg=COLORS["surface"], fg=COLORS["text"],
            font=("TkDefaultFont", fs("label")),
        ).pack(side="left", padx=(12, 0))

        self._station_var = tk.StringVar(value=self._station)
        self._station_var.trace_add("write", self._on_station_change)
        tk.Entry(
            inp_frame, textvariable=self._station_var,
            font=("TkDefaultFont", fs("label")), width=28,
            bg=COLORS["card"], fg=COLORS["text"],
            insertbackground=COLORS["text"], relief="flat",
            highlightthickness=1, highlightbackground=COLORS["border"],
            highlightcolor=COLORS["running"],
        ).pack(side="left", padx=6)

        # ── Action bar (surface bg + bottom border) ───────────────────
        _act_wrap = tk.Frame(self, bg=COLORS["surface"])
        _act_wrap.pack(fill="x")
        act_frame = tk.Frame(_act_wrap, bg=COLORS["surface"], pady=4)
        act_frame.pack(fill="x", padx=10)
        tk.Frame(_act_wrap, height=1, bg=COLORS["border"]).pack(fill="x")

        # Disabled by default — aktif setelah SN diisi (OPTIMIZE #19)
        self._toggle_btn = tk.Button(
            act_frame, text="▶  Start",
            command=self._toggle_run,
            bg="#2980b9", fg="white", relief="flat",
            font=("TkDefaultFont", fs("button")),
            padx=10, pady=4, cursor="hand2",
            state="disabled",
        )
        self._toggle_btn.pack(side="left")

        tk.Frame(act_frame, width=1, bg=COLORS["border"]).pack(side="left", fill="y", padx=8, pady=4)

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
            bg=COLORS["surface"], fg=COLORS["text"],
            font=("TkDefaultFont", fs("small")),
        ).pack(side="right")

        # ── Test list ────────────────────────────────────────────────
        self._list_panel = TestListPanel(
            self, scale=self._scale, controller=self._controller,
            bg=COLORS["bg"],
        )
        self._list_panel.pack(fill="both", expand=True, padx=10, pady=(0, 8))
        self._list_panel.load_tests(self._tests)

    def _refresh_project_label(self):
        if hasattr(self, "_proj_lbl"):
            self._proj_lbl.config(
                text=f"  [{self._project.upper()}]" if self._project else ""
            )

    def _update_start_btn(self):
        """Enable/disable tombol Start berdasarkan isi SN field (OPTIMIZE #19)."""
        if not hasattr(self, "_toggle_btn") or not hasattr(self, "_device_var"):
            return
        sn = self._device_var.get().strip()
        if sn:
            self._toggle_btn.config(state="normal")
        else:
            # Jangan disable saat test sedang berjalan (tombol jadi Stop)
            if not self._controller.is_seq_running():
                self._toggle_btn.config(state="disabled", text="▶  Start", bg="#2980b9")

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
        # Buat sesi baru di DB (synchronous — single INSERT, cepat)
        self._reset_db_session()
        self._status_var.set("Running...")
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
            self._status_var.set(f"STOP - NG: {ng_names}")
            self._finalize_db_session("NG")
        elif len(ok_rows) == len(rows):
            self._status_var.set("Semua test PASS")
            self._finalize_db_session("OK")
        else:
            self._status_var.set("Selesai")
            self._finalize_db_session(None)

        self._toggle_btn.config(text="▶  Start", bg="#2980b9")

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _auto_connect(self):
        """Scan semua koneksi dari config.json, coba connect tiap-tiap port."""
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
                ok = False
                try:
                    ok = sm.connect(name)
                except Exception as e:
                    self.after(0, lambda n=name, e=e:
                        log.warning("[serial] connect(%r) error: %s", n, e))
                status = f"OK [{found}]" if ok else f"NG (cari: {dev_name!r})"
                self.after(0, lambda n=name, s=status:
                    log.info("[serial] %s: %s", n, s))

        threading.Thread(target=_do, daemon=True).start()

    def _on_device_change(self, *_):
        """Dipanggil saat device_id berubah — siapkan session baru (background thread)."""
        test_loader.update_context({"device_id": self._device_var.get()})
        # FIX #4: DB I/O (find_open_session) dipindah ke background thread
        threading.Thread(
            target=self._new_db_session, kwargs={"force_new": False}, daemon=True
        ).start()

    def _on_station_change(self, *_):
        self._station = self._station_var.get()
        test_loader.update_context({"station": self._station})
        self._save_tasks()

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

    def _open_commissioning(self):
        CommissioningDialog(self)

    def _open_add_test(self):
        AddTestDialog(self, on_add=self._add_test, current_project=self._project)

    def _add_test(self, item, module_name: str = ""):
        new_proj = module_project(module_name)
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

        if new_proj and self._project != new_proj:
            self._project = new_proj
            self._refresh_project_label()
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
        """Tutup session lama lalu buat session baru (force_new, synchronous)."""
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
        Siapkan LocalServerUploader untuk device saat ini.

        force_new=False (saat SN berubah, dipanggil dari background thread):
          Cari session terbuka via REST API, resume jika ada. — FIX #4.

        force_new=True (saat Start ditekan):
          Selalu buat session baru via REST API.
        """
        db_cfg = self._load_db_config()
        if not db_cfg.get("enabled", True):
            self._controller._uploader = None
            return

        device_id = self._device_var.get().strip() if hasattr(self, "_device_var") else ""
        url       = db_cfg.get("server_url", "http://localhost:5001")

        try:
            from db_uploader import LocalServerUploader, LocalServerConfig
            uploader = LocalServerUploader(
                config=LocalServerConfig(base_url=url),
                station=self._station,
                device_id=device_id,
                project=self._project,
            )
            if force_new:
                sid = uploader.new_session()
                if sid:
                    log.info("DB: session baru #%d (device=%r)", sid, device_id)
                else:
                    log.warning("DB: gagal buat session di %s", url)
            else:
                sid = self._find_open_session_server(url, device_id)
                if sid:
                    uploader.set_session_id(sid)
                    log.info("DB: resume session #%d (device=%r)", sid, device_id)
                # else: lazy — dibuat saat upload pertama

            self._controller._uploader = uploader

        except Exception as e:
            log.warning("Gagal init DB uploader: %s", e)
            self._controller._uploader = None

    @staticmethod
    def _find_open_session_server(base_url: str, device_id: str) -> "int | None":
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
        uploader = self._controller._uploader
        if not uploader or not getattr(uploader, "_session_id", None):
            return
        sid = uploader._session_id
        # Jalankan di background agar tidak blokir UI
        def _do():
            ok = uploader.finalize_session(result)
            if ok:
                log.info("DB session #%d selesai: %s", sid, result or "?")
            else:
                log.warning("Gagal finalize DB session #%d", sid)
        threading.Thread(target=_do, daemon=True).start()

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

            if isinstance(data, list):
                names = data
            else:
                ver = data.get("version", 1)
                if ver > self._TASKS_VERSION:
                    log.warning(
                        "tasks.json version %d lebih baru dari yang didukung (%d), skip.",
                        ver, self._TASKS_VERSION,
                    )
                    return

                names         = data.get("tests", [])
                self._station = data.get("station", "")
                self._project = data.get("project", None)

                saved_preset = data.get("preset", "")
                if saved_preset and (saved_preset in DISPLAY_PRESETS
                                     or saved_preset == "Custom"):
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

            if not self._project:
                self._project = detect_project(self._test_names)

            if self._project == "tm81":
                self._keepalive.start()

        except Exception as e:
            log.warning("Gagal load tasks.json: %s", e)


if __name__ == "__main__":
    try:
        app = App()
        app.mainloop()
    except Exception:
        import traceback
        traceback.print_exc()
        input("Tekan Enter untuk keluar...")