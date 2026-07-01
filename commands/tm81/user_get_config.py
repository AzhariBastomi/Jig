"""
commands/tm81/user_get_config.py — Get User Config (CMD 0x08)
"""

from commands.tm81.base import TM81Command, CmdId


class UserGetConfig(TM81Command):

    SUBMIT_RATE = {0:"30min",1:"1h",2:"3h",3:"12h",4:"1day",5:"3day",6:"7day"}
    COUNTER_RES = {0:"1L", 1:"10L", 2:"100L"}
    MSG_TYPE    = {0:"Unconfirmed", 1:"Confirmed"}
    ACTIVATION  = {0:"Deactivated", 1:"Activated"}

    def execute(self) -> str:
        result = self.xfer(CmdId.USR_GET_CONFIG)
        if not result.valid:
            return f"NG:{result.error}"

        d = self._raw = result.payload
        if len(d) < 14:
            return f"NG:payload terlalu pendek ({len(d)} bytes)"

        counter_res   = d[9]
        init_counter  = int.from_bytes(d[1:5], "little") / (10 * 10**counter_res)
        last_counter  = int.from_bytes(d[5:9], "little") / (10 * 10**counter_res)
        tz_val        = int.from_bytes(bytes([d[12]]), signed=True)

        print(f"  Activation   : {self.ACTIVATION.get(d[0], d[0])}")
        print(f"  Init usage   : {init_counter:.2f} m3")
        print(f"  Last usage   : {last_counter:.2f} m3")
        print(f"  Counter res  : {self.COUNTER_RES.get(counter_res, counter_res)}")
        print(f"  Alarm byte   : 0x{d[10]:02x}")
        print(f"  Submit rate  : {self.SUBMIT_RATE.get(d[11], d[11])}")
        print(f"  Timezone     : GMT{'+' if tz_val>0 else ''}{tz_val}")
        print(f"  Msg type     : {self.MSG_TYPE.get(d[13], d[13])}")
        return "OK"

    def get_raw(self) -> bytes:
        return getattr(self, "_raw", b"")
