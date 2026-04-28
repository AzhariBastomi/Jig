import tkinter as tk
from tkinter import ttk, messagebox
import random
from config import C
from ui.recycle_view import RecycleView
from ui.recycle_item import RecycleViewItem
from ui.dialogs import TaskPickerDialog
from utils import _lighten

class App(tk.Tk):
    W, H = 1024, 600

    # SEKARANG APP MENERIMA DATA DARI LUAR
    def __init__(self, task_registry=None, task_desc=None, task_defaults=None):
        super().__init__()
        self.task_registry = task_registry or []
        self.task_desc     = task_desc or {}
        self.task_defaults = task_defaults or {}
        
        self.title("Task Manager")
        self.configure(bg=C["bg"])

        self.geometry(f"{self.W}x{self.H}+0+0")
        self.resizable(False, False)

        self.bind("<Escape>", lambda e: self.destroy())
        self.bind("<F11>",    lambda e: self.attributes("-fullscreen",
                                not self.attributes("-fullscreen")))
        self.attributes("-fullscreen", True)

        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("Vertical.TScrollbar",
                        background=C["card"], troughcolor=C["bg"],
                        bordercolor=C["bg"], arrowcolor=C["sub"])

        self._build()

    def _build(self):
        self._header()
        self._toolbar()
        self.rv = RecycleView(self)
        self.rv.pack(fill="both", expand=True)
        self._statusbar()

    def _header(self):
        hdr = tk.Frame(self, bg=C["surface"], pady=10)
        hdr.pack(fill="x")

        left = tk.Frame(hdr, bg=C["surface"])
        left.pack(side="left", padx=20)

        tk.Label(left, text="Task Manager",
                 bg=C["surface"], fg=C["text"],
                 font=("Segoe UI", 16, "bold")).pack(anchor="w")
        tk.Label(left, text="RecycleView  Tkinter OOP  —  1024×600",
                 bg=C["surface"], fg=C["sub"],
                 font=("Segoe UI", 8)).pack(anchor="w")

        self.lbl_summary = tk.Label(hdr, text="",
                                    bg=C["surface"], fg=C["sub"],
                                    font=("Segoe UI", 9), padx=20)
        self.lbl_summary.pack(side="right")

    def _toolbar(self):
        bar = tk.Frame(self, bg=C["bg"], pady=8)
        bar.pack(fill="x", padx=16)

        self._tbtn(bar, "+  Tambah Task",   C["accent"], self._open_picker).pack(side="left")
        self._tbtn(bar, "  Jalankan Semua", "#3B9EFF",   self._start_all  ).pack(side="left", padx=(8, 0))
        self._tbtn(bar, "  Reset Semua",    C["warn"],   self._reset_all  ).pack(side="left", padx=(8, 0))
        self._tbtn(bar, "  Hapus Semua",    C["err"],    self._clear_all  ).pack(side="left", padx=(8, 0))

        self._tbtn(bar, "  Keluar  [Esc]",  "#444466",   self.destroy     ).pack(side="right")

    def _tbtn(self, parent, text, color, cmd):
        b = tk.Label(parent, text=text, bg=color, fg="white",
                     font=("Segoe UI", 9, "bold"),
                     padx=14, pady=7, cursor="hand2")
        b.bind("<Button-1>", lambda e: cmd())
        b.bind("<Enter>",    lambda e: b.config(bg=_lighten(color)))
        b.bind("<Leave>",    lambda e: b.config(bg=color))
        return b

    def _statusbar(self):
        self._sv = tk.StringVar(value="Siap.")
        bar = tk.Frame(self, bg="#0A0A14", pady=4)
        bar.pack(fill="x", side="bottom")

        tk.Label(bar, textvariable=self._sv,
                 bg="#0A0A14", fg=C["sub"],
                 font=("Segoe UI", 8), padx=14).pack(side="left")

        tk.Label(bar, text="F11: Toggle Fullscreen  |  Esc: Keluar",
                 bg="#0A0A14", fg="#44445A",
                 font=("Segoe UI", 8), padx=14).pack(side="right")

    def _force_redraw_all(self):
        self.update_idletasks()
        for w in self.rv.items():
            w._draw()
        self.rv.cv.configure(scrollregion=self.rv.cv.bbox("all"))

    def _add_task(self, task):
        w = RecycleViewItem(self.rv.inner, task, app_ref=self)
        self.rv.add(w)
        self.update_idletasks()
        w._tick(task.progress)
        self.after(50, w._draw)

    def _open_picker(self):
        # MENGOPER DATA REGISTRY KE DIALOG
        dlg = TaskPickerDialog(self, self.task_registry, self.task_desc, self.task_defaults)
        self.wait_window(dlg)
        
        self.attributes("-fullscreen", True)
        self.lift()
        self.focus_force()
        if dlg.result:
            self._add_task(dlg.result)
            self.refresh_status()
            self.after(100, self._force_redraw_all)

    def _start_all(self):
        for w in self.rv.items():
            if w.task.progress < 100:
                w._do_start()

    def _reset_all(self):
        for w in self.rv.items():
            w._do_reset()

    def _clear_all(self):
        if messagebox.askyesno("Konfirmasi", "Hapus semua task?"):
            self.rv.clear()
            self.refresh_status()

    def refresh_status(self):
        items = self.rv.items()
        total = len(items)
        done  = sum(1 for i in items if i.task.progress >= 100)
        run   = sum(1 for i in items if i.task.running)
        antri = total - done - run
        txt = f"Total: {total}  |  Selesai: {done}  |  Berjalan: {run}  |  Antri: {antri}"
        self._sv.set(txt)
        self.lbl_summary.config(
            text=f"Selesai {done}/{total}  |  {run} berjalan"
        )


# ══════════════════════════════════════════════════════════════════
#  MODE SANDBOX / TESTING UI (Dengan Registry Palsu)
# ══════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    import sys
    import os
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

    class FakeTask:
        NAME = "UI Test Task"
        ICON = "T"
        COLOR = "#E040FB"
        def __init__(self, label="", start_progress=0):
            self.label = label or "Test Tampilan"
            self.progress = start_progress
            self.running = False
            self._stop = False
        def detail_info(self): return "Murni animasi UI."
        def reset(self):
            self._stop, self.running, self.progress = True, False, 0
        def run(self, on_tick, on_done):
            if self.running or self.progress >= 100: return
            self.running, self._stop = True, False
            def _animate():
                if self._stop: return
                if self.progress < 100:
                    self.progress += 2
                    on_tick(self.progress)
                    app.after(50, _animate)
                else:
                    self.running = False
                    on_done()
            _animate()

    # Bikin Registry Bohongan
    FAKE_REG = [FakeTask]
    FAKE_DESC = {FakeTask: "Klik ini untuk menambah animasi tes."}
    FAKE_DEF = {FakeTask: ["Tes Start", "Tes Jalan"]}

    print("Membuka UI Sandbox (UI Kosongan + Registry Bohongan)...")
    app = App(task_registry=FAKE_REG, task_desc=FAKE_DESC, task_defaults=FAKE_DEF)
    app.mainloop()