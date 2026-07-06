"""
commands/tm81/base.py — Base class untuk semua command TM81.

Cara pakai:
    import serial_manager as sm
    from commands.tm81.base import TM81Command

    sm.connect("ch340")
    cmd = TM81Command(conn="ch340")
    result = cmd.xfer(cmd_id=0x00)   # Ping
    print(result.payload.hex())
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "lib"))

import threading
import serial_manager as sm
from serial_comm import TM81Parser, ParseResult


# ---------------------------------------------------------------------------
# Command ID constants (mirror dari Lib/Env.py TM81)
# ---------------------------------------------------------------------------

class CmdId:
    PING                    = 0x00
    IRDA_DISABLE            = 0x01
    SENSOR_GET_CONFIG       = 0x02
    SENSOR_RESET_CONFIG     = 0x03
    SENSOR_GET_DATA         = 0x04
    USR_REBOOT_BOOTLOADER   = 0x05
    USR_SYNC_CFG            = 0x06
    USR_SET_CFG             = 0x07
    USR_GET_CONFIG          = 0x08
    USR_RESET_CONFIG        = 0x09
    USR_GET_TIME            = 0x0A
    USR_SET_TIME            = 0x0B
    USR_GET_VER             = 0x0C
    USR_TEST_WDT            = 0x0D
    ENTER_STANDBY           = 0x0E
    SET_DEV_EUI             = 0x0F
    SET_JOIN_EUI            = 0x10
    SET_APP_KEY             = 0x11
    SET_NW_KEY              = 0x12
    SET_DEV_ADDR            = 0x13
    SET_JOIN_MODE           = 0x14
    SET_DEV_CLASS           = 0x15
    GET_LORA_DATA           = 0x16
    FORCE_SEND_LORA         = 0x17
    USAGE_HISTORY_READ      = 0x18
    USAGE_HISTORY_WRITE     = 0x19
    GET_DEV_INFO            = 0x1A
    DEV_GET_ID              = 0x1B
    DEV_SET_ID              = 0x1C
    SET_LORA_DATA           = 0x1D
    TEST_GET_CHIP_ID        = 0x1E
    TEST_CC_GET_TEMP        = 0x1F
    TEST_CC_RESET_ACR       = 0x20
    TEST_CC_GET_ACR         = 0x21
    TEST_SOFT_RESET         = 0x22
    GET_LAST_SUBMIT_TIME    = 0x23
    BL_SET_RDY              = 100
    BL_FW_DATA              = 101
    BL_GOTO_APP             = 102


# ---------------------------------------------------------------------------
# TM81Command — base class
# ---------------------------------------------------------------------------

class TM81Command:
    """
    Base class untuk semua command TM81.

    conn    : nama koneksi di config.json (default: "ch340")
    timeout : timeout tunggu response (detik)
    """

    CONN    = "ch340"
    TIMEOUT = 2.0
    MAX_RETRY = 3

    def __init__(self, conn: str = None, timeout: float = None, params=None):
        self._conn    = conn    or self.CONN
        self._timeout = timeout or self.TIMEOUT
        # params diabaikan di base — subclass yang butuh override __init__ dan baca sendiri

    def xfer(self, cmd_id: int, data: bytes = b"", timeout: float = None) -> ParseResult:
        """
        Kirim command dan tunggu response.
        Return ParseResult. result.valid=True jika berhasil.
        """
        comm = sm.get_comm(self._conn)
        if comm is None or not comm.is_connected():
            return ParseResult(raw=b"", payload=b"", valid=False,
                               error=f"Koneksi '{self._conn}' tidak terhubung")

        timeout = timeout or self._timeout
        frame   = comm._parser.build_send_frame(cmd_id, data)

        result  = [None]
        event   = threading.Event()

        def _on_data(pr: ParseResult):
            result[0] = pr
            event.set()

        comm.on_data(_on_data)
        try:
            comm._port.write(frame)
        except Exception as e:
            try: comm._cb_data.remove(_on_data)
            except ValueError: pass
            return ParseResult(raw=b"", payload=b"", valid=False, error=str(e))

        event.wait(timeout=timeout)
        try: comm._cb_data.remove(_on_data)
        except ValueError: pass

        if result[0] is None:
            return ParseResult(raw=b"", payload=b"", valid=False, error="Timeout")

        return result[0]

    def execute(self) ->