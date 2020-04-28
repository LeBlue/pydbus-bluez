#!/usr/bin/env python3
import sys
from pydbus import SystemBus, Variant
from array import array
from xml.etree import ElementTree as ET

from .format import *
from .bzutils import BluezInterfaceObject, ORG_BLUEZ
from .object_manager import get_managed_objects
from .device import Device

from . import error as bzerror
import logging

def _make_id(s):
    id = s.lower().replace(' ', '_').replace('-', '_')
    if id.isidentifier():
        return id

    #TODO
    raise ValueError('Invalid id: {}'.format(id))

def _convert_to_long_uuid(uuid):
    if len(uuid) == 4:
        return '0000{}-0000-1000-8000-00805f9b34fb'.format(uuid)
    if len(uuid) == 8:
        return '{}-0000-1000-8000-00805f9b34fb'.format(uuid)
    return uuid


def _is_obj_device(obj):
    return obj.split('/')[-1].startswith('dev')

def _is_obj_service(obj):
    return obj.split('/')[-1].startswith('service')

def _is_obj_characteristic(obj):
    return obj.split('/')[-1].startswith('char')

def _is_obj_descriptor(obj):
    return obj.split('/')[-1].startswith('desc')

def _sub_objects(obj, object_list):
    sub_path = obj + '/'
    return [ sub for sub in object_list if sub.startswith(sub_path)]

def _is_sub_object_of(obj, sub):
    sub_path = obj + '/'
    return sub.startswith(sub_path)



class Gatt(object):

    bus = SystemBus()
    logger = logging.getLogger(__name__ + '.Gatt')
    logger.setLevel(logging.DEBUG)

    def add_service(self, name, uuid):
        key_service = _make_id(name)
        new_service = GattService(name, _convert_to_long_uuid(uuid))
        setattr(self, key_service, new_service)

        self.services.append(new_service)
        return new_service

    # gatt object can ONLY be created After device is connected
    def __init__(self, dev, gatt_desc, warn_unmatched=True):
        self.dev = dev
        self.services = []

        for serv_desc in gatt_desc:
            new_service = self.add_service(serv_desc['name'], serv_desc['uuid'])
            if 'chars' in serv_desc:
                for char_desc in serv_desc['chars']:
                    char_form = char_desc['form'] if 'form' in char_desc else FormatRaw
                    new_characteristic = new_service.add_characteristic(char_desc['name'], char_desc['uuid'], char_form)

                    if 'descriptors' in char_desc:
                        for desc_desc in char_desc['descriptors']:
                            desc_form = desc_desc['form'] if 'form' in desc_desc else FormatRaw
                            _ = new_characteristic.add_descriptor(desc_desc['name'], desc_desc['uuid'], desc_form)

                        self.logger.debug(str(new_characteristic.__dict__))

                self.logger.debug(str(new_service.__dict__))

        self.logger.debug(str(self.__dict__))

        self.resolve(15, warn_unmatched=warn_unmatched)

    # gatt object can ONLY be created After device is connected and services are resolved
    @bzerror.convertBluezError
    def resolve(self, resolve_timeout=0, warn_unmatched=True, resolve_unknown=True):

        if not self.dev.services_resolved:
            self.logger.debug('Services not resolved, waiting for it for max: {}s'.format(resolve_timeout))
            if resolve_timeout > 0:
                if not self.dev.wait_services_resolved(resolve_timeout):
                    raise bzerror.BluezFailedError('Timeout waiting for services resolved')
            else:
                raise bzerror.BluezFailedError('Services are not resolved')

        # get all objects starting with '/org/bluez/adapter/device/'
        device_sub_objs = get_managed_objects(self.bus, self.dev.obj + '/')
        service_objs_unmatched = [obj for obj in device_sub_objs if _is_obj_service(obj)]
        for service_obj in service_objs_unmatched.copy():
            # only get services
            device_sub_objs.remove(service_obj)
            service_proxy = self.bus.construct(GattService.introspection,
                ORG_BLUEZ, service_obj)

            service_uuid = bzerror.getBluezPropOrNone(service_proxy, 'UUID')
            if not service_uuid:
                continue

            # match service uuids
            for service in self.services:
                if service_uuid == service.uuid:
                    service_objs_unmatched.remove(service_obj)
                    service._obj = service_obj
                    service._proxy = service_proxy
                    self.logger.debug("Found: %s", str(service))


        # either warn or set generic names for unmatched

                    # subobjects of this service
                    service_sub_objs = _sub_objects(service_obj, device_sub_objs)

                    # cross reference char objects with uuids
                    matched_objs = service._resolve_characteristics(service_sub_objs)
                    for matched_obj in matched_objs:
                        device_sub_objs.remove(matched_obj)
                        service_sub_objs.remove(matched_obj)

                    if warn_unmatched:
                        # local decription was not found on remote device
                        for gatt_char in service.chars:
                            if not gatt_char.obj:
                                self.logger.warning('%s: Not found on device: %s.%s',
                                    self.__class__.__name__, service.name,  gatt_char.name)

                        # remaining obj are not matched locally
                        for service_sub_obj in service_sub_objs:
                            # ignore descriptors for now
                            if _is_obj_characteristic(service_sub_obj):

                                proxy = self.bus.construct(GattCharacteristic.introspection,
                                        ORG_BLUEZ, service_sub_obj)

                                uuid = bzerror.getBluezPropOrNone(proxy, 'UUID')

                                self.logger.warning('%s: Not found local: %s.%s (%s)',
                                    self.__class__.__name__, service.name, uuid, service_sub_obj)

                    # found match for service_obj -> gatt desciption uuid
                    break

        if warn_unmatched:
            for service in self.services:
                if not service.obj:
                    self.logger.warning('%s: Not found on device: %s',
                            self.__class__.__name__, service.name)

            for service_obj in service_objs_unmatched:

                proxy = self.bus.construct(GattService.introspection,
                    ORG_BLUEZ, service_obj)
                uuid = bzerror.getBluezPropOrNone(proxy, 'UUID')

                self.logger.warning('%s: Not found local: %ss (%s)',
                    self.__class__.__name__, uuid, service_obj)
        # a litte waring , if not found


    def clear(self):
        for s in self.services:
            for c in s.chars:
                try:
                    c._proxy.onPropertiesChanged = None
                except AttributeError:
                    pass
                c.obj = None
                c.service = None
                c._proxy = None
            try:
                s._proxy.onPropertiesChanged = None
            except AttributeError:
                pass

            s.chars = None
            s.obj = None
            s._proxy = None
        self.services = None

    def help_keys(self):
        print('Valid attributes for the Gatt object are:', file=sys.stderr)
        for s in self.services:
            for c in s.chars:
                print('.{}.{} ({}found)'.format(
                    _make_id(s.name), _make_id(c.name), 'not ' if not c.obj else ''), file=sys.stderr)


