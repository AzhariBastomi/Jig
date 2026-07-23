"""
flasher.py — Library untuk flashing firmware ke berbagai target MCU.

Supported targets:
  - Arduino   : via avrdude (.hex / .bin)
  - ESP32     : via esptool.py (.bin)
  - ESP8266   : via esptool.py (.bin)
  - STM32     : via st-flash (.bin)

Semua flasher mewarisi FlasherBase dan mengekspos:
  flash(firmware_path) -> FlashResult

Contoh pemakaian:
    from flasher import ArduinoFlasher, ArduinoConfig

    cfg = ArduinoConfig(port="COM3", mcu="atmega328p", baudrate=115200)
    result = ArduinoFlasher(cfg).flash("firmware.hex")
    print(result.ok, result.message)
"""

import subprocess
import shutil
import os
from dataclasses import dataclass, field
from typing import Optional, Callable


# ---------------------------------------------------------------------------
# Result
# ---------------------------------------------------------------------------

@dataclass
class FlashResult:
    ok:       bool
    message:  str
    stdout:   str = ""
    stderr:   str = ""

    def __str__(self):
        status = "OK" if self.ok else "NG"
        return f"[{status}] {self.message}"


# ---------------------------------------------------------------------------
# Base
# ---------------------------------------------------------------------------

class FlasherBase:
    """Base class semua flasher. Override flash() di subclass."""

    def flash(self, firmware_path: str,
              progress_cb: Optional[Callable[[int], None]] = None) -> FlashResult:
        raise NotImplementedError

    def _check_file(self, path: str) -> Optional[str]:
        """Return error string jika file tidak ditemukan, None jika OK."""
        if not os.path.isfile(path):
            return f"File tidak ditemukan: {path}"
        return None

    def _check_tool(self, tool: str) -> Optional[str]:
        """Return error string jika tool tidak ada di PATH."""
        if shutil.which(tool) is None:
            return f"Tool '{tool}' tidak ditemukan di PATH"
        return None

    def _run(self, cmd: list[str],
             progress_cb: Optional[Callable[[int], None]] = None,
             success_hint: str = "") -> FlashResult:
        """
        Jalankan command, baca output per chunk (bukan per baris).
        Mendukung \r (STM32_Programmer_CLI) dan \n (st-flash/avrdude).

        Progress mapping STM32_Programmer_CLI:
          "Download in Progress" → phase download (0–70%)
          "Read progress"        → phase verify  (70–99%)
          "██...██ XX%"          → persentase real dari tool
          "Download verified"    → 100%

        Progress mapping st-flash / avrdude:
          '#' characters         → perkiraan progress
        """
        import re

        _PHASE_DOWNLOAD = 1
        _PHASE_VERIFY   = 2

        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                bufsize=0,                   # unbuffered — dapat output langsung
            )

            out_lines  = []
            buf        = b""
            phase      = 0
            hash_count = 0

            while True:
                chunk = proc.stdout.read(64)
                if not chunk:
                    break
                buf += chunk

                # Split pada \r dan \n
                parts = re.split(rb"[\r\n]", buf)
                buf   = parts[-1]           # sisa yang belum lengkap

                for raw in parts[:-1]:
                    line = raw.decode("utf-8", errors="replace").strip()
                    if line:
                        out_lines.append(line)

                    if not progress_cb:
                        continue

                    # Deteksi phase (STM32_Programmer_CLI)
                    if "Download in Progress" in line:
                        phase = _PHASE_DOWNLOAD
                        progress_cb(5)
                    elif "Read progress" in line or "Verifying" in line:
                        phase = _PHASE_VERIFY
                        progress_cb(70)
                    elif "Download verified" in line or "File download complete" in line:
                        progress_cb(99)

                    # Parse persentase dari baris: "██...██ 65%"
                    m = re.search(r"(\d{1,3})\s*%", line)
                    if m:
                        raw_pct = int(m.group(1))
                        if phase == _PHASE_DOWNLOAD:
                            # Download = 5–70%
                            pct = 5 + int(raw_pct * 0.65)
                        elif phase == _PHASE_VERIFY:
                            # Verify = 70–99%
                            pct = 70 + int(raw_pct * 0.29)
                        else:
                            pct = raw_pct
                        progress_cb(min(pct, 99))

                    # st-flash / avrdude style: hitung '#'
                    hash_count += raw.count(b"#")
                    if hash_count and phase == 0:
                        pct = min(int(hash_count / 50 * 100), 99)
                        progress_cb(pct)

            proc.wait()
            full_out = "\n".join(out_lines)

            if proc.returncode == 0:
                if progress_cb:
                    progress_cb(100)
                return FlashResult(ok=True, message="Flash berhasil", stdout=full_out)
            else:
                error_msg = self._extract_error(full_out, proc.returncode)
                return FlashResult(
                    ok=False,
                    message=error_msg,
                    stdout=full_out,
                )

        except FileNotFoundError as e:
            return FlashResult(ok=False, message=str(e))
        except Exception as e:
            return FlashResult(ok=False, message=f"Error: {e}")

    def _extract_error(self, stdout: str, returncode: int) -> str:
        """
        Cari baris error yang relevan dari output tool.
        Prioritas: baris yang mengandung kata kunci error umum.
        """
        import re

        # Keyword error yang dicari, urutan prioritas
        ERROR_KEYWORDS = [
            "Error",
            "error",
            "FAILED",
            "failed",
            "No ST-LINK",
            "No target",
            "Unable",
            "Cannot",
            "could not",
            "timeout",
            "Timeout",
            "not found",
            "invalid",
        ]

        lines = [l.strip() for l in stdout.splitlines() if l.strip()]

        for kw in ERROR_KEYWORDS:
            for line in lines:
                if kw in line:
                    # Bersihkan prefix berulang seperti "Error: Error:"
                    clean = re.sub(r"^(Error\s*:\s*)+", "Error: ", line)
                    return clean

        # Fallback: ambil baris terakhir yang tidak kosong
        if lines:
            return f"exit {returncode}: {lines[-1]}"

        return f"Flash gagal (exit {returncode})"


