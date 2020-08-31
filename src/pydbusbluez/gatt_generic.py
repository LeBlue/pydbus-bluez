from .org_bluetooth import (
    model_number_string,
    serial_number_string,
    firmware_revision_string,
    hardware_revision_string,
    software_revision_string,
    manufacturer_name_string,
)

device_information = {
    "name": "Device Information",
    "uuid": "0000180a-0000-1000-8000-00805f9b34fb",
    "chars": [
        model_number_string,
        serial_number_string,
        firmware_revision_string,
        hardware_revision_string,
        software_revision_string,
        manufacturer_name_string,
    ],
}
