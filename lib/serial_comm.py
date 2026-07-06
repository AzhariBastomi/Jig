"""
serial_comm.py - Serial Communication Library untuk JIG Test

Arsitektur
----------
  SerialConfig   - konfigurasi koneksi (hardcode per JIG)
  ParseResult    - hasil parsing satu frame data
  BaseParser     - interface parser
  FrameParser    - parsing berdasarkan start/end marker
  CRCParser      - parsing + validasi CRC
  SerialComm     - class utama: find port, connect, reader thread, send command

Cara pakai
----------
  from serial_comm import SerialComm, SerialConfig, FrameParser, CRCParser

  config = SerialConfig(device_name="Arduino")
  parser = FrameParser(start=b'<', end=b'>')
  comm   = SerialComm(config, parser)

  comm.on_data(lambda result: print(result.payload))
  comm.connect()
  comm.send("TEST_LED")
"""

from __future__ import annotations

import serial
import serial.tools.list_ports
import threading
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Callable, Optional

# crccheck — library untuk berbagai algoritma CRC
from crccheck.crc import (
    Crc32Mpeg2,
    CrcKermit,
    Crc16,
    Crc16CcittFalse,
    Crc32,
    Crc8,
)

# Map nama string (dari config.json) ke class crccheck
_CRC_MAP = {
    "crc32mpeg2":     Crc32Mpeg2,       # TM81 IrDA
    "kermit":         CrcKermit,        # CRC-16/Kermit
    "crc16":          Crc16,            # CRC-16/IBM
    "crc16ccitt":     Crc16CcittFalse,  # CRC-16/CCITT-FALSE
    "crc32":          Crc32,            # CRC-32 standard
    "crc8":           Crc8,             # CRC-8
}


log = logging.getLogger(__name__)


# =============================================================================
# SerialConfig — semua setting koneksi di satu tempat
# =============================================================================

@dataclass
class SerialConfig:
    # --- Port discovery ---
    device_name: str  = "Arduino"        # substring yang dicari di port description

    # --- Serial parameters ---
    baudrate:    int  = 115200
    bytesize:    int  = serial.EIGHTBITS  # 5 | 6 | 7 | 8
    parity:      str  = serial.PARITY_NONE   # N | E | O | M | S
    stopbits:    float= serial.STOPBITS_ONE  # 1 | 1.5 | 2
    timeout:     float= 1.0              # read timeout (detik)

    # --- Flow control ---
    xonxoff:     bool = False            # software flow control (XON/XOFF)
    rtscts:      bool = False            # hardware flow control RTS/CTS
    dsrdtr:      bool = False            # hardware flow control DSR/DTR

    # --- Command format ---
    cmd_terminator: bytes = b'\n'        # ditambahkan di akhir setiap command


# =============================================================================
# ParseResult — hasil parsing satu frame
# =============================================================================

@dataclass
class ParseResult:
    raw:     bytes          # data mentah dari port
    payload: bytes          # isi data setelah header/footer/CRC dilepas
    valid:   bool           # True jika frame komplit dan CRC/marker cocok
    error:   str  = ""      # keterangan jika valid=False


# =============================================================================
# BaseParser — interface untuk semua parser
# =============================================================================

class BaseParser(ABC):
    """
    Override parse() untuk setiap strategi parsing.
    Reader thread memanggil feed(byte) satu byte per satu.
    Ketika satu frame komplit, on_frame(ParseResult) dipanggil.
    """

    def __init__(self):
        self._buf: bytearray = bytearray()
        self._on_frame: Optional[Callable[[ParseResult], None]] = None

    def set_frame_callback(self, fn: Callable[[ParseResult], None]):
        self._on_frame = fn

    def feed(self, byte: bytes):
        """Masukkan satu byte. Parser memutuskan kapan frame komplit."""
        self._buf += byte
        result = self.parse(self._buf)
        if result is not None:
            self._buf.clear()
            if self._on_frame:
                self._on_frame(result)

    @abstractmethod
    def parse(self, buf: bytearray) -> Optional[ParseResult]:
        """
        Return ParseResult jika buf berisi frame komplit, None jika belum.
        Jika return bukan None, buffer otomatis dikosongkan.
        """


# =============================================================================
# FrameParser — parsing berdasarkan start/end marker
# =============================================================================

class FrameParser(BaseParser):
    """
    Format: <START> payload <END>
    Contoh: b'<' ... b'>'  atau  b'STX' ... b'ETX'

    Jika include_markers=False (default), payload tidak menyertakan marker.
    """

    def __init__(self, start: bytes = b'<', end: bytes = b'>',
                 include_markers: bool = False):
        super().__init__()
        self.start           = start
        self.end             = end
        self.include_markers = include_markers

    def parse(self, buf: bytearray) -> Optional[ParseResult]:
        raw = bytes(buf)

        # Buang byte sebelum start marker
        si = raw.find(self.start)
        if si == -1:
            self._buf.clear()
            return None
        if si > 0:
            self._buf = bytearray(raw[si:])
            raw = bytes(self._buf)

        # Cari end marker setelah start
        ei = raw.find(self.end, len(self.start))
        if ei == -1:
            return None   # frame belum komplit

        frame   = raw[si : ei + len(self.end)]
        payload = raw[si + len(self.start) : ei]

        return ParseResult(
            raw     = frame,
            payload = payload if not self.include_markers else frame,
            valid   = True,
        )


