#!/usr/bin/env python3

import sys
from argparse import ArgumentParser

import pydbusbluez as bluez
from pydbusbluez.format import FormatTuple, FormatRaw, FormatBase, FormatPacked, FormatUint

from gi.repository.GLib import MainLoop, timeout_add_seconds
from importlib import import_module

import cmd
import time
import ast


def generic_notify(gatt_char, new_value):
    print('Value changed:', _make_id(gatt_char.name), str(new_value))


def dev_connected_changed(dev, new_value):
    print('Device status changed:', str(new_value))
    if 'Connected' in new_value:
        if not new_value['Connected']:
            print('Disconnected:', str(dev))


def adapter_changed(adap, new_value):
    print('Adapter changed:', str(new_value))


class CmdTimeout(object):

    def __init__(self, timeout_secs, loop):
        self.timeout = timeout_secs
        self.remaining = timeout_secs
        self.canceled = False
        def mainloop_quit():
            loop.quit()

        self.expired_cb = mainloop_quit
        timeout_add_seconds(1, self._tick)


    def _tick(self):
        self.remaining -= 1
        if self.remaining <= 0 and not self.canceled:
            self.canceled = True
            if self.expired_cb:
                self.expired_cb()
            return False

        return not self.canceled

def bt_connect(GATT, adapter, addr, timeout):
    d = None
    try:
        adapter_obj = bluez.Adapter(adapter)
        devs = adapter_obj.devices()
        for d in devs:
            if d.name == addr.upper():
                break
        if not d:
            adapter_obj.scan()
            time.sleep(timeout)

        devs = adapter_obj.devices()
        for d in devs:
            if d.name == addr.upper():
                break

        if d:
            d.connect()
        if d.connected:
            return bluez.Gatt(d, GATT)

    except bluez.BluezError as e:
        print('Failed:', str(e), file=sys.stderr)





def main():
    parser = ArgumentParser(description='BT (my_peripheral) command interpreter')
    parser = ArgumentParser(
    description='Peripheral connect and set/get values (for "my_peripheral.GATT")')

    _def_adapter = 'hci0'
    _def_scan = 5

    parser.add_argument('-i', '--adapter', metavar='hciX', default=_def_adapter,
                        help='bluetooh adapter to use (default={})'.format(_def_adapter))

    parser.add_argument('-d', '--scan-duration', metavar='sec', default=_def_scan, type=int,
                        help='scan duration in seconds (default={})'.format(_def_scan))

    parser.add_argument('-a', '--address', nargs='?', default=None, help='device address(es) to connect to')

    parser.add_argument('-g', '--gatt', metavar='MOD', default=None, help='gatt description to import (PACKAGE.MODULE:[GATT_VARIABLE]')


    parser.add_argument('script', default=None, nargs='*', type=str, help='commands to run from script(s), see the run/record commands')

    parser.convert_arg_line_to_args = lambda self, arg_line: arg_line.split()

    print(parser)
    args = parser.parse_args()


    if args.gatt:
        gatt_module = args.gatt.split(':')[0]
        try:
            gatt_mod = import_module(gatt_module)
        except ImportError as e:
            print(str(e), file=sys.stderr)
            sys.exit(1)
        try:
            gatt_var = 'GATT'
            if len(args.gatt.split(':')) > 1:
                gatt_var = args.gatt.split(':')[1]
            GATT = getattr(gatt_mod, gatt_var)
        except AttributeError as e:
            print('Failed to import gatt profile:', str(e), file=sys.stderr)
            GATT = []
    else:
        GATT = []


    # gatt = None
    # if args.address:
    #     gatt = bt_connect(GATT, args.adapter, args.address, args.scan_duration)


    shell = BTShell(GATT, device_addr=args.address, adapter=args.adapter, scan_duration=args.scan_duration)
    # shell.make_prompt()
    # add connect command
    if args.address:
        shell.cmdqueue.append('connect '+ args.address)

    shell.load_scripts(args.script)
    # try:
    #     for script in args.script:
    #         with open(script) as f:
    #             shell.cmdqueue.extend(f.read().splitlines())
    # except FileNotFoundError as e:
    #     print(str(e))
    #     sys.exit(1)
    try:
        shell.cmdloop()
    except KeyboardInterrupt:
        print('quit')


def _make_id(s):
    id = s.lower().replace(' ', '_').replace('-', '_')
    if id.isidentifier():
        return id

    #TODO
    raise ValueError('Invalid id: {}'.format(id))

def _gatt_valid(gatt):
    try:
        if gatt and gatt.dev and gatt.dev.connected:
            return True
    except bluez.BluezError:
        pass
    return False

