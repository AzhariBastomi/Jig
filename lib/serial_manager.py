"""
serial_manager.py - Multi-connection serial manager.

Mendukung beberapa port bersamaan (misalnya STLink + UART device).
Konfigurasi dibaca dari config.json di root project.

Cara pakai:
    import serial_manager as sm

    # Koneksi default (diatur di config.json -> serial.default)
    sm.connect()
    resp = sm.send_and_wait("TEST_LED")

    # Koneksi bernama
    sm.connect("stlink")
    sm.connect("uart")
    resp = sm.send_and_wait("TEST_COMM", conn="uart")

    sm.disconnect("uart")
    sm.disconnect_all()
"""

from __future__ import annotations
import logging
import os, sys, json
from typing import Optional
from serial_comm import SerialComm, SerialConfig, FrameParser, RawLineParser, TM81Parser

_log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Baca config.json
# ---------------------------------------------------------------------------

def _load_json() -> dict:
    path = os.path.join(os.path.dirname(__file__), "..", "json", "config.json")
    try:
        with open(os.path.abspath(path)) as f:
            return json.load(f).get("serial", {})
    except Exception:
        return {}

_CFG = _load_json()

# Nama koneksi default ("uart" jika tidak diset)
DEFAULT_CONN = _CFG.get("default", "uart")

# Dict semua konfigurasi koneksi dari config.json
_CONN_DEFS: dict[str, dict] = _CFG.get("connections", {})

# Fallback jika config.json tidak punya "connections" (format lama)
if not _CONN_DEFS:
    _CONN_DEFS = {
        DEFAULT_CONN: {
            "device_name": _CFG.get("device_name", "USB Serial"),
            "baudrate":    _CFG.get("baudrate",    115200),
            "timeout":     _CFG.get("timeout",     2.0),
        }
    }


def _make_parser(name: str):
    """Pilih parser berdasarkan field 'parser' di config.json.

    Config options per koneksi:
        parser      : "frame" | "crc" | "raw"   (default: "frame")
        frame_start : karakter awal frame         (default: "<")
        frame_end   : karakter akhir frame        (default: ">")
    """
    d     = _CONN_DEFS.get(name, {})
    kind  = d.get("parser", "frame")
    start = d.get("frame_start", "<").encode()
    end   = d.get("frame_end",   ">").encode()
    if kind == "raw":
        return RawLineParser()
    elif kind == "tm81":
        return TM81Parser(
            crc_type  = d.get("crc_type",  "crc32mpeg2"),
            crc_bytes = d.get("crc_bytes", 4),
            crc_bigend= d.get("crc_bigend", False),
        )
    else:
        return FrameParser(start=start, end=end)


def _direct_port(name: str) -> Optional[str]:
    """
    Kembalikan port langsung jika koneksi menggunakan port_windows / port_linux.
    Return None jika koneksi pakai device_name scan biasa.
    """
    d = _CONN_DEFS.get(name, {})
    if "port_windows" in d or "port_linux" in d:
        if sys.platform.startswith("win"):
            return d.get("port_windows")
        else:
            return d.get("port_linux")
    return None


def _make_config(name: str) -> SerialConfig:
    """Buat SerialConfig dari entry di config.json."""
    d = _CONN_DEFS.get(name, {})
    if not d:
        raise KeyError(f"Koneksi '{name}' tidak ditemukan di config.json")
    # Jika ada port langsung (bluetooth), device_name tidak dipakai untuk scan
    device_name = d.get("device_name", _direct_port(name) or "USB Serial")
    return SerialConfig(
        device_name    = device_name,
        baudrate       = d.get("baudrate",    115200),
        timeout        = d.get("timeout",     2.0),
        bytesize       = d.get("bytesize",    8),
        parity         = d.get("parity",      "N"),
        stopbits       = d.get("stopbits",    1),
        xonxoff        = d.get("xonxoff",     False),
        rtscts         = d.get("rtscts",      False),
        dsrdtr         = d.get("dsrdtr",      False),
        cmd_terminator = b'\n',
    )


