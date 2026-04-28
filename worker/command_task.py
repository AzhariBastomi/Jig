import time
import threading
from ._base_task import BaseTask

class SendCommandTask(BaseTask):
    NAME  = "Send Command"
    ICON  = "CMD"
    COLOR = "#FF5722"  
    LAYOUT_TYPE = "button" 

    def __init__(self, command=""):
        super().__init__(label=f"Cmd: {command or 'PING 192.168.1.1'}")
        self.command = command or "PING 192.168.1.1"
        self.status_text = "Menunggu"
        self.result_color = "#8888AA" 

    def run(self, on_update):
        if self.running or self.status_text in ["OK", "NG"]: 
            return
        self.running = True
        self.status_text = "Mengirim..."
        self.result_color = "#3B9EFF" 
        
        print(f"\n[▶] CMD | MENGIRIM PERINTAH: {self.command}", flush=True)
        on_update()

        def _worker():
            time.sleep(2) 
            if self.running:
                self.status_text = "Menunggu Respon..."
                self.result_color = "#FFB347" 
                print(f"[⏳] CMD | MENUNGGU RESPON DARI ALAT: {self.command}", flush=True)
                on_update()

        threading.Thread(target=_worker, daemon=True).start()

    def stop(self, on_update):
        if self.running:
            self.running = False
            self.status_text = "Dibatalkan"
            self.result_color = "#FF6B6B"
            print(f"[■] CMD | DIBATALKAN OLEH USER: {self.command}", flush=True)
            on_update()

    def set_ok(self, on_update):
        self.running = False
        self.status_text = "OK (Sukses)"
        self.result_color = "#3DD68C" 
        print(f"[✔] CMD | HASIL 'OK' (SUKSES): {self.command}", flush=True)
        on_update()

    def set_ng(self, on_update):
        self.running = False
        self.status_text = "NG (Gagal)"
        self.result_color = "#FF6B6B" 
        print(f"[✖] CMD | HASIL 'NG' (GAGAL): {self.command}", flush=True)
        on_update()

    def reset(self, on_update=None):
        self.running = False
        self.status_text = "Menunggu"
        self.result_color = "#8888AA"
        print(f"\n[↺] CMD | DIRESET KE AWAL: {self.command}", flush=True)
        if on_update: on_update()