# =============================================================================
# CRCParser — parsing + validasi CRC
# =============================================================================

class TM81Parser(BaseParser):
    """
    Protocol TM81 (IrDA via CH340), CRC via crccheck library.

    SEND frame:
        0xFF 0xFF | 0x01 0x0F 0x00 | LEN | 0x02 | CMD_ID | DATA | 0x03 | CRC(crc_bytes LE) | 0x04

    RECEIVE:
        ACK  : 0x11
        NAK  : 0x0F
        Frame: 0x01 0x0F CMD LEN 0x02 ... 0x03 CRC EOT

    Konfigurasi (dari config.json):
        crc_type   : nama algoritma CRC (lihat _CRC_MAP), default "crc32mpeg2"
        crc_bytes  : ukuran CRC dalam byte, default 4
        crc_bigend : urutan byte CRC, default False (little-endian)
    """

    ACK           = b""
    NAK           = b""
    EOT           = b""
    HEADER_PREFIX = b""

    def __init__(self, crc_type: str = "crc32mpeg2",
                 crc_bytes: int = 4, crc_bigend: bool = False):
        super().__init__()
        self._crc_cls    = _CRC_MAP.get(crc_type, Crc32Mpeg2)
        self._crc_bytes  = crc_bytes
        self._crc_bigend = crc_bigend

    def _calc_crc(self, data: bytes) -> int:
        return self._crc_cls.calc(data)

    def build_send_frame(self, cmd_id: int, data: bytes = b"") -> bytes:
        """Bangun frame TX lengkap untuk CMD_ID tertentu."""
        data_len  = len(data)
        cmd_len   = (12 + data_len).to_bytes(1, "little")
        cmd_bytes = (
            b"\x01\x0f\x00"
            + cmd_len
            + b""
            + cmd_id.to_bytes(1, "little")
            + data
            + b""
        )
        crc_val   = self._calc_crc(cmd_bytes)
        crc_b     = crc_val.to_bytes(self._crc_bytes,
                                     "big" if self._crc_bigend else "little")
        frame     = b"\xff\xff" + cmd_bytes + crc_b + b""
        hex_str   = " ".join(f"{b:02x}" for b in frame)
        print(f"[TM81 TX] cmd=0x{cmd_id:02x} crc={crc_val:#010x} len={len(frame)}B  {hex_str}",
              flush=True)
        return frame

    def parse(self, buf: bytearray) -> Optional[ParseResult]:
        raw = bytes(buf)

        # --- ACK ---
        if raw == self.ACK:
            print("[TM81 RX] ACK (0x11)", flush=True)
            self._buf.clear()
            return ParseResult(raw=raw, payload=b"", valid=True, error="ACK")

        # --- NAK ---
        if raw == self.NAK:
            print("[TM81 RX] NAK (0x0f)", flush=True)
            self._buf.clear()
            return ParseResult(raw=raw, payload=b"", valid=False, error="NAK")

        # --- Cari header 0x01 0x0F ---
        si = raw.find(self.HEADER_PREFIX)
        if si == -1:
            if self.ACK[0] in raw:
                self._buf = bytearray(raw[raw.index(self.ACK[0]):])
                return None
            # Simpan byte terakhir jika bisa jadi awal HEADER_PREFIX
            # (misal: sudah terima 0x01, tunggu 0x0f berikutnya)
            if raw and raw[-1] == self.HEADER_PREFIX[0]:
                self._buf = bytearray(raw[-1:])
            else:
                self._buf.clear()
            return None
        if si > 0:
            self._buf = bytearray(raw[si:])
            raw = bytes(self._buf)

        if len(raw) < 11:
            return None

        eot_idx = raw.find(self.EOT, 4)
        if eot_idx == -1:
            return None

        frame    = raw[: eot_idx + 1]
        if len(frame) < 7:
            return None

        # CRC tidak diverifikasi di RX (referensi tm81-command-tester juga tidak cek CRC RX)
        crc_size = self._crc_bytes
        payload  = frame[5: -(crc_size + 2)] if len(frame) >= 11 else b""
        hex_str  = " ".join(f"{b:02x}" for b in frame)
        print(f"[TM81 RX] len={len(frame)}B  {hex_str}", flush=True)
        if payload:
            print(f"[TM81 RX] payload={payload.hex(' ')}", flush=True)
        self._buf = bytearray(raw[eot_idx + 1:])
        return ParseResult(raw=frame, payload=payload, valid=True)