# ---------------------------------------------------------------------------
# Arduino (avrdude)
# ---------------------------------------------------------------------------

@dataclass
class ArduinoConfig:
    port:        str   = "COM3"          # Serial port  (COM3 / /dev/ttyUSB0)
    mcu:         str   = "atmega328p"    # avrdude -p
    programmer:  str   = "arduino"       # avrdude -c  (arduino/stk500v2/usbasp/...)
    baudrate:    int   = 115200
    avrdude_bin: str   = "avrdude"
    extra_flags: list  = field(default_factory=list)


class ArduinoFlasher(FlasherBase):
    """
    Flash Arduino via avrdude.
    Mendukung .hex (Intel HEX) dan .bin (raw binary → dikonversi ke :format bin).
    """

    def __init__(self, config: ArduinoConfig):
        self.cfg = config

    def flash(self, firmware_path: str,
              progress_cb: Optional[Callable[[int], None]] = None) -> FlashResult:

        if err := self._check_file(firmware_path):
            return FlashResult(ok=False, message=err)
        if err := self._check_tool(self.cfg.avrdude_bin):
            return FlashResult(ok=False, message=err)

        ext  = os.path.splitext(firmware_path)[1].lower()
        fmt  = "i" if ext == ".hex" else "r"   # Intel HEX atau raw binary

        cmd = [
            self.cfg.avrdude_bin,
            "-p", self.cfg.mcu,
            "-c", self.cfg.programmer,
            "-P", self.cfg.port,
            "-b", str(self.cfg.baudrate),
            "-U", f"flash:w:{firmware_path}:{fmt}",
            *self.cfg.extra_flags,
        ]

        return self._run(cmd, progress_cb)


# ---------------------------------------------------------------------------
# ESP32 & ESP8266 (esptool)
# ---------------------------------------------------------------------------

@dataclass
class EspConfig:
    port:        str   = "COM3"
    baud:        int   = 460800          # Flash speed (bisa 921600 untuk ESP32)
    flash_addr:  str   = "0x0"           # Alamat flash target
    chip:        str   = "auto"          # auto / esp32 / esp8266 / esp32s2 / ...
    esptool_bin: str   = "esptool.py"
    before:      str   = "default_reset" # before reset sequence
    after:       str   = "hard_reset"    # after  reset sequence
    extra_flags: list  = field(default_factory=list)


class EspFlasher(FlasherBase):
    """
    Flash ESP32 / ESP8266 via esptool.py.
    Ganti cfg.chip = 'esp32' atau 'esp8266' sesuai target.
    """

    def __init__(self, config: EspConfig):
        self.cfg = config

    def flash(self, firmware_path: str,
              progress_cb: Optional[Callable[[int], None]] = None) -> FlashResult:

        if err := self._check_file(firmware_path):
            return FlashResult(ok=False, message=err)
        if err := self._check_tool(self.cfg.esptool_bin):
            return FlashResult(ok=False, message=err)

        cmd = [
            self.cfg.esptool_bin,
            "--chip",   self.cfg.chip,
            "--port",   self.cfg.port,
            "--baud",   str(self.cfg.baud),
            "--before", self.cfg.before,
            "--after",  self.cfg.after,
            "write_flash",
            *self.cfg.extra_flags,
            self.cfg.flash_addr,
            firmware_path,
        ]

        return self._run(cmd, progress_cb)


