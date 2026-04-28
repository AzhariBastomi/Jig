import random
import threading
import time

class BaseTask:
    NAME  = "Base Task"
    ICON  = "X"
    COLOR = "#7B68EE"
    LAYOUT_TYPE = "progress" 

    def __init__(self, label=""):
        self.label    = label or self.NAME
        self.progress = 0
        self.running  = False
        self._stop    = False

    def _step_duration(self): return 0.1
    def _increment(self): return random.randint(2, 6)

    def detail_info(self):
        return (
            f"{self.ICON}  {self.label}\n"
            f"---------------------\n"
            f"Tipe     : {self.NAME}\n"
            f"Progress : {self.progress}%\n"
            f"Status   : {self._status_text()}"
        )

    def _status_text(self):
        if self.progress >= 100: return "Selesai"
        if self.running:         return "Berjalan"
        if self.progress > 0:    return "Dijeda"
        return "Belum mulai"

    def reset(self):
        self._stop    = True
        self.running  = False
        self.progress = 0
        print(f"\n[↺] {self.ICON} | RESET: {self.label}", flush=True)

    def run(self, on_tick, on_done):
        if self.running or self.progress >= 100:
            return
        self._stop   = False
        self.running = True

        print(f"\n[▶] {self.ICON} | MEMULAI TASK: {self.label}", flush=True)

        def _worker():
            last_print = -1
            while not self._stop and self.progress < 100:
                inc = self._increment()
                self.progress = min(self.progress + inc, 100)
                on_tick(self.progress)
                
                # --- LOGIKA PRINT TERMINAL (TIDAK SPAM) ---
                # Hanya print ke terminal setiap kelipatan 5% agar tidak terlalu cepat
                if self.progress - last_print >= 5 or self.progress == 100:
                    bar = "█" * (self.progress // 5) + "░" * (20 - (self.progress // 5))
                    # \r membuat teks menimpa baris yang sama di terminal
                    print(f"\r    [{bar}] {self.progress:3d}% — {self.label[:20]}", end="", flush=True)
                    last_print = self.progress

                time.sleep(self._step_duration())
                
            self.running = False
            
            # --- CEK HASIL AKHIR ---
            if self.progress >= 100:
                print(f"\n[✔] {self.ICON} | SELESAI: {self.label}", flush=True)
                on_done()
            elif self._stop:
                print(f"\n[■] {self.ICON} | DIHENTIKAN: {self.label} pada {self.progress}%", flush=True)

        threading.Thread(target=_worker, daemon=True).start()