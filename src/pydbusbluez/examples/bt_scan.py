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


def device_found(device_object, properties, print_properties, some=None):

    print('[NEW]', device_object, device_object.device_name, str(some))

    if properties:
        for prop, value in properties.items():
            print('[CHG] Device',  id(device_object), device_object.name, prop, str(value))

    device_object.onPropertiesChanged(device_changed, print_properties)
    device_object.adapter.onDeviceRemoved(device_object, device_removed)
    # ObjectManager.get().onObjectRemoved(device_object, device_removed)


def device_removed(adapter, device_object):
    print('[DEL]', id(device_object), device_object, device_object.device_name)
    device_object.clear()
    # print(device_object._proxy)
    # device_object.clear()
    # print(device_object._proxy)
    # del device_object._proxy

    # del device_object
    # print(device_object._proxy)


def device_changed(device_object, properties, print_properties):
    print('[CHG]',  id(device_object), device_object, device_object.device_name)

    if properties:
        for prop, value in properties.items():
            print('[CHG] Device', device_object.name, prop, str(value))


def adapter_changed(adapter, properties, loop):
    print('Controller changed:', str(adapter), properties)

    for prop, value in properties.items():
        print('[CHG] Controller', adapter.name, prop, str(value))


def adapter_removed(adapter):
    print('[DEL]', id(adapter), adapter, adapter.name)
    adapter.onDeviceAdded(None)
    adapter.onPropertiesChanged(None)


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
    hci.onDeviceAdded(device_found, args.properties, init=True, some='Foo')
    # hci.onDeviceRemoved(device_removed, args.properties)
    #hci.scan()

    # for d in hci.devices():
    #     device_found(d, d.properties, args.properties)

    try:
        loop.run()
    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        try:
            hci.onDeviceAdded(None)
            hci.onPropertiesChanged(None)
            hci.scan(enable=False)
            hci.clear()
        except:
            pass

if __name__ == "__main__":
    main()