import tkinter as tk
from tkinter import ttk
import random
from config import C

class TaskPickerDialog(tk.Toplevel):
    def __init__(self, parent, registry, desc, defaults):
        super().__init__(parent)
        self.result   = None
        self._parent  = parent
        
        self.registry = registry
        self.desc     = desc
        self.defaults = defaults

        # Ukuran dialog tetap proporsional untuk layar 1024x600
        W, H = 500, 400 
        px = parent.winfo_rootx() + (parent.winfo_width()  - W) // 2
        py = parent.winfo_rooty() + (parent.winfo_height() - H) // 2
        self.geometry(f"{W}x{H}+{px}+{py}")
        self.resizable(False, False)
        self.configure(bg=C["surface"])

        self.transient(parent)
        self.overrideredirect(True)
        self.attributes("-topmost", True)

        self._build()
        self._add_drag()
        self.update_idletasks()
        self.deiconify()
        self.lift()
        self.after(10, self._safe_grab)

    def _safe_grab(self):
        try:
            self.grab_set()
            self.bind("<Escape>", lambda e: self.destroy())
        except Exception:
            self.after(50, self._safe_grab)

    def _add_drag(self):
        self._drag_x, self._drag_y = 0, 0
    def _drag_start(self, e):
        self._drag_x, self._drag_y = e.x, e.y
    def _drag_move(self, e):
        dx, dy = e.x - self._drag_x, e.y - self._drag_y
        self.geometry(f"+{self.winfo_x() + dx}+{self.winfo_y() + dy}")

    def _build(self):
        # --- 1. Title Bar (Tetap di atas, tidak ikut di-scroll) ---
        titlebar = tk.Frame(self, bg=C["accent"])
        titlebar.pack(fill="x")

        tk.Label(titlebar, text="  Tambah Task Baru",
                 bg=C["accent"], fg="white",
                 font=("Segoe UI", 11, "bold"), pady=10).pack(side="left")

        btn_close = tk.Label(titlebar, text=" ✕ ",
                             bg=C["accent"], fg="white",
                             font=("Segoe UI", 12, "bold"),
                             padx=10, pady=10, cursor="hand2")
        btn_close.pack(side="right")
        btn_close.bind("<Button-1>", lambda e: self.destroy())
        
        titlebar.bind("<ButtonPress-1>", self._drag_start)
        titlebar.bind("<B1-Motion>", self._drag_move)

        # --- 2. Kontainer Utama untuk Scroll ---
        container = tk.Frame(self, bg=C["surface"])
        container.pack(fill="both", expand=True, padx=2, pady=5)

        # Scrollbar dengan gaya kustom
        sb = ttk.Scrollbar(container, orient="vertical")
        sb.pack(side="right", fill="y")

        # Canvas sebagai viewport
        self.canvas = tk.Canvas(container, bg=C["surface"], 
                                highlightthickness=0, yscrollcommand=sb.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        sb.config(command=self.canvas.yview)

        # Frame internal yang menampung kartu-kartu task
        self.inner_frame = tk.Frame(self.canvas, bg=C["surface"])
        self.canvas_window = self.canvas.create_window((0, 0), window=self.inner_frame, anchor="nw")

        # Logic Resizing & ScrollRegion
        self.inner_frame.bind("<Configure>", self._on_frame_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        
        # Bind MouseWheel
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind_all("<Button-4>", self._on_mousewheel)
        self.canvas.bind_all("<Button-5>", self._on_mousewheel)

        # --- 3. Mengisi Daftar Task ---
        tk.Label(self.inner_frame, text="Pilih jenis task untuk ditambahkan:",
                 bg=C["surface"], fg=C["sub"],
                 font=("Segoe UI", 9), pady=10).pack(fill="x")

        for cls in self.registry:
            self._card(cls)

    def _on_frame_configure(self, event):
        # Update area scroll saat konten bertambah
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_configure(self, event):
        # Pastikan lebar inner_frame mengikuti lebar canvas
        self.canvas.itemconfig(self.canvas_window, width=event.width)

    def _on_mousewheel(self, event):
        # Dukungan scroll untuk Windows/MacOS (delta) dan Linux (Button 4/5)
        if event.num == 4: self.canvas.yview_scroll(-1, "units")
        elif event.num == 5: self.canvas.yview_scroll(1, "units")
        else: self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")

    def _card(self, cls):
        color = cls.COLOR
        card = tk.Frame(self.inner_frame, bg=C["card"], cursor="hand2")
        card.pack(fill="x", padx=15, pady=4)

        badge = tk.Label(card, text=cls.ICON, bg=color, fg="white",
                         font=("Segoe UI", 10, "bold"), width=5, pady=12)
        badge.pack(side="left")

        info = tk.Frame(card, bg=C["card"])
        info.pack(side="left", fill="x", expand=True, padx=12, pady=8)

        tk.Label(info, text=cls.NAME, bg=C["card"], fg=C["text"],
                 font=("Segoe UI", 10, "bold"), anchor="w").pack(fill="x")

        tk.Label(info, text=self.desc.get(cls, ""), bg=C["card"], fg=C["sub"],
                 font=("Segoe UI", 8), anchor="w").pack(fill="x")

        def _hover(on, f=card):
            f.config(bg=C["card_hov"] if on else C["card"])
            for child in f.winfo_children():
                if isinstance(child, tk.Frame):
                    child.config(bg=C["card_hov"] if on else C["card"])
                elif not child.cget("bg") == color: # Jangan ubah warna badge
                    child.config(bg=C["card_hov"] if on else C["card"])

        def _pick():
            param = random.choice(self.defaults.get(cls, [""]))
            self.result = cls(param)
            self.destroy()

        # Bind semua elemen card agar responsif saat diklik/hover
        for w in [card, badge, info] + list(info.winfo_children()):
            w.bind("<Button-1>", lambda e: _pick())
            w.bind("<Enter>", lambda e: _hover(True))
            w.bind("<Leave>", lambda e: _hover(False))


# ══════════════════════════════════════════════════════════════════
#  MODE SANDBOX / TESTING DIALOG (Tampil Saja, Tanpa App Utama)
# ══════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    import sys
    import os
    
    # Supaya bisa baca config.py kalau di-run dari dalam folder ui
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

    # 1. Buat beberapa Task Bohongan hanya untuk mengetes UI Dialog
    class FakeTask1: NAME, ICON, COLOR = "Download Sistem", "DL", "#3B9EFF"
    class FakeTask2: NAME, ICON, COLOR = "Training AI Modul", "AI", "#E040FB"
    class FakeTask3: NAME, ICON, COLOR = "Backup Data Server", "BK", "#3DD68C"
    class FakeTask4: NAME, ICON, COLOR = "Scan Bluetooth", "BT", "#00BCD4"
    class FakeTask5: NAME, ICON, COLOR = "Kirim Perintah PING", "CMD", "#FF5722"
    class FakeTask6: NAME, ICON, COLOR = "Update Firmware", "FW", "#FFB347"
    class FakeTask7: NAME, ICON, COLOR = "Hapus Cache", "DEL", "#FF6B6B"

    # 2. Masukkan ke dalam Registry Bohongan (Sengaja dibanyakin agar bisa di-scroll)
    TEST_REG = [FakeTask1, FakeTask2, FakeTask3, FakeTask4, FakeTask5, FakeTask6, FakeTask7]
    
    TEST_DESC = {
        FakeTask1: "Mengunduh file sistem terbaru dari server.",
        FakeTask2: "Melatih model jaringan saraf tiruan.",
        FakeTask3: "Mencadangkan direktori root ke Cloud.",
        FakeTask4: "Mencari perangkat BLE di sekitar.",
        FakeTask5: "Mengirimkan data serial via Modbus.",
        FakeTask6: "Pembaruan OTA untuk mikrokontroler.",
        FakeTask7: "Membersihkan memori sampah di lokal."
    }
    
    # Beri nilai parameter kosong agar tidak error saat diklik
    TEST_DEF = {t: [""] for t in TEST_REG}

    # 3. Setup Tkinter Utama Bayangan
    root = tk.Tk()
    root.title("Simulasi App Utama")
    root.geometry("800x600")
    root.configure(bg=C["bg"])
    
    tk.Label(root, text="[ INI ADALAH APLIKASI UTAMA ]\n\nDialog akan muncul di atas ini.\nCoba gulir (scroll) daftarnya, lalu klik salah satu menu.", 
             bg=C["bg"], fg=C["sub"], font=("Segoe UI", 12)).pack(expand=True)

    # 4. Fungsi pembungkus untuk memanggil dialog
    def show_dialog():
        print("Membuka Dialog Pilihan Task...")
        dlg = TaskPickerDialog(root, TEST_REG, TEST_DESC, TEST_DEF)
        
        # Tahan program di sini sampai dialog ditutup
        root.wait_window(dlg)
        
        # Cek hasil pilihan
        if dlg.result:
            print(f"\n[HASIL] Anda memilih: {dlg.result.__class__.__name__}")
        else:
            print("\n[HASIL] Dialog ditutup tanpa memilih (Batal).")
            
        # Matikan program setelah dialog tertutup
        root.quit()

    # Tampilkan dialog 0.5 detik setelah jendela utama terbuka
    root.after(500, show_dialog)
    root.mainloop()