import tkinter as tk
from tkinter import messagebox
from config import C
from utils import _pill, _pcolor, _lighten

class RecycleViewItem(tk.Frame):
    def __init__(self, parent, task, app_ref, **kwargs):
        super().__init__(parent, bg=C["card"], **kwargs)
        self.task    = task
        self.app_ref = app_ref
        
        # Cari tahu tipe layout dari class task-nya, default 'progress'
        self.layout_type = getattr(self.task, "LAYOUT_TYPE", "progress")
        self._build()

    def _build(self):
        self.config(padx=14, pady=10)

        # KIRI: Frame Utama untuk Info
        self.left = tk.Frame(self, bg=C["card"])
        self.left.pack(side="left", fill="both", expand=True)

        # Baris 1: Icon + Judul
        r1 = tk.Frame(self.left, bg=C["card"])
        r1.pack(fill="x")

        tk.Label(r1, text=f" {self.task.ICON} ",
                 bg=self.task.COLOR, fg="white",
                 font=("Segoe UI", 10, "bold"),
                 padx=6, pady=3).pack(side="left")

        tk.Label(r1, text=self.task.label,
                 bg=C["card"], fg=C["text"],
                 font=("Segoe UI", 10, "bold"), anchor="w").pack(side="left", fill="x", expand=True, padx=(10, 0))

        # KANAN: Frame Utama untuk Tombol
        self.right = tk.Frame(self, bg=C["card"])
        self.right.pack(side="right", padx=(12, 0))

        # --- CABANG PEMBUATAN LAYOUT ---
        if self.layout_type == "progress":
            self._build_progress_layout(r1)
        elif self.layout_type == "button":
            self._build_button_layout(r1)

    # ══════════════════════════════════════════════════════════════════
    #  VERSI 1: LAYOUT PROGRESS BAR (Download, dll)
    # ══════════════════════════════════════════════════════════════════
    def _build_progress_layout(self, r1_frame):
        # Tambahan di Baris 1: Label Persentase
        self.lbl_pct = tk.Label(r1_frame, text="0%",
                                bg=C["card"], fg=C["err"],
                                font=("Segoe UI", 11, "bold"), width=5)
        self.lbl_pct.pack(side="right")

        # Baris 2 Kiri: Deskripsi Tipe
        tk.Label(self.left, text=self.task.NAME, bg=C["card"], fg=C["sub"],
                 font=("Segoe UI", 8), anchor="w").pack(fill="x", padx=2, pady=(2, 4))

        # Baris 3 Kiri: Canvas Progress Bar
        self.cv = tk.Canvas(self.left, height=8, bg=C["card"], highlightthickness=0, bd=0)
        self.cv.pack(fill="x", pady=(0, 4))
        self.cv.bind("<Configure>", self._draw)

        # Tombol Vertikal di Kanan
        self.btn_start = self._btn(self.right, "  Start  ", self.task.COLOR, self._do_start)
        self.btn_start.pack(pady=(0, 4))
        self._btn(self.right, "  Reset  ", C["warn"], self._do_reset).pack(pady=(0, 4))
        self._btn(self.right, "  Info   ", C["sub"],  self._do_info ).pack()

    # ══════════════════════════════════════════════════════════════════
    #  VERSI 2: LAYOUT TOMBOL OK/NG (Send Command)
    # ══════════════════════════════════════════════════════════════════
    def _build_button_layout(self, r1_frame):
        # Tambahan di Baris 1: Teks Status
        self.lbl_status = tk.Label(r1_frame, text=self.task.status_text,
                                   bg=C["card"], fg=self.task.result_color,
                                   font=("Segoe UI", 10, "bold"))
        self.lbl_status.pack(side="right")

        # Baris 2 Kiri: Deskripsi Command
        tk.Label(self.left, text=self.task.NAME, bg=C["card"], fg=C["sub"],
                 font=("Segoe UI", 8), anchor="w").pack(fill="x", padx=2, pady=(4, 8))

        # Tombol di Kanan (Mendatar / Vertikal tergantung selera, kita buat grid/pack)
        # Tombol Start/Stop
        self.btn_toggle = self._btn(self.right, "  Start  ", self.task.COLOR, self._cmd_toggle)
        self.btn_toggle.pack(fill="x", pady=(0, 4))
        
        # Tombol OK & NG bersebelahan
        row2 = tk.Frame(self.right, bg=C["card"])
        row2.pack(fill="x")
        self._btn(row2, " OK ", C["ok"], self._cmd_ok, width=3).pack(side="left", padx=(0, 2))
        self._btn(row2, " NG ", C["err"], self._cmd_ng, width=3).pack(side="right", padx=(2, 0))

    # ── FUNGSI HELPER TOMBOL ──────────────────────────────────────────
    def _btn(self, parent, text, color, cmd, width=8):
        b = tk.Label(parent, text=text, bg=color, fg="white",
                     font=("Segoe UI", 9, "bold"),
                     padx=8, pady=6, cursor="hand2", width=width)
        b.bind("<Button-1>", lambda e: cmd())
        b.bind("<Enter>",    lambda e: b.config(bg=_lighten(color)))
        b.bind("<Leave>",    lambda e: b.config(bg=color))
        return b

    def _draw(self, _=None):
        if self.layout_type != "progress": return
        self.cv.delete("all")
        w, h, r = self.cv.winfo_width(), self.cv.winfo_height(), self.cv.winfo_height() // 2
        _pill(self.cv, 0, 0, w, h, r, C["bar_bg"])
        fw = max(int(w * self.task.progress / 100), 0)
        if fw: _pill(self.cv, 0, 0, fw, h, r, _pcolor(self.task.progress))

    # ── LOGIKA LAYOUT GLOBAL (PROGRESS & BUTTON) ──
    def _do_start(self):
        if self.layout_type == "progress":
            self.task.run(on_tick=lambda v: self.app_ref.after(0, self._tick, v),
                          on_done=lambda:   self.app_ref.after(0, self._done))
        elif self.layout_type == "button":
            if not self.task.running and self.task.status_text not in ["OK", "NG"]:
                self.task.run(on_update=lambda: self.app_ref.after(0, self._refresh_cmd_ui))
        self.app_ref.refresh_status()

    def _do_reset(self):
        if self.layout_type == "progress":
            self.task.reset()
            self._tick(0)
        elif self.layout_type == "button":
            self.task.reset(on_update=lambda: self.app_ref.after(0, self._refresh_cmd_ui))

    def _do_info(self):
        messagebox.showinfo("Detail Task", self.task.detail_info())

    def _tick(self, v):
        self.task.progress = v
        # Hanya update teks persen jika layoutnya memang progress bar
        if self.layout_type == "progress":
            self.lbl_pct.config(text=f"{v}%", fg=_pcolor(v))
            self._draw()
        self.app_ref.refresh_status()

    def _done(self):
        # Hanya update teks 100% jika layoutnya progress bar
        if self.layout_type == "progress":
            self.lbl_pct.config(text="100%", fg=C["ok"])
            self._draw()
        self.app_ref.refresh_status()
        
    # ── LOGIKA LAYOUT BUTTON (CMD) ──
    def _refresh_cmd_ui(self):
        # Update teks status & warna
        self.lbl_status.config(text=self.task.status_text, fg=self.task.result_color)
        # Update tulisan tombol Start menjadi Stop jika sedang berjalan
        btn_text  = "  Stop  " if self.task.running else "  Start  "
        btn_color = C["err"] if self.task.running else self.task.COLOR
        self.btn_toggle.config(text=btn_text, bg=btn_color)
        # Re-bind animasi hover warna
        self.btn_toggle.bind("<Leave>", lambda e, c=btn_color: self.btn_toggle.config(bg=c))
        self.app_ref.refresh_status()

    def _cmd_toggle(self):
        if self.task.running: self.task.stop(on_update=lambda: self.app_ref.after(0, self._refresh_cmd_ui))
        else:                 self.task.run(on_update=lambda: self.app_ref.after(0, self._refresh_cmd_ui))

    def _cmd_ok(self):
        self.task.set_ok(on_update=lambda: self.app_ref.after(0, self._refresh_cmd_ui))

    def _cmd_ng(self):
        self.task.set_ng(on_update=lambda: self.app_ref.after(0, self._refresh_cmd_ui))