"""
controllers/keepalive.py — Background keepalive ping untuk TM81.
Dikonfigurasi via json/config.json -> keepalive section.
"""

import json
import logging
import os
import sys
import threading

_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
_LIB  = os.path.join(_ROOT, "lib")
if _LIB not in sys.path:
    sys.path.insert(0, _LIB)

log = logging.getLogger("keepalive")

# Error yang menandakan port serial rusak / perlu reconnect
_SERIAL_ERR_KEYWORDS = (
    "writefile", "permissionerror", "access is denied",
    "getoverlappedresult", "broken pipe", "port is closed",
    "port not open", "device not found", "oserror",
)


class KeepaliveManager:
    """
    Mengirimkan ping ke TM81 secara periodik agar device tidak masuk sleep mode.
    Dikonfigurasi via json/config.json -> keepalive section.
    """

    def __init__(self):
        self._stop_evt = threading.Event()
        self._thread: "threading.Thread | None" = None
        self._cfg = self._load_cfg()

    @staticmethod
    def _load_cfg() -> dict:
        try:
            path = os.path.join(_ROOT, "config", "config.json")
            with open(path) as f:
                return json.load(f).get("keepalive", {})
        except Exception:
            return {}

    @property
    def enabled(self) -> bool:
        return self._cfg.get("enabled", True)

    @property
    def interval(self) -> float:
        return self._cfg.get("interval_ms", 5000) / 1000.0

    @property
    def connection(self) -> str:
        return self._cfg.get("connection", "ch340")

    def _is_serial_error(self, result: str) -> bool:
        lower = result.lower()
        return any(kw in lower for kw in _SERIAL_ERR_KEYWORDS)

    def start(self):
        if not self.enabled:
            return
        if self._thread and self._thread.is_alive():
            return
        self._stop_evt.clear()
        self._thread = threading.Thread(
            target=self._run, daemon=True, name="keepalive-ping"
        )
        self._thread.start()
        log.info("[PING] started — interval=%.1fs, conn=%r", self.interval, self.connection)

    def stop(self):
        self._stop_evt.set()
        log.info("[PING] stopped")

    def is_running(self) -> bool:
        return (
            self._thread is not None
            and self._thread.is_alive()
            and not self._stop_evt.is_set()
        )

    def _try_connect(self) -> bool:
        try:
            import serial_manager as sm
            import serial.tools.list_ports as lp

            dev_name = sm._CONN_DEFS.get(self.connection, {}).get("device_name", "")
            kw       = dev_name.lower()

            found = ""
            for p in lp.comports():
                if (kw in (p.description  or "").lower()
                        or kw in (p.manufacturer or "").lower()
                        or kw in (p.product      or "").lower()):
                    found = p.device
                    break

            if not found:
                return False

            ok = sm.connect(self.connection)
            if ok:
                log.info("[PING] %r terhubung di %s", self.connection, found)
            return ok
        except Exception as e:
            log.debug("[PING] _try_connect error: %s", e)
            return False

    def _disconnect(self) -> None:
        try:
            import serial_manager as sm
            sm.disconnect(self.connection)
            log.info("[PING] %r di-disconnect", self.connection)
        except Exception as e:
            log.debug("[PING] _disconnect error: %s", e)

    def _run(self):
        import serial_manager as sm
        from commands.tm81.ping import Ping

        _state = "unknown"

        while not self._stop_evt.wait(self.interval):
            try:
                result = str(Ping().execute()).strip()

                if result.upper().startswith("OK"):
                    if _state != "connected":
                        log.info("[PING] aktif ke %r", self.connection)
                        _state = "connected"
                    log.debug("[PING] OK")

                elif "tidak terhubung" in result.lower():
                    if _state != "disconnected":
                        log.info("[PING] %r belum terhubung, scan port...", self.connection)
                        _state = "disconnected"
                    if self._try_connect():
                        _state = "connected"

                elif self._is_serial_error(result):
                    if _state != "disconnected":
                        log.warning("[PING] serial error — disconnect & reconnect: %s", result)
                        _state = "disconnected"
                    self._disconnect()
                    if self._stop_evt.wait(2.0):
                        break
                    if self._try_connect():
                        _state = "connected"

                else:
                    # Device NG (Timeout, NAK) — port masih OK, lanjutkan
                    log.debug("[PING] device NG: %s", result)

            except Exception as e:
                if _state != "disconnected":
                    log.warning("[PING] exception — disconnect & reconnect: %s", e)
                    _state = "disconnected"
                self._disconnect()