class GattService(BluezInterfaceObject):

    iface = 'org.bluez.{}1'.format(__name__)
    intro_xml = '''<?xml version="1.0" ?>
        <!DOCTYPE node
        PUBLIC '-//freedesktop//DTD D-BUS Object Introspection 1.0//EN'
        'http://www.freedesktop.org/standards/dbus/1.0/introspect.dtd'>
        <node>
        <interface name="org.freedesktop.DBus.Introspectable">
            <method name="Introspect">
            <arg direction="out" name="xml" type="s"/>
            </method>
        </interface>
        <interface name="org.bluez.GattService1">
            <property access="read" name="UUID" type="s"/>
            <property access="read" name="Device" type="o"/>
            <property access="read" name="Primary" type="b"/>
            <property access="read" name="Includes" type="ao"/>
        </interface>
        <interface name="org.freedesktop.DBus.Properties">
            <method name="Get">
            <arg direction="in" name="interface" type="s"/>
            <arg direction="in" name="name" type="s"/>
            <arg direction="out" name="value" type="v"/>
            </method>
            <method name="Set">
            <arg direction="in" name="interface" type="s"/>
            <arg direction="in" name="name" type="s"/>
            <arg direction="in" name="value" type="v"/>
            </method>
            <method name="GetAll">
            <arg direction="in" name="interface" type="s"/>
            <arg direction="out" name="properties" type="a{sv}"/>
            </method>
            <signal name="PropertiesChanged">
            <arg name="interface" type="s"/>
            <arg name="changed_properties" type="a{sv}"/>
            <arg name="invalidated_properties" type="as"/>
            </signal>
        </interface>
        </node>'''
    introspection = ET.fromstring(intro_xml)

    def __init__(self, name, uuid):
        # self.name = name
        self.uuid = uuid.lower()
        self.chars = []
        super().__init__(None, name)

    def __str__(self):
        return '{}(obj=\'{}\',name=\'{}\',uuid=\'{}\')'.format(
                self.__class__.__name__.split('.')[-1],
                self.obj,
                self.name,
                self.uuid
            )

    @property
    def device(self):
        dev_path = bzerror.getBluezPropOrNone(self._proxy, 'Device')
        if dev_path:
            try:
                return Device(obj=dev_path)
            except bzerror.BluezError:
                pass

        return None

    def add_characteristic(self, name, uuid, form=None):
        key_char = _make_id(name)
        new_characteristic = GattCharacteristic(name, _convert_to_long_uuid(uuid), self)

        setattr(self, key_char, new_characteristic)
        self.chars.append(new_characteristic)

        if form:
            new_characteristic.form = form
        else:
            self.logger.warning('No \'form\' set for %s, using \'FormatRaw\'', new_characteristic.name)
            new_characteristic.form = FormatRaw

        return new_characteristic

    def _resolve_characteristics(self, objects, warn_unmatched=False, resolve_unknown=True):
        matched_chars = []
        for obj in objects:
            if not _is_obj_characteristic(obj):
                continue

            proxy = SystemBus().construct(GattCharacteristic.introspection, ORG_BLUEZ, obj)
            uuid = bzerror.getBluezPropOrNone(proxy, 'UUID')

            if not uuid:
                # TODO: remember that this failed to match?
                continue

            for char in self.chars:
                if char.uuid == uuid:
                    # char.obj = obj
                    char._proxy = proxy
                    char._obj = obj
                    matched_chars.append(obj)
                    char_sub_objs = _sub_objects(obj, objects)
                    matched_desc = char._resolve_descriptors(char_sub_objs)
                    matched_chars.extend(matched_desc)
                    break


        return matched_chars


