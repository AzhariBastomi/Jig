import sys
import os
from ._base_task import BaseTask
from config import BT_TARGET_NAME

# Pastikan dapat melakukan import dari 'Lib' di direktori terluar
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from Lib.bluetooth_scan import BluetoothScanner

class BluetoothScanTask(BaseTask):
    NAME  = "Bluetooth Scan"
    ICON  = "BT"
    COLOR = "#00BCD4"

    def __init__(self, label=""):
        super().__init__(label=label or f"BT Scan: cari '{BT_TARGET_NAME}'")
        self.found_devices  = []
        self.target_device  = None
        self.error_msg      = ""
        self._scanner       = None
        self.scan_duration  = 10

    def run(self, on_tick, on_done):
        if self.running or self.progress >= 100:
            return
        self._stop          = False
        self.running        = True
        self.found_devices  = []
        self.target_device  = None
        self.error_msg      = ""

        print(f"[BT] ══════════════════════════════════════", flush=True)
        print(f"[BT] Memulai scan Bluetooth (hcitool scan --flush)", flush=True)
        print(f"[BT] Target  : '{BT_TARGET_NAME}'", flush=True)
        print(f"[BT] Mode    : Stop otomatis jika target ditemukan", flush=True)
        print(f"[BT] ══════════════════════════════════════", flush=True)

        def _on_device(mac, name):
            self.found_devices.append({"mac": mac, "name": name})
            print(f"[BT] Ditemukan  : {mac}  —  {name}", flush=True)

            if BT_TARGET_NAME.lower() in name.lower():
                self.target_device = {"mac": mac, "name": name}
                print(f"[BT] ✓ TARGET KETEMU! Menghentikan scan...", flush=True)
                print(f"[BT]   Nama : {name}", flush=True)
                print(f"[BT]   MAC  : {mac}", flush=True)
                if self._scanner:
                    self._scanner.stop()

        def _on_progress(pct, found):
            if self._stop:
                return
            self.progress = min(pct, 99)
            on_tick(self.progress)
            bar = "█" * (pct // 5) + "░" * (20 - pct // 5)
            print(f"\r[BT] [{bar}] {pct:3d}%  ({found} device)", end="", flush=True)

        def _on_done(devices):
            self.found_devices = devices
            self.progress      = 100
            self.running       = False
            on_tick(100)
            on_done()
            print(f"\n[BT] ══ Hasil Scan ══════════════════════", flush=True)
            if self.target_device:
                print(f"[BT] STATUS  : ✓ TARGET DITEMUKAN", flush=True)
                print(f"[BT] Nama    : {self.target_device['name']}", flush=True)
                print(f"[BT] MAC     : {self.target_device['mac']}", flush=True)
            else:
                print(f"[BT] STATUS  : ✗ Target '{BT_TARGET_NAME}' tidak ditemukan", flush=True)
            print(f"[BT] Total scan : {len(devices)} perangkat", flush=True)
            if devices:
                print(f"[BT] Semua device:", flush=True)
                for i, d in enumerate(devices, 1):
                    mark = " ← TARGET" if d['mac'] == (self.target_device or {}).get('mac') else ""
                    print(f"[BT]   {i:2d}. {d['mac']}  —  {d['name']}{mark}", flush=True)
            print(f"[BT] ══════════════════════════════════════", flush=True)

        def _on_error(msg):
            self.error_msg = msg
            self.running   = False
            self.progress  = 100
            on_tick(100)
            on_done()
            print(f"\n[BT] ERROR: {msg}", flush=True)

        self._scanner = BluetoothScanner(
            on_device=_on_device,
            on_progress=_on_progress,
            on_done=_on_done,
            on_error=_on_error,
            flush=True,
            scan_duration=self.scan_duration,
        )
        self._scanner.start()

    def reset(self):
        if self._scanner:
            self._scanner.stop()
            print(f"[BT] Scan direset.", flush=True)
        self._scanner      = None
        self.found_devices = []
        self.target_device = None
        self.error_msg     = ""
        self._stop         = True
        self.running       = False
        self.progress      = 0

    def detail_info(self):
        if self.error_msg:
            return (
                f"[{self.ICON}] {self.label}\n"
                f"---------------------\n"
                f"Status : ERROR\n\n"
                f"{self.error_msg}"
            )
        n = len(self.found_devices)
        lines = [
            f"[{self.ICON}] {self.label}",
            f"---------------------",
            f"Target    : {BT_TARGET_NAME}",
            f"Progress  : {self.progress}%",
            f"Status    : {self._status_text()}",
            f"Scan      : {n} perangkat ditemukan",
            f"",
        ]
        if self.target_device:
            lines += [
                f"✓ TARGET DITEMUKAN:",
                f"  Nama : {self.target_device['name']}",
                f"  MAC  : {self.target_device['mac']}",
                f"",
            ]
        elif self.progress >= 100:
            lines.append(f"✗ Target '{BT_TARGET_NAME}' tidak ditemukan.")

        if self.found_devices:
            lines.append("Semua Perangkat Terdeteksi:")
            for i, d in enumerate(self.found_devices, 1):
                mark = " ← TARGET" if self.target_device and d['mac'] == self.target_device['mac'] else ""
                lines.append(f"  {i:2d}. {d['mac']}  —  {d['name']}{mark}")
        return "\n".join(lines)