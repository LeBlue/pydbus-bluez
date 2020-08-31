from . import format as fmt


gap = {
    "name": "GAP",
    "uuid": "00001801-0000-1000-8000-00805f9b34fb",
}

device_information = {
    "name": "device_information",
    "uuid": "0000180a-0000-1000-8000-00805f9b34fb",
}

SERVICES = {gap["uuid"]: gap, device_information["uuid"]: device_information}

model_number_string = {
    "name": "Model Number String",
    "uuid": "00002a24-0000-1000-8000-00805f9b34fb",
    "fmt": fmt.FormatUtf8s,
}
serial_number_string = {
    "name": "Serial Number String",
    "uuid": "00002a25-0000-1000-8000-00805f9b34fb",
    "fmt": fmt.FormatUtf8s,
}

firmware_revision_string = {
    "name": "Firmware Revision String",
    "uuid": "00002a26-0000-1000-8000-00805f9b34fb",
    "fmt": fmt.FormatUtf8s,
}
hardware_revision_string = {
    "name": "Hardware Revision String",
    "uuid": "00002a27-0000-1000-8000-00805f9b34fb",
    "fmt": fmt.FormatUtf8s,
}
software_revision_string = {
    "name": "Software Revision String",
    "uuid": "00002a28-0000-1000-8000-00805f9b34fb",
    "fmt": fmt.FormatUtf8s,
}
manufacturer_name_string = {
    "name": "Manufacturer Name String",
    "uuid": "00002a29-0000-1000-8000-00805f9b34fb",
    "fmt": fmt.FormatUtf8s,
}
database_hash = {
    "name": "Database Hash",
    "uuid": "00002b2a-0000-1000-8000-00805f9b34fb",
    "fmt": fmt.FormatRaw,
}
client_supported_features = {
    "name": "Client Supported Features",
    "uuid": "00002b29-0000-1000-8000-00805f9b34fb",
    "fmt": fmt.FormatBitfield,
}
service_changed = {
    "name": "Service Changed",
    "uuid": "00002a05-0000-1000-8000-00805f9b34fb",
    "fmt": fmt.FormatRaw,
}


CHARACTERISTICS = {
    model_number_string["uuid"]: model_number_string,
    serial_number_string["uuid"]: serial_number_string,
    firmware_revision_string["uuid"]: firmware_revision_string,
    hardware_revision_string["uuid"]: hardware_revision_string,
    software_revision_string["uuid"]: software_revision_string,
    manufacturer_name_string["uuid"]: manufacturer_name_string,
    database_hash["uuid"]: database_hash,
    client_supported_features["uuid"]: client_supported_features,
    service_changed["uuid"]: service_changed,
}


class FormatCCC(fmt.FormatTuple):
    sub_cls = (fmt.FormatUint8, fmt.FormatUint8)
    sub_cls_names = ("foo", "bar")


ccc = {"name": "CCC", "uuid": "00002902-0000-1000-8000-00805f9b34fb", "fmt": FormatCCC}


class FormatCRF(fmt.FormatTuple):
    sub_cls = (
        fmt.FormatUint8Enum,
        fmt.FormatSint8,
        fmt.FormatUint16,
        fmt.FormatUint8Enum,
        fmt.FormatUtf8s,
    )
    sub_cls_names = ("format", "exponent", "unit", "namespace", "description")


crf = {"name": "CRF", "uuid": "00002904-0000-1000-8000-00805f9b34fb", "fmt": FormatCRF}


class FormatValidRange(fmt.FormatTuple):
    # sub_cls = (fmt.??, fmt.??)
    # TODO: dual variable length not supported (depends on characteristic and/or crf descriptor)
    sub_cls = (fmt.FormatRaw,)
    sub_cls_names = ("lower inclusive bound", "upper inclusive bound")


valid_range = {
    "name": "valid_range",
    "uuid": "00002906-0000-1000-8000-00805f9b34fb",
    "fmt": FormatValidRange,
}


DESCRIPTORS = {ccc["uuid"]: ccc, crf["uuid"]: crf, valid_range["uuid"]: valid_range}


class FormatTemperatureCelsius(fmt.FormatSint16):
    exponent = -1
    pass


class FormatBatteryPowerState(fmt.FormatBitfield):
    pass


class FormatBatteryLevelState(fmt.FormatTuple):
    len = 2
    sub_cls = [fmt.FormatUint8, FormatBatteryPowerState]
