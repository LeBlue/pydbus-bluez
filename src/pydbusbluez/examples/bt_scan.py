#!/usr/bin/env python3
import sys

from argparse import ArgumentParser
from pydbusbluez import Adapter, Device, BluezError, ObjectManager

from gi.repository.GLib import MainLoop, timeout_add_seconds
import logging

def cli_aruments():
    parser = ArgumentParser(
        description='Scan for devices an print their names')

    _def_adapter = 'hci0'
    _def_scan = 0

    parser.add_argument('-i', '--adapter', metavar='hciX', default=_def_adapter,
                        help='bluetooh adapter to use (default={})'.format(_def_adapter))

    parser.add_argument('-d', '--scan-duration', metavar='sec', default=_def_scan, type=int,
                        help='scan duration in seconds (default={}), 0 == forever'.format(_def_scan))

    parser.add_argument('-p', '--properties', action='store_true',
                        help='print device properties')

    args = parser.parse_args()

    return args


def device_found(device_object, properties, print_properties):
    print(device_object, device_object.device_name)
    if print_properties:
        print(properties)

def adapter_changed(adapter, properties, loop):
    print('Adapter changed:', str(adapter), properties)
    if 'Discovering' in properties and properties['Discovering']:
        print('Scan enabled')

    if 'Powered' in properties and not properties['Powered']:
        print('Adapter unpowered/disconnected', file=sys.stderr)
        loop.quit()


def scan_timeout(loop, *args, **kwargs):
    loop.quit()

def main():

    args = cli_aruments()
    try:
        hci = Adapter(args.adapter)
    except BluezError as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)

    loop = MainLoop.new(None, False)

    if args.scan_duration:
        timeout_add_seconds(args.scan_duration, scan_timeout, loop)

    hci.onPropertiesChanged(adapter_changed, loop)
    hci.onDeviceAdded(device_found, args.properties, init=True)
    hci.scan()

    # for d in hci.devices():
    #     device_found(d, d.properties, args.properties)

    try:
        loop.run()
    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        try:
            hci.scan(enable=False)
        except:
            pass

if __name__ == "__main__":
    main()