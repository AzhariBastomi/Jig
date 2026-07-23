"""
commands/tm81/sensor_calibration.py - Sensor Calibration (CMD 0x02 + 0x04)
Loop: get_config -> get_data -> cek status bit -> konfirmasi operator.
Tipe: MANUAL (operator confirm saat calibration done).
"""

import logging
_log = logging.getLogger(__name__)

try:
    from commands.tm81.base import TM81Command, CmdId
except ImportError:
    import sys as _sys, os as _os
    _sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", ".."))
    _sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "..", "lib"))
    from commands.tm81.base import TM81Command, CmdId


class SensorCalibration(TM81Command):

    CAL_STATUS_FAIL           = 0x01
    CAL_STATUS_NEVER_CAL      = 0x10
    CAL_STATUS_REMOVED        = 0x04
    CAL_STATUS_METAL          = 0x08
    CAL_STATUS_LOW_VOLTAGE    = 0x20

    def _check_cal_status(self, status_byte: int) -> str:
        """Return "" jika OK, atau pesan error."""
        if status_byte & self.CAL_STATUS_FAIL:
            return "Calibration failed"
        if not (status_byte & self.CAL_STATUS_NEVER_CAL):
            return "Never calibrated"
        if status_byte & self.CAL_STATUS_REMOVED:
            return "Sensor removed"
        if status_byte & self.CAL_STATUS_METAL:
            return "Metal interference detected"
        if status_byte & self.CAL_STATUS_LOW_VOLTAGE:
            return "Sensor voltage too low"
        return ""

    @staticmethod
    def _resp_cmd(r) -> int:
        """Ambil CMD_ID dari frame response (byte index 2)."""
        return r.raw[2] if r.raw and len(r.raw) >= 3 else -1

    def execute(self) -> str:
        import time

        max_attempts = 10
        for attempt in range(max_attempts):
            time.sleep(2)

            # 1. Trigger sensor cycle (SENSOR_GET_CONFIG)
            r = self.xfer(CmdId.SENSOR_GET_CONFIG, timeout=3.0)
            if not r.valid and r.error != "ACK":
                _log.debug(f"  [cal] sensor_get_config fail: {r.error}")
                time.sleep(2)
                continue
            if self._resp_cmd(r) != CmdId.SENSOR_GET_CONFIG:
                _log.debug(f"  [cal] wrong response cmd=0x{self._resp_cmd(r):02x}, skip")
                time.sleep(2)
                continue

            time.sleep(2)  # tunggu device selesai satu siklus

            # 2. Baca hasil - device butuh ~4-5s, gunakan timeout 6s
            r = self.xfer(CmdId.SENSOR_GET_DATA, timeout=6.0)
            if not r.valid:
                _log.debug(f"  [cal] sensor_get_data fail: {r.error}")
                time.sleep(2)
                continue

            if not r.payload or len(r.payload) < 1:
                _log.debug("  [cal] empty payload, retry")
                continue

            status_byte = r.payload[0]
            err = self._check_cal_status(status_byte)
            if err:
                _log.debug(f"  [cal] attempt {attempt+1}/{max_attempts}: {err}")
                continue

            # Status OK
            return "OK:Calibration successful"

        return "NG:Calibration failed after max attempts"


# -- Standalone test ----------------------------------------------------------
if __name__ == "__main__":
    import sys as _sys, os as _os
    _sys.path.insert(0, _os.path.join(_os.path.dirname(__file__), "..", "..", "lib"))
    import serial_manager as sm
    sm.connect("ch340")
    # SensorCalibration adalah tipe MANUAL - hasilnya bergantung kondisi sensor
    result = SensorCalibration().execute()
    print(result)
    sm.disconnect_all()
