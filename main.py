import sys
import os

# Memastikan direktori root masuk ke system path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ui.app import App
from registry import TASK_REGISTRY, TASK_DESC, TASK_DEFAULTS

if __name__ == "__main__":
    
    # 1. Inisialisasi UI dengan memberikan daftar Worker yang sebenarnya
    app = App(
        task_registry=TASK_REGISTRY,
        task_desc=TASK_DESC,
        task_defaults=TASK_DEFAULTS
    )
    
    # 2. UI akan terbuka KOSONG MELOMPONG. 
    # Baru saat tombol "Tambah Task" ditekan, list menu akan muncul dari registry di atas.
    app.mainloop()