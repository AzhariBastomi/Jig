"""commands/tm81/lora_set_config.py — Set LoRa Config (CMD 0x1D)

Kirim: tx_power(1B) + data_rate(1B) + rx1_delay_sec(1B)
"""
from commands.tm81.base import TM81Command, CmdId


class LoraSetConfig(TM81Command):
    def __init__(self, conn=None, timeout=None, params=None):
        super().__init__(conn, timeout)
        p = params or {}
        self._tx_power    = p.get("tx_power",    0)
        self._data_rate   = p.get("data_rate",   2)
        self._rx1_delay   = p.get("rx1_delay",   2)

    def execute(self) -> str:
        data = (
            self._tx_power.to_bytes(1, "little")
            + self._data_rate.to_bytes(1, "little")
            + self._rx1_delay.to_bytes(1, "little")
        )
        result = self.xfer(CmdId.SET_LORA_DATA, data)
        if not result.valid and result.error not in ("ACK",):
            return f"NG:{result.error}"
        print(f"  Set LoRa Config: TxPwr={self._tx_power} DR={self._data_rate} RX1Delay={self._rx1_delay}s → OK")
        return "OK"
