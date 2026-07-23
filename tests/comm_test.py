"""Communication Test - loopback ping to device UART."""

import sys as _sys, os as _os
_sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), ".."))
_sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "lib"))

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))

import serial_manager as sm

TITLE       = "Communication Test"
TYPE        = "auto"
COMMAND     = "TEST_COMM"
DESCRIPTION = "Loopback ping to device UART"


if __name__ == "__main__":
    print("Connecting...")
    if not sm.connect():
        print("Gagal connect ke device")
    else:
        resp = sm.send_and_wait(COMMAND, timeout=5.0)
        result = "OK" if resp.upper() == "OK" else "NG"
        print(f"[{TITLE}] -> {result} (response: {resp!r})")
        sm.disconnect()