class GattCharacteristic(BluezInterfaceObject):

    iface = 'org.bluez.{}1'.format(__name__)
    intro_xml = '''<?xml version="1.0" ?>
        <!DOCTYPE node
        PUBLIC '-//freedesktop//DTD D-BUS Object Introspection 1.0//EN'
        'http://www.freedesktop.org/standards/dbus/1.0/introspect.dtd'>
        <node>
        <interface name="org.freedesktop.DBus.Introspectable">
            <method name="Introspect">
            <arg direction="out" name="xml" type="s"/>
            </method>
        </interface>
        <interface name="org.bluez.GattCharacteristic1">
            <method name="ReadValue">
            <arg direction="in" name="options" type="a{sv}"/>
            <arg direction="out" name="value" type="ay"/>
            </method>
            <method name="WriteValue">
            <arg direction="in" name="value" type="ay"/>
            <arg direction="in" name="options" type="a{sv}"/>
            </method>
            <method name="AcquireWrite">
            <arg direction="in" name="options" type="a{sv}"/>
            <arg direction="out" name="fd" type="h"/>
            <arg direction="out" name="mtu" type="q"/>
            </method>
            <method name="AcquireNotify">
            <arg direction="in" name="options" type="a{sv}"/>
            <arg direction="out" name="fd" type="h"/>
            <arg direction="out" name="mtu" type="q"/>
            </method>
            <method name="StartNotify"/>
            <method name="StopNotify"/>
            <property access="read" name="UUID" type="s"/>
            <property access="read" name="Service" type="o"/>
            <property access="read" name="Value" type="ay"/>
            <property access="read" name="Notifying" type="b"/>
            <property access="read" name="Flags" type="as"/>
            <property access="read" name="WriteAcquired" type="b"/>
            <property access="read" name="NotifyAcquired" type="b"/>
        </interface>
        <interface name="org.freedesktop.DBus.Properties">
            <method name="Get">
            <arg direction="in" name="interface" type="s"/>
            <arg direction="in" name="name" type="s"/>
            <arg direction="out" name="value" type="v"/>
            </method>
            <method name="Set">
            <arg direction="in" name="interface" type="s"/>
            <arg direction="in" name="name" type="s"/>
            <arg direction="in" name="value" type="v"/>
            </method>
            <method name="GetAll">
            <arg direction="in" name="interface" type="s"/>
            <arg direction="out" name="properties" type="a{sv}"/>
            </method>
            <signal name="PropertiesChanged">
            <arg name="interface" type="s"/>
            <arg name="changed_properties" type="a{sv}"/>
            <arg name="invalidated_properties" type="as"/>
            </signal>
        </interface>
        </node>
    '''
    introspection = ET.fromstring(intro_xml)

    def __init__(self, name, uuid, service):
        self.uuid = uuid.lower()
        self.form = FormatRaw
        self._obj = None
        self._proxy = None
        self.service = service
        self.name = name
        self.descriptors = []
        super().__init__(None, name)

    @bzerror.convertBluezError
    def read(self, options={}, raw=False, native=True):

        if options and 'timeout' in options:
            to = options['timeout']
            del options['timeout']
        else:
            to = None

        if options and 'offset' in options and not isinstance(options['offset'], Variant):
            options['offset'] = Variant('q', options['offset'])

        if self._proxy:
            try:
                v = bzerror.callBluezFunction(self._proxy.ReadValue, options, timeout=to)
            except bzerror.DBusTimeoutError:
                return None

            self.logger.debug('Read: {} {} {}'.format(v, type(v), self.form.__name__))
            if raw:
                return v
            else:
                try:
                    v_dec = self.form.decode(v)
                except Exception as e:
                    raise bzerror.BluezDecodeError('{}: {}, got: {}'.format(self, str(e), str(v)))
                return v_dec


        return None

    @bzerror.convertBluezError
    def read_async(self, success_cb, error_cb, user_data, options={}, raw=False, native=True):

        if self._proxy:
            if error_cb:
                def _error_cb(proxy, err, data):
                    try:
                        bzerror.getDBusError(err)
                    except Exception as e:
                        error_cb(self, e, data)
            else:
                _error_cb = None

            if success_cb:
                def _success_cb(proxy, result, data):
                    # result conaines tuple with one element of bytes list
                    if len(result):
                        value = result[0]
                        try:
                            if not raw:
                                v_dec = self.form.decode(value)
                        except bzerror.BluezError as e:
                            err = bzerror.BluezDecodeError('{}: {}, got: {}'.format(self, str(e), str(value)))
                            error_cb(self, err, data)
                            return
                        success_cb(self, v_dec, data)
                    else:
                        error_cb(self, bzerror.BluezFailedError("No value was returned"), data)
            else:
                _success_cb = None

            # try:
            self._proxy.ReadValueAsync(_success_cb, _error_cb, user_data, options)
            # except bzerror.BluezError as e:
            #     # error_cb(self, e, user_data)
            #     raise

        else:
            raise bzerror.BluezDoesNotExistError("Not found: " + self.name)

    @property
    def value(self):
        val = self._getBluezPropOrNone('Value')
        if val != None:
            try:
                return self.form.decode(val)
            except Exception:
                pass
        return None

    @bzerror.convertBluezError
    def flags(self):
        if self._proxy:
            return self._proxy.Flags
        return []

    @bzerror.convertBluezError
    def write(self, value, options={}):

        if self._proxy:
            if isinstance(value, bytes):
                v_obj = value
                v_enc = value
            else:
                if isinstance(value, self.form):
                    v_obj = value
                    v_enc = value.encode()
                else:
                    v_obj = self.form(value)
                    v_enc = v_obj.encode()


                length = 0
            if 'length' in options:
                length = options['length']
                del options['length']
                if not isinstance(length, int):
                    raise TypeError('Length key in \'options\' must be \'int\'')
                if len(v_enc) > length:
                    v_enc = v_enc[:length]

            self.logger.debug('Write: {} {} {}'.format(v_enc, str(v_obj), self.form.__name__))

            self._proxy.WriteValue(v_enc, options)


    @bzerror.convertBluezError
    def onValueChanged(self, func, *args, **kwargs):
        # to remove
        if self.obj:
            def valueChangedCallback(gatt_char_self, changed_values, *cbargs, **cbkwargs):
                if 'Value' in changed_values:
                    gatt_value_obj = gatt_char_self.form.decode(
                        changed_values['Value'])
                    func(gatt_char_self, gatt_value_obj, *cbargs, **cbkwargs)

            self.onPropertiesChanged(valueChangedCallback, *args, prop='Value', **kwargs)
        else:
            raise bzerror.BluezDoesNotExistError('Object not initialized: ' + str(self))

    def notifyOn(self):
        if self.obj:
            if not self.notifying:
                self._proxy.StartNotify()
        else:
            raise bzerror.BluezDoesNotExistError('Failed to enable notify: {}'.format(str(self)))


    def notifyOff(self):
        if self.obj:
            try:
                self.onPropertiesChanged(None)
                if self.notifying:
                    self._proxy.StopNotify()
            except bzerror.BluezError:
                pass

    @property
    def notifying(self):
        if self.obj:
            try:
                return self._proxy.Notifying
            except bzerror.BluezError:
                pass
        return False

    def __str__(self):
        return '{}(obj=\'{}\',name=\'{}\',uuid=\'{}\',form=\'{}\')'.format(
                self.__class__.__name__.split('.')[-1],
                self.obj,
                self.name,
                self.uuid,
                self.form.__name__.split('.')[-1]
            )

    def add_descriptor(self, name, uuid, form=FormatRaw):
        new_descriptor = GattDescriptor(name, _convert_to_long_uuid(uuid), self)
        new_descriptor.form = form

        key_desc = _make_id(name)

        setattr(self, key_desc, new_descriptor)
        self.descriptors.append(new_descriptor)
        return new_descriptor

    def _resolve_descriptors(self, objects, warn_unmatched=False):
        matched_descriptors = []
        for obj in objects:
            proxy = SystemBus().construct(GattDescriptor.introspection, ORG_BLUEZ, obj)
            uuid = bzerror.getBluezPropOrNone(proxy, 'UUID')

            if not uuid:
                # TODO: remember that this failed to match?
                continue

            for desc in self.descriptors:
                if desc.uuid == uuid:
                    # desc.obj = obj
                    desc._proxy = proxy
                    desc._obj = obj
                    matched_descriptors.append(obj)

        return matched_descriptors



