"""
CRC Communication Test - kirim frame ber-CRC, validasi response.

Format frame yang diharapkan:
  Kirim  : <TEST_CRC + CRC_2byte>   (dibangun oleh CRCParser.build_frame)
  Terima : <OK + CRC_2byte>         (device membalas dengan frame ber-CRC)

Jika device Anda memakai format berbeda, sesuaikan di sini.
"""

import threading
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))

from test_base import TestBase
from serial_comm import SerialComm, CRCParser
from serial_manager import DEFAULT_CONFIG


class CrcCommTest(TestBase):
    TITLE       = "CRC Comm Test"
    TYPE        = "auto"
    COMMAND     = "TEST_CRC"
    DESCRIPTION = "Kirim & terima frame dengan validasi CRC-16/CCITT"

    # CRC config — harus sama dengan device
    CRC_PRESET  = "crc-ccitt-false"
    CRC_BYTES   = 2
    START       = b'<'
    END         = b'>'

    def run(self) -> str:
        # Parser CRC terpisah khusus test ini
        parser = CRCParser(
            start      = self.START,
            end        = self.END,
            crc_bytes  = self.CRC_BYTES,
            crc_preset = self.CRC_PRESET,
        )

        comm   = SerialComm(DEFAULT_CONFIG, parser)
        result = [None]
        done   = threading.Event()

        def on_data(frame):
            if not frame.valid:
                result[0] = f"NG:CRC_ERROR:{frame.error}"
                done.set()
                return
            resp = frame.payload.decode(errors="ignore").strip().upper()
            result[0] = "OK" if resp == "OK" else f"NG:RESP={resp}"
            done.set()

        comm.on_data(on_data)

        if not comm.connect():
            return "NG:NOT_CONNECTED"

        # Bangun frame dengan CRC dan kirim
        frame_bytes = parser.build_frame(self.COMMAND.encode())
        comm.send_raw(frame_bytes)

        done.wait(timeout=5.0)
        comm.disconnect()

        return result[0] or "NG:TIMEOUT"


if __name__ == "__main__":
    t = CrcCommTest()
    result = t.run()
    print(f"[{CrcCommTest.TITLE}] -> {result}")
