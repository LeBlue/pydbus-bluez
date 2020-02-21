#!/usr/bin/env python3
import sys
from pydbus import SystemBus, Variant
from array import array

from .format import *
from .bzutils import get_managed_objects, BluezInterfaceObject

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

class Gatt(object):

    bus = SystemBus()
    logger = logging.getLogger(__name__ + '.Gatt')
    logger.setLevel(logging.INFO)

    # gatt object can ONLY be created After device is connected
    def __init__(self, dev, gatt_desc, warn_unmatched=True):
        self.dev = dev
        self.services = []


        for serv_desc in gatt_desc:
            key_service = _make_id(serv_desc['name'])
            new_service = GattService(serv_desc['name'], _convert_to_long_uuid(serv_desc['uuid']))
            setattr(self, key_service, new_service)

            self.services.append(new_service)
            if 'chars' in serv_desc:
                for char_desc in serv_desc['chars']:
                    key_char = _make_id(char_desc['name'])

                    new_characteristic = GattCharacteristic(
                        char_desc['name'], _convert_to_long_uuid(char_desc['uuid']), new_service)
                    setattr(new_service, key_char, new_characteristic)
                    new_service.chars.append(new_characteristic)
                    if 'form' in char_desc:
                        new_characteristic.form = char_desc['form']
                    else:
                        self.logger.warn('No \'form\' set for %s, using \'FormatRaw\'', new_characteristic.name)
                        new_characteristic.form = FormatRaw
                self.logger.debug(str(new_service.__dict__))
        self.logger.debug(str(self.__dict__))

        self.resolve(15, warn_unmatched=warn_unmatched)

    # gatt object can ONLY be created After device is connected and services are resolved
    @bzerror.convertBluezError
    def resolve(self, resolve_timeout=0, warn_unmatched=True):

        if not self.dev.services_resolved:
            self.logger.debug('Services not resolved, waiting for it for max: {}s'.format(resolve_timeout))
            if resolve_timeout > 0:
                if not self.dev.wait_services_resolved(resolve_timeout):
                    raise bzerror.BluezFailedError('Timeout waiting for services resolved')
            else:
                raise bzerror.BluezFailedError('Services are not resolved')

        # get all objects starting with '/org/bluez/adapter/device/'
        device_sub_objs = get_managed_objects(self.bus, self.dev.obj + '/')
        service_objs = [obj for obj in device_sub_objs if obj.split('/')[-1].startswith('service')]

        for service_obj in service_objs.copy():
            # only get services
            device_sub_objs.remove(service_obj)
            try:
                ser_proxy = self.bus.get(
                    'org.bluez', service_obj, 'org.bluez.GattService1')

            except bzerror.BluezDoesNotExistError:
                continue

            # match service uuids
            for service in self.services:
                if ser_proxy.UUID == service.uuid:
                    self.logger.debug(service)

                    service_objs.remove(service_obj)
                    service.obj = service_obj
                    # subobjects of this service

                    service_sub_objs = [
                        obj for obj in device_sub_objs if obj.startswith(service_obj + '/')]

                    # cross reference chars with uuids
                    for service_sub_obj in service_sub_objs.copy():
                        if service_sub_obj.split('/')[-1].startswith('char'):
                            char_obj = service_sub_obj
                            device_sub_objs.remove(char_obj)

                            try:
                                char_proxy = self.bus.get(
                                    'org.bluez', char_obj, 'org.bluez.GattCharacteristic1')
                            except bzerror.BluezDoesNotExistError as e:
                                self.logger.warn('%s: %s %s: %s', self.__class__.__name__, char_obj, str(e))
                                continue

                            char_uuid = char_proxy.UUID

                            for service_char_gatt in service.chars:
                                if char_uuid == service_char_gatt.uuid:
                                    service_char_gatt.obj = char_obj
                                    self.logger.debug(service_char_gatt)

                                    # remove from list, to find out, which we could not match to bluez objects
                                    service_sub_objs.remove(char_obj)

                                    # found matching characteristic to characteristing obj
                                    break


                    if warn_unmatched:
                        # local decription was not found on remote device
                        for gatt_char in service.chars:
                            if not gatt_char.obj:
                                self.logger.warn('%s: Not found on device: %s.%s',
                                    self.__class__.__name__, service.name,  gatt_char.name)

                        # remaining obj are not matched locally
                        for service_sub_obj in service_sub_objs:
                            # ignore descriptors for now
                            if service_sub_obj.split('/')[-1].startswith('char'):
                                try:
                                    uuid = self.bus.get(
                                        'org.bluez', service_sub_obj, 'org.bluez.GattCharacteristic1').UUID
                                except bzerror.BluezDoesNotExistError:
                                    uuid = 'unknown'

                                self.logger.warn('%s: Not found local: %s.%s (%s)',
                                    self.__class__.__name__, service.name, uuid, service_sub_obj)

                    # found match for service_obj -> gatt desciption uuid
                    break

        if warn_unmatched:
            for service in self.services:
                if not service.obj:
                    self.logger.warn('%s: Not found on device: %s',
                            self.__class__.__name__, service.name)

            for service_obj in service_objs:
                try:
                    uuid = self.bus.get(
                        'org.bluez', service_obj, 'org.bluez.GattService1').UUID
                except bzerror.BluezDoesNotExistError:
                    uuid = 'unknown'

                self.logger.warn('%s: Not found local: %ss (%s)',
                    self.__class__.__name__, uuid, service_obj)
        # a litte waring , if not found


    def help_keys(self):
        print('Valid attributes for the Gatt object are:', file=sys.stderr)
        for s in self.services:
            for c in s.chars:
                print('.{}.{} ({}found)'.format(
                    _make_id(s.name), _make_id(c.name), 'not ' if not c.obj else ''), file=sys.stderr)


class GattService(BluezInterfaceObject):

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


class GattCharacteristic(BluezInterfaceObject):

    def __init__(self, name, uuid, service):
        self.uuid = uuid.lower()
        self.form = FormatRaw
        self._obj = None
        self._proxy = None
        self.service = service
        self.name = name
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
                #v = self._proxy.ReadValue(options, timeout=to)
                v = bzerror.callBluezFunction(self._proxy.ReadValue, options, timeout=to)
            except bzerror.DBusTimeoutError:
                return None

            self.logger.debug('Read: {} {} {}'.format(v, type(v), self.form.__name__))
            if raw:
                return v
            else:
                v_dec = self.form.decode(v)
                return v_dec


        return None

    @property
    def value(self):
        val = self._getBluezPropOrNone('Value')
        if val != None:
           return self.form.decode(val)

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
    def notifyOn(self, func, enable=True, **kwargs):
        # to remove
        if self.obj:
            def val_changed_dec(gatt_char_self, changed_values, **kwargs):
                if 'Value' in changed_values:
                    gatt_value_obj = gatt_char_self.form.decode(
                        changed_values['Value'])
                    func(gatt_char_self, gatt_value_obj, **kwargs)

            self.onPropertiesChanged(val_changed_dec, 'Value', **kwargs)
            if enable:
                self._proxy.StartNotify()
        else:
            raise bzerror.BluezDoesNotExistError('Object not initialized: ' + str(self))

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



class GattDescriptor(BluezInterfaceObject):
    def __init__(self, name, uuid):
        self.name = name
        self.uuid = uuid.lower()
        self._obj = None
        self._proxy = None
        super().__init__(None)
