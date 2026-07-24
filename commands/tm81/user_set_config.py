"""commands/tm81/user_set_config.py — Set User Config (CMD 0x07)

Kirim:
  activation(1B) + initial_counter(4B) + counter_res(1B) +
  alarm(1B) + submit_id(1B) + timezone(1B) + msg_type(1B)

Defaults: activated, 0, RES_10L, 0, THIRTY_MINS, UTC+7, CONFIRMED
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


class UserSetConfig(TM81Command):
    def __init__(self, conn=None, timeout=None, params=None):
        super().__init__(conn, timeout)
        p = params or {}
        self._activation    = p.get("activation",    1)   # 1=ACTIVATED
        self._counter       = p.get("initial_counter", 0)
        self._counter_res   = p.get("counter_res",   1)   # 1=RES_10L
        self._alarm         = p.get("alarm",         0)
        self._submit_id     = p.get("submit_id",     0)   # 0=THIRTY_MINS
        self._timezone      = p.get("timezone",      7)   # UTC+7
        self._msg_type      = p.get("msg_type",      1)   # 1=CONFIRMED

    def execute(self) -> str:
        data = (
            self._activation.to_bytes(1, "little")
            + self._counter.to_bytes(4, "little")
            + self._counter_res.to_bytes(1, "little")
            + self._alarm.to_bytes(1, "little")
            + self._submit_id.to_bytes(1, "little")
            + self._timezone.to_bytes(1, "little")
            + self._msg_type.to_bytes(1, "little")
        )
        result = self.xfer(CmdId.USR_SET_CFG, data)
        if not result.valid and result.error not in ("ACK",):
            return f"NG:{result.error}"
        SUBMIT = {0:"30min",1:"1h",2:"3h",3:"12h",4:"1day",5:"3day",6:"7day"}
        CRES   = {0:"1L",1:"10L",2:"100L"}
        ACT    = {0:"Deactivated",1:"Activated"}
        MSG    = {0:"Unconfirmed",1:"Confirmed"}
        tz_sign = "+" if self._timezone >= 0 else ""
        summary = (
            f"act={ACT.get(self._activation, self._activation)} "
            f"counter={self._counter} "
            f"res={CRES.get(self._counter_res, self._counter_res)} "
            f"alarm={self._alarm:#04x} "
            f"submit={SUBMIT.get(self._submit_id, self._submit_id)} "
            f"tz=UTC{tz_sign}{self._timezone} "
            f"msg={MSG.get(self._msg_type, self._msg_type)}"
        )
        _log.debug(f"  User Set Config → OK  {summary}")
        return f"OK:{summary}"

# ── Standalone test ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys as _sys, os as _os
    _sys.path.insert(0, _os.path.join(_os.path.dirname(__file__), "..", "..", "lib"))
    import serial_manager as sm
    sm.connect("ch340")
    # activation=1, initial_counter=0, alarm=0, timezone=7
    params = {}
    result = UserSetConfig(params=params).execute()
    print(result)
    sm.disconnect_all()