# ---------------------------------------------------------------------------
# Singleton registry  {name: SerialComm}
# ---------------------------------------------------------------------------

_conns: dict[str, SerialComm] = {}


def get_comm(conn: str = None) -> Optional[SerialComm]:
    """Kembalikan SerialComm aktif untuk koneksi `conn`, atau None."""
    return _conns.get(conn or DEFAULT_CONN)


def is_connected(conn: str = None) -> bool:
    c = _conns.get(conn or DEFAULT_CONN)
    return c is not None and c.is_connected()


def list_connections() -> dict[str, bool]:
    """Return dict {name: is_connected} untuk semua koneksi yang didefinisikan."""
    result = {}
    for name in _CONN_DEFS:
        c = _conns.get(name)
        result[name] = (c is not None and c.is_connected())
    return result


# ---------------------------------------------------------------------------
# Connect / disconnect
# ---------------------------------------------------------------------------

def connect(conn: str = None, parser=None) -> bool:
    """Buka koneksi bernama conn. Jika sudah terhubung, return True."""
    name = conn or DEFAULT_CONN
    if is_connected(name):
        return True
    try:
        cfg = _make_config(name)
    except KeyError as e:
        _log.error("[serial_manager] %s", e)
        return False

    prs  = parser or _make_parser(name)
    comm = SerialComm(cfg, prs)
    # Jika ada port langsung (misal bluetooth), lewati device_name scan
    direct = _direct_port(name)
    ok   = comm.connect(port=direct)  # port=None -> auto-find via device_name
    if ok:
        _conns[name] = comm
        # Jika debug_rx=true di config.json, cetak semua data masuk ke terminal
        if _CONN_DEFS.get(name, {}).get("debug_rx", False):
            _register_debug_rx(comm, name)
    return ok


def _register_debug_rx(comm: SerialComm, name: str):
    """Daftarkan callback yang mencetak setiap frame yang masuk ke terminal."""
    def _on_data(frame):
        if frame.valid:
            payload = frame.payload.decode("utf-8", errors="replace").strip()
            _log.debug("[%s] RX: %r", name, payload)
        else:
            raw = frame.raw.decode("utf-8", errors="replace").strip()
            if raw:
                _log.debug("[%s] RX (raw): %r", name, raw)
    comm.on_data(_on_data)


def disconnect(conn: str = None):
    """Tutup koneksi bernama conn."""
    name = conn or DEFAULT_CONN
    c    = _conns.pop(name, None)
    if c:
        c.disconnect()


def disconnect_all():
    """Tutup semua koneksi aktif."""
    for name in list(_conns):
        disconnect(name)


# ---------------------------------------------------------------------------
# Send
# ---------------------------------------------------------------------------

def send(command: str, conn: str = None) -> bool:
    """Kirim command ke koneksi conn. Return False jika tidak connected."""
    c = _conns.get(conn or DEFAULT_CONN)
    if not c or not c.is_connected():
        return False
    return c.send(command)


def send_and_wait(command: str, conn: str = None, timeout: float = 5.0) -> str:
    """Kirim command, tunggu satu frame response, return payload string."""
    import threading
    c = _conns.get(conn or DEFAULT_CONN)
    if not c or not c.is_connected():
        return ""

    result = [None]
    done   = threading.Event()

    def on_frame(frame):
        if frame.valid:
            result[0] = frame.payload.decode("utf-8", errors="replace").strip()
        else:
            result[0] = ""
        done.set()

    c.on_data(on_frame)
    c.send(command)
    done.wait(timeout=timeout)

    c.off_data(on_frame)

    return result[0] or ""


# ---------------------------------------------------------------------------
# Backward compat
# ---------------------------------------------------------------------------

try:
    DEFAULT_CONFIG = _make_config(DEFAULT_CONN)
except KeyError as e:
    _log.error("[serial_manager] %s", e)
    DEFAULT_CONFIG = None
