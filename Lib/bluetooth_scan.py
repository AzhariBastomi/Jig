"""
Lib/bluetooth_scan.py
─────────────────────
Module subprocess untuk Bluetooth scanning menggunakan hcitool.
Berjalan sebagai background thread dan memanggil callback saat ada update.

Penggunaan:
    from Lib.bluetooth_scan import BluetoothScanner

    def on_device(mac, name):
        print(f"Ditemukan: {mac} — {name}")

    def on_done(devices):
        print(f"Selesai. Total: {len(devices)} perangkat")

    def on_error(msg):
        print(f"Error: {msg}")

    scanner = BluetoothScanner(
        on_device=on_device,
        on_done=on_done,
        on_error=on_error,
        flush=True,         # --flush: hapus cache inquiry sebelum scan
        scan_duration=10,   # durasi scan dalam detik
    )
    scanner.start()
    # ... nanti bisa:
    scanner.stop()
"""

import subprocess
import threading
import re
import time


class BluetoothScanner:
    """
    Wrapper subprocess untuk `hcitool scan [--flush]`.

    Attributes
    ----------
    devices : list[dict]
        Daftar perangkat yang ditemukan.
        Setiap item: {"mac": str, "name": str}
    running : bool
        True selama scan sedang berjalan.
    """

    CMD_BASE    = ["sudo", "hcitool", "scan"]
    CMD_FLUSH   = ["sudo", "hcitool", "scan", "--flush"]
    TIMEOUT_SEC = 30   # batas maksimum subprocess

    def __init__(
        self,
        on_device=None,
        on_progress=None,
        on_done=None,
        on_error=None,
        flush: bool = True,
        scan_duration: int = 10,
    ):
        """
        Parameters
        ----------
        on_device    : callable(mac: str, name: str)
            Dipanggil setiap kali satu perangkat baru ditemukan.
        on_progress  : callable(pct: int, found: int)
            Dipanggil tiap detik dengan estimasi progress (0-100)
            dan jumlah perangkat yang sudah ditemukan.
        on_done      : callable(devices: list[dict])
            Dipanggil saat scan selesai (normal maupun error).
        on_error     : callable(message: str)
            Dipanggil jika terjadi error (hcitool tidak ada, bt off, dsb).
        flush        : bool
            Jika True, tambahkan --flush agar cache inquiry dihapus dulu.
        scan_duration: int
            Estimasi durasi scan dalam detik (untuk kalkulasi progress).
        """
        self.on_device    = on_device    or (lambda mac, name: None)
        self.on_progress  = on_progress  or (lambda pct, found: None)
        self.on_done      = on_done      or (lambda devices: None)
        self.on_error     = on_error     or (lambda msg: None)
        self.flush        = flush
        self.scan_duration = max(1, scan_duration)

        self.devices: list[dict] = []
        self.running  = False
        self._stop    = False
        self._proc    = None
        self._thread  = None

    # ──────────────────────────────────────────────
    #  Public API
    # ──────────────────────────────────────────────

    def start(self):
        """Mulai scan di background thread. Tidak blocking."""
        if self.running:
            return
        self.devices  = []
        self._stop    = False
        self.running  = True
        self._thread  = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        """Hentikan scan paksa (kill subprocess)."""
        self._stop = True
        if self._proc and self._proc.poll() is None:
            try:
                self._proc.kill()
            except Exception:
                pass
        self.running = False

    def is_running(self) -> bool:
        return self.running

    # ──────────────────────────────────────────────
    #  Internal
    # ──────────────────────────────────────────────

    def _run(self):
        cmd = self.CMD_FLUSH if self.flush else self.CMD_BASE

        try:
            self._proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,          # line-buffered
            )
        except FileNotFoundError:
            self.running = False
            self.on_error("hcitool tidak ditemukan. Pastikan bluez terinstall:\nsudo apt install bluez")
            self.on_done(self.devices)
            return
        except PermissionError:
            self.running = False
            self.on_error("Tidak ada izin menjalankan hcitool.\nCoba jalankan dengan sudo.")
            self.on_done(self.devices)
            return

        # Thread progress ticker (estimasi berdasarkan waktu)
        progress_thread = threading.Thread(target=self._progress_ticker, daemon=True)
        progress_thread.start()

        # Baca output baris per baris secara real-time
        try:
            for line in self._proc.stdout:
                if self._stop:
                    break
                self._parse_line(line.rstrip())
        except Exception as e:
            self.on_error(f"Error membaca output: {e}")

        # Tunggu proses selesai
        try:
            self._proc.wait(timeout=self.TIMEOUT_SEC)
        except subprocess.TimeoutExpired:
            self._proc.kill()

        # Cek stderr untuk error
        if not self._stop:
            stderr = self._proc.stderr.read().strip()
            if stderr and not self.devices:
                self.on_error(self._friendly_error(stderr))

        self.running = False
        self.on_progress(100, len(self.devices))
        self.on_done(self.devices)

    def _progress_ticker(self):
        """Estimasi progress berdasarkan waktu scan."""
        start = time.time()
        while self.running and not self._stop:
            elapsed = time.time() - start
            pct = min(int(elapsed / self.scan_duration * 95), 95)
            self.on_progress(pct, len(self.devices))
            time.sleep(0.5)

    def _parse_line(self, line: str):
        """
        Parse baris output hcitool scan.
        Format output:
            Scanning ...
            \tAA:BB:CC:DD:EE:FF\tDevice Name
        """
        # Lewati baris header
        if not line or line.startswith("Scanning"):
            return

        # Match baris device: tab + MAC + tab + nama
        match = re.match(
            r'^\s*([0-9A-Fa-f]{2}(?::[0-9A-Fa-f]{2}){5})\s+(.+)$',
            line
        )
        if match:
            mac  = match.group(1).strip().upper()
            name = match.group(2).strip() or "Unknown Device"

            # Hindari duplikat
            if not any(d["mac"] == mac for d in self.devices):
                device = {"mac": mac, "name": name}
                self.devices.append(device)
                self.on_device(mac, name)

    @staticmethod
    def _friendly_error(stderr: str) -> str:
        """Konversi pesan error teknis ke pesan yang lebih ramah."""
        s = stderr.lower()
        if "no such device" in s or "hci0" in s:
            return "Bluetooth adapter tidak ditemukan.\nPastikan Bluetooth aktif:\nsudo rfkill unblock bluetooth"
        if "connection refused" in s or "dbus" in s:
            return "Service Bluetooth tidak berjalan.\nJalankan:\nsudo systemctl start bluetooth"
        if "operation not permitted" in s:
            return "Tidak ada izin. Coba jalankan dengan sudo."
        if "device or resource busy" in s:
            return "Bluetooth sedang digunakan proses lain."
        return f"Error Bluetooth:\n{stderr[:200]}"


# ──────────────────────────────────────────────────────────────────
#  Standalone test (jalankan langsung: python3 Lib/bluetooth_scan.py)
# ──────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys

    print("=" * 50)
    print("  Bluetooth Scanner — hcitool scan --flush")
    print("=" * 50)

    found = []

    def on_dev(mac, name):
        print(f"  [+] {mac}  {name}")
        found.append(mac)

    def on_prog(pct, n):
        bar = "█" * (pct // 5) + "░" * (20 - pct // 5)
        print(f"\r  [{bar}] {pct:3d}%  ({n} device)", end="", flush=True)

    def on_done(devices):
        print(f"\n\n  Selesai. Ditemukan {len(devices)} perangkat.")
        for d in devices:
            print(f"    • {d['mac']}  —  {d['name']}")
        sys.exit(0)

    def on_err(msg):
        print(f"\n  [ERROR] {msg}")

    scanner = BluetoothScanner(
        on_device=on_dev,
        on_progress=on_prog,
        on_done=on_done,
        on_error=on_err,
        flush=True,
        scan_duration=10,
    )

    print("  Memulai scan... (Ctrl+C untuk berhenti)\n")
    scanner.start()

    try:
        while scanner.is_running():
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\n  Scan dihentikan.")
        scanner.stop()