class Esp32Flasher(EspFlasher):
    """Shortcut: ESP32 dengan default yang umum dipakai."""
    def __init__(self, port: str = "COM3", baud: int = 460800,
                 flash_addr: str = "0x1000", **kwargs):
        super().__init__(EspConfig(
            port=port, baud=baud, flash_addr=flash_addr,
            chip="esp32", **kwargs))


class Esp8266Flasher(EspFlasher):
    """Shortcut: ESP8266 dengan default yang umum dipakai."""
    def __init__(self, port: str = "COM3", baud: int = 115200,
                 flash_addr: str = "0x0", **kwargs):
        super().__init__(EspConfig(
            port=port, baud=baud, flash_addr=flash_addr,
            chip="esp8266", **kwargs))


# ---------------------------------------------------------------------------
# STM32 (Windows: STM32_Programmer_CLI | Linux: st-flash)
# ---------------------------------------------------------------------------

@dataclass
class Stm32Config:
    stlink_bin:  str   = ""              # kosong = auto-detect via stlink_path
    reset:       bool  = True            # Reset setelah flash
    flash_addr:  str   = "0x08000000"    # Alamat flash STM32
    format:      str   = "binary"        # binary / ihex
    extra_flags: list  = field(default_factory=list)


class Stm32Flasher(FlasherBase):
    """
    Flash STM32.
    Windows : STM32_Programmer_CLI.exe -c port=SWD -w <file> <addr> -v -rst
    Linux   : st-flash write <file> <addr>
    Tool di-detect otomatis via stlink_path.find_flash_tool().
    """

    def __init__(self, config: Stm32Config = None):
        self.cfg = config or Stm32Config()

    def _resolve_tool(self) -> tuple:
        """Return (tool_path, is_windows). Raise FileNotFoundError jika tidak ada."""
        import sys as _sys
        tool = self.cfg.stlink_bin
        if not tool:
            from stlink_path import find_flash_tool
            tool = find_flash_tool()
        return tool, _sys.platform == "win32"

    def flash(self, firmware_path: str,
              progress_cb: Optional[Callable[[int], None]] = None) -> FlashResult:

        if err := self._check_file(firmware_path):
            return FlashResult(ok=False, message=err)

        try:
            tool, is_windows = self._resolve_tool()
        except FileNotFoundError as e:
            return FlashResult(ok=False, message=str(e))

        ext = os.path.splitext(firmware_path)[1].lower()

        if is_windows:
            # STM32_Programmer_CLI.exe -c port=SWD -w "<file>" <addr> -v -rst
            cmd = [
                tool,
                "-c", "port=SWD",
                "-w", firmware_path, self.cfg.flash_addr,
                "-v",
                *self.cfg.extra_flags,
            ]
            if self.cfg.reset:
                cmd.append("-rst")
            return self._run(cmd, progress_cb)

        # Linux: st-flash
        if ext == ".hex" or self.cfg.format == "ihex":
            cmd = [
                tool,
                "--format", "ihex",
                *self.cfg.extra_flags,
                "write",
                firmware_path,
            ]
        else:
            cmd = [
                tool,
                *self.cfg.extra_flags,
                "write",
                firmware_path,
                self.cfg.flash_addr,
            ]

        result = self._run(cmd, progress_cb)

        if result.ok and self.cfg.reset:
            subprocess.run([tool, "reset"], capture_output=True)

        return result


# ---------------------------------------------------------------------------
# Factory helper
# ---------------------------------------------------------------------------

def make_flasher(target: str, **kwargs) -> FlasherBase:
    """
    Buat flasher berdasarkan nama target string.

    target: "arduino" | "esp32" | "esp8266" | "stm32"
    kwargs: diteruskan ke Config masing-masing

    Contoh:
        f = make_flasher("arduino", port="COM4", mcu="atmega2560", programmer="stk500v2")
        f = make_flasher("esp32",   port="COM5", baud=921600)
        f = make_flasher("stm32")
    """
    target = target.lower()
    if target == "arduino":
        return ArduinoFlasher(ArduinoConfig(**kwargs))
    elif target == "esp32":
        return Esp32Flasher(**kwargs)
    elif target == "esp8266":
        return Esp8266Flasher(**kwargs)
    elif target == "stm32":
        return Stm32Flasher(Stm32Config(**kwargs))
    else:
        raise ValueError(f"Target tidak dikenal: {target!r}. "
                         f"Pilihan: arduino, esp32, esp8266, stm32")