class BTShell(cmd.Cmd):
    intro = 'Welcome to the BT test shell.   Type help or ? to list commands.\n'
    prompt_start = '(bt) '
    file = None

    def __init__(self, gatt_db_description, device_addr, *args, adapter='hci0', scan_duration=5, **kwargs):
        self.gatt = None
        self.gatt_db_description = gatt_db_description
        self.adapter = adapter
        self.device_addr = device_addr
        self.scan_duration = scan_duration
        self.clp_cache = self.build_clpt_cache(self.gatt_db_description)
        self.autoconnect = False
        self.autoconnecting = False
        super().__init__(*args, **kwargs)

        self.scan_filters = None
        self.make_prompt()

    def bt_connect(self):
        d = None
        try:
            adapter_obj = bluez.Adapter(self.adapter)
            devs = adapter_obj.devices()
            for d in devs:
                if d.name == self.device_addr.upper():
                    break
            if not d:
                adapter_obj.scan()
                time.sleep(self.scan_duration)

            devs = adapter_obj.devices()
            for d in devs:
                if d.name == self.device_addr.upper():
                    break

            if d:
                d.connect()
            if d.connected:
                return bluez.Gatt(d, self.gatt_db_description)

        except bluez.BluezError as e:
            print('Failed:', str(e), file=sys.stderr)

    def load_scripts(self, scripts):
        try:
            for script in scripts:
                with open(script) as f:
                    print('Loading:', script)
                    shell.cmdqueue.extend(f.read().splitlines())
            return True
        except FileNotFoundError as e:
            print(str(e))
        return False

    def make_prompt(self):
        if _gatt_valid(self.gatt):
            self.prompt = '{}{} $ '.format(self.prompt_start, self.gatt.dev.name)
        else:
            if self.autoconnect:
                # try only once
                if self.autoconnecting:
                    self.autoconnecting = False
                    self.autoconnect = True
                else:
                    self.autoconnecting = True
                    self.cmdqueue.append('connect ' + self.device_addr)
            else:
                self.prompt = '{}{} $ '.format(self.prompt_start, 'disconnected')

    def build_clpt_cache(self, gatt_desc):
        ca = []
        for s in gatt_desc:
            for c in s['chars']:
                el = _make_id(c['name'])
                ca.append(el)
                if 'descriptors' in c:
                    for d in c['descriptors']:
                        ca.append(el + '_' + _make_id(d['name']))
        return ca

    def build_clpt_cache_gatt(self):
        ca = []
        for s in self.gatt.services:
            for c in s.chars:
                el = _make_id(c.name)
                ca.append(el)
                for d in c.descriptors:
                    ca.append(el + '_' + _make_id(d.name))
        return ca

    def find_char_or_desc_obj(self, name):
        if name not in self.clp_cache:
            print('Not found:', name)
            return
        if self.gatt:
            for s in self.gatt.services:
                for c in s.chars:
                    c_name = _make_id(c.name)
                    if c_name == name:
                        return c
                    if name.startswith(c_name):
                        for d in c.descriptors:
                            if c_name + '_' + _make_id(d.name) == name:
                                return d

        else:
            print('Disconnected')
            if self.autoconnect:
                self.cmdqueue.append('connect ' + self.device_addr)

        return None

    def _char_names_complete(self, text, line, begidx, endidx):
        if not text:
            return self.clp_cache
        clp = [arg for arg in self.clp_cache if arg.startswith(text)]
        return clp

    # ----- basic bt commands -----
    def do_set(self, arg):
        'set a value: formated as simple python types, e.g 1, "foo", (1,5), [0,4,5]'
        args = _parse_args_simple(arg)
        if len(args) < 2:
            print('set: Need an argument, simple python types, e.g 1, "foo", (1, 5), [0,4,5]', file=sys.stderr)

        o = self.find_char_or_desc_obj(args[0])
        if not o:
            print('set: Not valid:', args[0])
            return
        try:
            exp_arg = ' '.join(args[1:])
            #print('arg is: \'{}\''.format(exp_arg))
            v = ast.literal_eval(exp_arg)
        except (ValueError, SyntaxError) as e:
            print('set: ', arg, str(e), file=sys.stderr)
            return
        try:
            exp = o.fmt(v)
        except Exception as e:
            print(str(e), file=sys.stderr)
            return
        try:
            o.write(exp)
        except bluez.BluezError as e:
            print('set: ', arg, str(e), file=sys.stderr)




    def complete_set(self, text, line, begidx, endidx):
        if len(line) != endidx:
            return None
        pl = _parse_args_simple(line)

        if len(pl) < 2 or (len(pl) == 2 and line[-1] != ' '):
            return self._char_names_complete(text, line, begidx, endidx)

        o = self.find_char_or_desc_obj(pl[1])
        if not o:
            print('complete not foud: ', pl[1], file=sys.stderr)
            return None
        if not o.fmt:
            print('format not foud: ', pl[1], file=sys.stderr)
            return None

        return None

    def do_get(self, arg):
        'get (fetch) a characteristic value or all values'
        #print(arg)
        g_chars = _parse_args_simple(arg)
        #print(str(arg.split(' ')))
        if not g_chars:
            g_chars = self.clp_cache
        #print('reading: ', str(g_chars))

        for g_char in g_chars:
            o = self.find_char_or_desc_obj(g_char)
            if not o:
                print(
                    'get:', g_char, 'Not valid in GATT database or not resolved', file=sys.stderr)
                continue
            try:
                v = o.read()
            except bluez.BluezError as e:
                print('get: ', g_char, str(e), file=sys.stderr)
                continue

            print(_make_id(o.name), v, file=sys.stderr)

    def complete_get(self, text, line, begidx, endidx):
        if len(line) != endidx:
            return None
        return self._char_names_complete(text, line, begidx, endidx)

    def do_info(self, arg):
        'show information about characteristic value type'
        g_chars = _parse_args_simple(arg)
        print(str(arg.split(' ')))
        if len(g_chars) != 1:
            print('info: Expectect one arugment', file=sys.stderr)
            return
        o = self.find_char_or_desc_obj(g_chars[0])
        if not o:
            print('Not found:', g_chars[0])
            return
        d = None
        if isinstance(o, bluez.GattDescriptor):
            d = o
            o = d.char
        print(str(o.service))
        print(str(o))
        fmt = o.fmt
        if d:
            print(str(d))
            fmt = d.fmt
        else:
            print(o.flags)

        if not issubclass(fmt, FormatBase):
            print('Unkown format', file=sys.stderr)
        else:
            if issubclass(fmt, FormatTuple):

                fields = []
                for idx, sc in enumerate(fmt.sub_cls):
                    try:
                        fields.append("'{}': {}".format(fmt.sub_cls_names[idx], sc.__name__))
                    except (AttributeError, IndexError):
                        fields.append("{}".format(sc.__name__))

                print('{} ({})'.format(str(fmt.__name__), ', '.join(fields), file=sys.stderr))
            else:
                print('{} python native: {}'.format(str(fmt.__name__), str(fmt.native_types), file=sys.stderr))

        print(str(fmt))

    complete_info = _char_names_complete

    def do_value(self, arg):
        'Get the last known value of characteristic'
        print(arg)
        g_chars = _parse_args_simple(arg)
        if not g_chars:
            g_chars = self.clp_cache

        for g_char in g_chars:
            o = self.find_char_or_desc_obj(g_char)
            if not o:
                print('value:', g_char, 'Not valid in GATT database', file=sys.stderr)
                continue
            try:
                v = o.value
            except bluez.BluezError as e:
                print('value:', o.name, str(e), file=sys.stderr)
                return

            print(o.name, v)

    complete_value = _char_names_complete

    def do_autoconnect(self, arg):
        'reconnect on disconnection before next command'
        self.autoconnect = True

    def do_connect(self, arg):
        'connect device or select device for interaction. When no paramter is given, -a option or last parameter will be used as address'
        args = _parse_args_simple(arg)
        if len(args) == 0:
            if _gatt_valid(self.gatt) and self.gatt.dev.connected:
                print('Already connected', file=sys.stderr)
                return

        elif len(args) > 1:
            print('At most one argument expected (device address)', file=sys.stderr)
            return
        else:
            self.device_addr = args[0]

        if _gatt_valid(self.gatt) and self.gatt.dev.name.lower() == args[0].lower() and self.gatt.dev.connected:
            print('Already connected', file=sys.stderr)
            self.clp_cache = self.build_clpt_cache_gatt()
            return
        self.gatt = None

        try:
            self.gatt = self.bt_connect()
            print('Connected', file=sys.stderr)
            self.clp_cache = self.build_clpt_cache_gatt()

        except bluez.BluezError as e:
            print('connect', str(e), file=sys.stderr)

    def complete_connect(self, text, line, begidx, endidx):
        if len(line) != endidx:
            return None
        pl = _parse_args_simple(line)
        #  (len(pl) == 2 and line[-1] != ' ') or
        if len(pl) == 2 or (len(pl) == 1 and line.endswith(' ')):
            try:
                hci = bluez.Adapter(self.adapter)
                devs = hci.devices()

            except bluez.BluezError:
                print('autocomplete failed', file=sys.stderr)
                return None
            return [ d.name for d in devs if d.name.lower().startswith(text.lower()) ]

        return None

    def do_scan(self, arg):
        'enable/disable scanning (on/off)'
        pl = _parse_args_simple(arg)
        if len(pl) == 0 or pl[0] == 'on':
            enable = True
        elif pl[0] == 'off':
            enable = False
        else:
            print('Argument needs to be on/off')
            return
        try:
            hci = bluez.Adapter(self.adapter)
            scanning = hci.scan(enable=enable, filters=self.scan_filters)
            print("Scanning:", scanning)
        except bluez.BluezError:
            print('Setting scanning failed', file=sys.stderr)
            return None

    def complete_scan(self, text, line, begidx, endidx):
        return [ en for en in ['on', 'off'] if en.startswith(text) ]


    def do_db_schema(self, arg):
        'dump resolved gatt schema'
        if self.gatt:
            self.gatt.dump()
        else:
            print('Disconnected', file=sys.stderr)

    def do_dump_db_schema(self, arg):
        'dump resolved db schema to file'
        args = _parse_args_simple(arg)
        if len(args) != 1:
            print('Need file to dump schema into as argument')
            return
        f = args[0] if args[0].endswith('.py') else args[0] + '.py'
        if not self.gatt or not self.gatt.dev.services_resolved:
            print("DB not resolved, try connecting first", file=sys.stderr)
            return
        print("Writing", f)
        with open(f, 'w') as schema_file:
            header = [
                'import pydbusbluez.format as fmt\n',
                'import pydbusbluez.org_bluetooth\n',
                '\n',
            ]
            footer = []
            schema_file.writelines(header)
            if self.gatt.dev.device_name:
                schema_file.write('# GATT schema for {}\n'.format(self.gatt.dev.device_name))
            schema_file.write('GATT = [\n')
            for s in sorted(self.gatt.services, key=lambda x: x.uuid):
                if s.obj:
                    schema_file.writelines(
                        ['\t{\n',
                        '\t\t"name": "{}",\n'.format(s.name),
                        '\t\t"uuid": "{}",\n'.format(s.uuid),
                        '\t\t"chars": [\n'
                        ]
                    )
                    for c in sorted(s.chars, key=lambda x: x.uuid):

                        if c.obj:
                            schema_file.writelines(
                                ['\t\t\t{{ # {}\n'.format(c.flags),
                                '\t\t\t\t"name": "{}",\n'.format(c.name),
                                '\t\t\t\t"uuid": "{}",\n'.format(c.uuid),
                                '\t\t\t\t"fmt": fmt.{},\n'.format(str(c.fmt)),
                                ])
                            if len(c.descriptors) > 0:
                                schema_file.writelines(
                                    [
                                    '\t\t\t\t"descriptors": [\n'
                                    ]
                                )
                            for d in sorted(c.descriptors, key=lambda x: x.uuid):
                                if d.obj:
                                    schema_file.writelines(
                                        ['\t\t\t\t\t{\n',
                                        '\t\t\t\t\t\t"name": "{}",\n'.format(d.name),
                                        '\t\t\t\t\t\t"uuid": "{}",\n'.format(d.uuid),
                                        '\t\t\t\t\t\t"fmt": fmt.{},\n'.format(str(d.fmt)),
                                        '\t\t\t\t\t},\n',
                                        ]
                                    )
                            if len(c.descriptors) > 0:
                                #close descriptor list
                                schema_file.write('\t\t\t\t],\n')

                            # close char obj
                            schema_file.write('\t\t\t},\n')

                    # close char list
                    schema_file.write('\t\t],\n')
                    # close service obj
                    schema_file.write('\t},\n')

            # close service list
            schema_file.write(']\n')
            schema_file.writelines(footer)

    def do_disconnect(self, arg):
        'disconnect currently selected device'
        if self.gatt and self.gatt.dev and self.gatt.dev.connected:
            g = self.gatt
            self.gatt = None
            g.dev.disconnect()

        else:
            self.gatt = None
        print('Disconnected', file=sys.stderr)

    def do_sleep(self, arg):
        'sleep for n seconds'
        args = _parse_args_simple(arg)
        if not args:
            print('Need number of seconds as argument', file=sys.stderr)
        try:
            s = int(args[0])
        except Exception as e:
            print(str(e))
            return

        time.sleep(s)

    def do_echo(self, arg):
        print(arg, file=sys.stderr)

    def default(self, line):
        args = _parse_args_simple(line)
        if not args[0].startswith('#'):
            print('Unkonwn commmand:', args[0], file=sys.stderr)
        else:
            if line[1:2]:
                print(line[1:])
            else:
                print(line[2:])

    def do_notify(self, arg):
        'enable all notifications and print changed values'
        args = _parse_args_simple(arg)
        timeout_seconds = None
        if len(args) > 0:
            try:
                timeout_seconds = int(args[0])
            except Exception as e:
                print(str(e))
                return

        for s in self.gatt.services:
            for c in s.chars:
                try:
                    flags = c.flags
                    if 'notify' in flags or 'indicate' in flags:
                        c.onValueChanged(generic_notify)
                        c.notifyOn()
                    elif 'read' in flags:
                        c.onValueChanged(generic_notify)

                except bluez.BluezDoesNotExistError as e:
                    print(c.name, str(e), file=sys.stderr)

        loop = MainLoop.new(None, False)

        self.gatt.dev.onPropertiesChanged(dev_connected_changed)
        timeout = None
        if timeout_seconds:
            timeout = CmdTimeout(timeout_seconds, loop)
        try:
            if timeout_seconds:
                print('Notifying for {} seconds'.format(
                    timeout_seconds), file=sys.stderr)
            else:
                print('Notifiying, CTRL+C to end', file=sys.stderr)

            loop.run()
        except (KeyboardInterrupt, bluez.BluezError) as e:
            print('aborted:', self.gatt.dev.name, str(e), file=sys.stderr)
            loop.quit()
            if timeout:
                timeout.canceled = True

    def complete_notify_single(self, text, line, begidx, endidx):
        if len(line) != endidx:
            return None
        return self._char_names_complete(text, line, begidx, endidx)

    def do_notify_single(self, arg):
        'enable notifications on char and print changed values'
        args = _parse_args_simple(arg)
        timeout_seconds = None
        if len(args) > 1:
            try:
                timeout_seconds = int(args[1])
            except Exception as e:
                print(str(e))
                return
        else:
            print('To few arguments (char, [timeout[)')
            return

        g_char = self.find_char_or_desc_obj(args[0])
        if not g_char:
            print(
                'get:', str(g_char), 'Not valid in GATT database or not resolved', file=sys.stderr)
            return

        c = g_char
        try:
            flags = c.flags
            if 'notify' in flags or 'indicate' in flags:
                c.onValueChanged(generic_notify)
                c.notifyOn()
            elif 'read' in flags:
                c.onValueChanged(generic_notify)

        except bluez.BluezDoesNotExistError as e:
            print(c.name, str(e), file=sys.stderr)

        loop = MainLoop.new(None, False)

        self.gatt.dev.onPropertiesChanged(dev_connected_changed)
        timeout = None
        if timeout_seconds:
            timeout = CmdTimeout(timeout_seconds, loop)
        try:
            if timeout_seconds:
                print('Notifying for {} seconds'.format(
                    timeout_seconds), file=sys.stderr)
            else:
                print('Notifiying, CTRL+C to end', file=sys.stderr)

            loop.run()
        except (KeyboardInterrupt, bluez.BluezError) as e:
            print('aborted:', self.gatt.dev.name, str(e), file=sys.stderr)
            loop.quit()
            if timeout:
                timeout.canceled = True



    def do_quit(self, arg):
        self.close()
        return True

    # ----- record and playback -----
    def do_record(self, arg):
        'Save future commands to filename: record somefile.btsh'
        if not _parse_args_simple(arg):
            print("Need filename argument")
            return
        try:
            self.file = open(arg, 'w')
        except Exception as e:
            print(str(e))

    def do_run(self, arg):
        'Run commands from a file: somefile.btsh'
        if not _parse_args_simple(arg):
            print("Need filename argument")
            return
        self.close()
        try:
            with open(arg) as f:
                self.cmdqueue.extend(f.read().splitlines())
        except Exception as e:
            print('run:', arg, str(e))

    def precmd(self, line):
        if self.file and 'run' not in line:
            print(line, file=self.file)
        return line

    def postcmd(self, stop, line):
        if stop:
            return True

        self.make_prompt()
        return False

    def emptyline(self):
        pass

    def close(self):
        if self.file:
            self.file.close()
            self.file = None



def _parse_args_simple(arg):
    return [ a for a in arg.split(' ') if a != '' ]


if __name__ == '__main__':
    main()