class GattDescriptor(BluezInterfaceObject):

    iface = 'org.bluez.{}1'.format(__name__)
    intro_xml = '''<?xml version="1.0" ?>
        <!DOCTYPE node
        PUBLIC '-//freedesktop//DTD D-BUS Object Introspection 1.0//EN'
        'http://www.freedesktop.org/standards/dbus/1.0/introspect.dtd'>
        <node>
        <interface name="org.freedesktop.DBus.Introspectable">
            <method name="Introspect">
            <arg direction="out" name="xml" type="s"/>
            </method>
        </interface>
        <interface name="org.bluez.GattDescriptor1">
            <method name="ReadValue">
            <arg direction="in" name="options" type="a{sv}"/>
            <arg direction="out" name="value" type="ay"/>
            </method>
            <method name="WriteValue">
            <arg direction="in" name="value" type="ay"/>
            <arg direction="in" name="options" type="a{sv}"/>
            </method>
            <property access="read" name="UUID" type="s"/>
            <property access="read" name="Characteristic" type="o"/>
            <property access="read" name="Value" type="ay"/>
        </interface>
        <interface name="org.freedesktop.DBus.Properties">
            <method name="Get">
            <arg direction="in" name="interface" type="s"/>
            <arg direction="in" name="name" type="s"/>
            <arg direction="out" name="value" type="v"/>
            </method>
            <method name="Set">
            <arg direction="in" name="interface" type="s"/>
            <arg direction="in" name="name" type="s"/>
            <arg direction="in" name="value" type="v"/>
            </method>
            <method name="GetAll">
            <arg direction="in" name="interface" type="s"/>
            <arg direction="out" name="properties" type="a{sv}"/>
            </method>
            <signal name="PropertiesChanged">
            <arg name="interface" type="s"/>
            <arg name="changed_properties" type="a{sv}"/>
            <arg name="invalidated_properties" type="as"/>
            </signal>
        </interface>
        </node>'''

    introspection = ET.fromstring(intro_xml)

    def __init__(self, name, uuid, char):
        # self.name = name
        self.uuid = uuid.lower()
        self.form = FormatRaw
        self._obj = None
        self._proxy = None
        self.char = char

        super().__init__(None, name)

# def __init__(self, name, uuid, service):
#         self.uuid = uuid.lower()
#         self.form = FormatRaw
#         self._obj = None
#         self._proxy = None
#         self.service = service
#         self.name = name
#         super().__init__(None, name)

    def __str__(self):
        return '{}(obj=\'{}\',name=\'{}\',uuid=\'{}\',form=\'{}\')'.format(
                self.__class__.__name__.split('.')[-1],
                self.obj,
                self.name,
                self.uuid,
                self.form.__name__.split('.')[-1]
            )

    read = GattCharacteristic.read
    read_async = GattCharacteristic.read_async
    write = GattCharacteristic.write
    value = GattCharacteristic.value
