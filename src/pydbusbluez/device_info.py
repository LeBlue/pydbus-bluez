#!/usr/bin/env python3

from pydbusbluez.device import Device, Adapter
from pydbusbluez.error import BluezDoesNotExistError, BluezError, DBusTimeoutError
from pydbusbluez.gatt import Gatt, FormatUint8, FormatBitfield
from pydbusbluez.gatt_generic import device_information
import sys

from gi.repository import GObject

from argparse import ArgumentParser

from time import sleep
from datetime import datetime

def_adapter = 'hci0'

def print_char(gatt_char, new_value):
    print(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'New value:', gatt_char.service.name, gatt_char.name, " = ", str(gatt_char.form.decode(new_value['Value'])))

def read_char(gatt_char):
    try:
        if gatt_char.read({'timeout': 2}) == None:
            print('Warn timeout')
    except DBusTimeoutError:
        pass

    return True


def main():
    parser = ArgumentParser(description='bluetooth tester')
    parser.add_argument('-i', '--adapter', metavar='hciX', default=def_adapter,
                        help='bluetooh adapter to use (default={})'.format(def_adapter))

    parser.add_argument('-a', '--device', metavar='addr', default=None,
                        help='device address to connect to')

    parser.add_argument('-p', '--pair', default=False, action='store_true',
                        help='Send pairing request to device, if not paired (Needs an agent)')

    parser.add_argument('-k', '--keep', default=False, action='store_true',
                        help='keep connection alive')

    parser.add_argument('-l', '--loop', default=False, action='store_true',
                        help='loop requesting info (sleeps 1s)')

    parser.add_argument('-w', '--wait', metavar='sec', default=1, type=int,
                        help='time to wait before starting to read')

    args = parser.parse_args()

    print('Scanning on: {}'.format(args.adapter))

    try:
        adapter = Adapter(args.adapter)
    except BluezDoesNotExistError as e:
        print(str(e))
        sys.exit(2)

    devs = adapter.devices()
    dev = None

    for d in devs:
        da = d.address()
        if da and da.upper() == args.device.upper():
            print('Found {}: {}'.format(args.device, d))
            dev = d

    if not dev:
        adapter.scan()

        sleep(3)
        sr = adapter.devices()

        for d in sr:
            da = d.address()
            if da and da.upper() == args.device.upper():
                print('Found {}: {}'.format(args.device, d))
                dev = d

        if not dev:
            print('Could not find device nearby: {}'.format(args.device))
            adapter.scan(enable=False)
            sys.exit(1)

        adapter.scan(enable=False)


    if dev.connected():
        print('Already connected: {}'.format(dev))
    else:
        if args.pair:
            if not dev.paired():
                print('Device is not paired')
                print('Connecting/pairing to: {}'.format(str(dev)))
                dev.pair()
                # waait for paring-agent
                wait_secs = 60
                while wait_secs > 0 and not dev.paired():
                    wait_secs -= 1
                    sleep(1)
                if not dev.paired():
                    print("Pairing failed")
                    sys.exit(1)

                if not dev.trusted():
                    dev.trust(True)
                    print('Device is now trusted')

        if not dev.connect():
            print('Connecting failed')
            sys.exit(1)

    gatt = Gatt(dev, [device_information])

    gatt.resolve()
    if not dev.services_resolved:
        print('Waited not long enough for service resolving, did not find uuids')
        sys.exit(1)

    print('Service UUIDs resolved')

    dev_info = gatt.device_information # pylint: disable=no-member

    for dinfo in dev_info.chars:
        if dinfo.obj:
            print(dinfo.name, ':', dinfo.read(options={'timeout': 4}))

    if args.wait > 0:
        sleep(args.wait)

    if args.loop:
        loop = GObject.MainLoop.new(None, False)

        for dinfo_char in dev_info.chars:
            if dinfo_char.obj:
                # add callback for printing if new value is avalable
                dinfo_char.onPropertiesChanged(print_char)

                # add cyclic read every 1 sec
                GObject.timeout_add_seconds(1, read_char, dinfo_char)


        try:
            loop.run()
        except (KeyboardInterrupt, SystemExit) as e:
            print('Interupted:', str(e))



    if not args.keep:
        dev.disconnect()


if __name__ == '__main__':
    main()