# =============================================================================
# RawLineParser — fallback sederhana: satu baris = satu frame
# =============================================================================

class RawLineParser(BaseParser):
    """Frame = satu baris yang diakhiri terminator (default \\n)."""

    def __init__(self, terminator: bytes = b'\n'):
        super().__init__()
        self.terminator = terminator

    def parse(self, buf: bytearray) -> Optional[ParseResult]:
        raw = bytes(buf)
        idx = raw.find(self.terminator)
        if idx == -1:
            return None
        line = raw[: idx]
        return ParseResult(raw=line + self.terminator,
                           payload=line.strip(), valid=True)


# =============================================================================
# SerialComm — class utama
# =============================================================================

class SerialComm:
    """
    Mengelola koneksi serial: find port, connect, reader thread, send.

    Callbacks
    ---------
    on_data(fn)       : dipanggil setiap ParseResult komplit diterima
    on_connect(fn)    : dipanggil saat berhasil connect
    on_disconnect(fn) : dipanggil saat disconnect / port hilang
    """

    def __init__(self, config: SerialConfig, parser: BaseParser):
        self._config   = config
        self._parser   = parser
        self._port: Optional[serial.Serial] = None
        self._thread: Optional[threading.Thread] = None
        self._stop_evt = threading.Event()

        self._cb_data:       list[Callable] = []
        self._cb_connect:    list[Callable] = []
        self._cb_disconnect: list[Callable] = []

        self._parser.set_frame_callback(self._on_frame)

    # ------------------------------------------------------------------
    # Port discovery
    # ------------------------------------------------------------------

    def find_port(self) -> Optional[str]:
        """Cari port berdasarkan device_name di deskripsi."""
        keyword = self._config.device_name.lower()
        for p in serial.tools.list_ports.comports():
            desc = (p.description or "").lower()
            if keyword in desc:
                return p.device
        return None

    # ------------------------------------------------------------------
    # Connect / disconnect
    # ------------------------------------------------------------------

    def connect(self, port=None):
        """Buka koneksi serial. Jika port=None, cari otomatis via find_port()."""
        if port is None:
            port = self.find_port()
        if port is None:
            log.warning("Port tidak ditemukan untuk device: %s", self._config.device_name)
            return False
        try:
            self._port = serial.Serial(
                port     = port,
                baudrate = self._config.baudrate,
                bytesize = self._config.bytesize,
                parity   = self._config.parity,
                stopbits = self._config.stopbits,
                timeout  = self._config.timeout,
                xonxoff  = self._config.xonxoff,
                rtscts   = self._config.rtscts,
                dsrdtr   = self._config.dsrdtr,
            )
        except serial.SerialException as e:
            log.error("Gagal buka port %s: %s", port, e)
            return False

        self._stop_evt.clear()
        self._thread = threading.Thread(target=self._reader, daemon=True)
        self._thread.start()

        for fn in self._cb_connect:
            fn(port)
        log.info("Terhubung ke %s", port)
        return True

    def disconnect(self):
        """Tutup koneksi serial dan hentikan reader thread."""
        self._stop_evt.set()
        if self._port and self._port.is_open:
            self._port.close()
        if self._thread:
            self._thread.join(timeout=2.0)
        self._port = None
        for fn in self._cb_disconnect:
            fn()

    def is_connected(self):
        return self._port is not None and self._port.is_open

    # ------------------------------------------------------------------
    # Send
    # ------------------------------------------------------------------

    def send(self, data):
        """
        Kirim data ke port serial.
        - bytes / bytearray  -> dikirim langsung
        - str                -> di-encode UTF-8 + cmd_terminator
        """
        if not self.is_connected():
            return False
        if isinstance(data, (bytes, bytearray)):
            raw = bytes(data)
        else:
            raw = str(data).encode() + self._config.cmd_terminator
        try:
            self._port.write(raw)
            return True
        except serial.SerialException as e:
            log.error("Gagal kirim: %s", e)
            return False

    # ------------------------------------------------------------------
    # Callbacks
    # ------------------------------------------------------------------

    def on_data(self, fn):
        self._cb_data.append(fn)

    def on_connect(self, fn):
        self._cb_connect.append(fn)

    def on_disconnect(self, fn):
        self._cb_disconnect.append(fn)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _reader(self):
        """Thread: baca satu byte sekaligus, feed ke parser."""
        while not self._stop_evt.is_set():
            try:
                if self._port and self._port.is_open:
                    b = self._port.read(1)
                    if b:
                        self._parser.feed(b)
            except serial.SerialException as e:
                log.warning("Reader error: %s", e)
                break
        for fn in self._cb_disconnect:
            fn()

    def _on_frame(self, result):
        for fn in self._cb_data:
            fn(result)
