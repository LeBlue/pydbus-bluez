from . import format as fmt

firmware_revision_string = {
   "name": "Firmware Revision String",
   "uuid": "00002a26-0000-1000-8000-00805f9b34fb",
   "form": fmt.FormatUtf8s,
}
hardware_revision_string = {
   "name": "Hardware Revision String",
   "uuid": "00002a27-0000-1000-8000-00805f9b34fb",
   "form": fmt.FormatUtf8s,
}
manufacturer_name_string = {
   "name": "Manufacturer Name String",
   "uuid": "00002a29-0000-1000-8000-00805f9b34fb",
   "form": fmt.FormatUtf8s,
}
serial_number_string = {
   "name": "Serial Number String",
   "uuid": "00002a25-0000-1000-8000-00805f9b34fb",
   "form": fmt.FormatUtf8s,
}
software_revision_string = {
   "name": "Software Revision String",
   "uuid": "00002a28-0000-1000-8000-00805f9b34fb",
   "form": fmt.FormatUtf8s,
}
model_number_string = {
   "name": "Model Number String",
   "uuid": "00002a24-0000-1000-8000-00805f9b34fb",
   "form": fmt.FormatUtf8s,
}


class FormatTemperatureCelsius(fmt.FormatSint16):
   exponent = -1
   pass


class FormatBatteryPowerState(fmt.FormatBitfield):
   pass


class FormatBatteryLevelState(fmt.FormatTuple):
   len = 2
   sub_cls = [fmt.FormatUint8, FormatBatteryPowerState]

