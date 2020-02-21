from .format import *


class FormatTemperatureCelsius(FormatSint16):
    pass


class FormatBatteryPowerState(FormatBitField):
    pass


class FormatBatteryLevelState(FormatTuple):
    len = 2
    sub_cls = [FormatUint8, FormatBatteryPowerState]

