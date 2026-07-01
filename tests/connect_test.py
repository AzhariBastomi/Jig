"""
Connect Test - Buka koneksi serial ke device yang ditentukan.

Ganti CONN_NAME sesuai nama koneksi di config.json:
    "stlink" -> STLink Virtual COM
    "uart"   -> UART device
    ""       -> pakai default dari config.json
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))

from test_base import TestBase
import serial_manager as sm


class ConnectTest(TestBase):
    TITLE       = "Connect Serial"
    TYPE        = "auto"
    COMMAND     = "CONNECT"
    DESCRIPTION = "Buka koneksi ke device"

    # Ganti ke nama koneksi yang diinginkan ("stlink", "uart", atau "" = default)
    CONN_NAME: str = ""

    def run(self) -> str:
        conn = self.CONN_NAME or None
        if sm.is_connected(conn):
            return "OK"
        success = sm.connect(conn)
        name = conn or sm.DEFAULT_CONN
        return "OK" if success else f"NG:Gagal connect ke {name!r}"


if __name__ == "__main__":
    conn_arg = sys.argv[1] if len(sys.argv) > 1 else None
    t = ConnectTest()
    if conn_arg:
        t.CONN_NAME = conn_arg
    result = t.run()
    print(f"[{ConnectTest.TITLE}] conn={t.CONN_NAME or sm.DEFAULT_CONN!r} -> {result}")
    sm.disconnect_all()
