
from time import sleep
from pydbus import SystemBus, Variant

from .bzutils import BluezInterfaceObject
from .object_manager import BluezObjectManager
from . import error as bz
from .pydbus_backfill import ProxyMethodAsync

from gi.repository.GLib import Error as GLibError
from xml.etree import ElementTree as ET



class Adapter(BluezInterfaceObject):

    iface = 'org.bluez.{}1'.format(__qualname__)
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
        <interface name="org.bluez.Adapter1">
            <method name="StartDiscovery"/>
            <method name="SetDiscoveryFilter">
            <arg direction="in" name="properties" type="a{sv}"/>
            </method>
            <method name="StopDiscovery"/>
            <method name="RemoveDevice">
            <arg direction="in" name="device" type="o"/>
            </method>
            <method name="GetDiscoveryFilters">
            <arg direction="out" name="filters" type="as"/>
            </method>
            <property access="read" name="Address" type="s"/>
            <property access="read" name="AddressType" type="s"/>
            <property access="read" name="Name" type="s"/>
            <property access="readwrite" name="Alias" type="s"/>
            <property access="read" name="Class" type="u"/>
            <property access="readwrite" name="Powered" type="b"/>
            <property access="readwrite" name="Discoverable" type="b"/>
            <property access="readwrite" name="DiscoverableTimeout" type="u"/>
            <property access="readwrite" name="Pairable" type="b"/>
            <property access="readwrite" name="PairableTimeout" type="u"/>
            <property access="read" name="Discovering" type="b"/>
            <property access="read" name="UUIDs" type="as"/>
            <property access="read" name="Modalias" type="s"/>
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
        <interface name="org.bluez.GattManager1">
            <method name="RegisterApplication">
            <arg direction="in" name="application" type="o"/>
            <arg direction="in" name="options" type="a{sv}"/>
            </method>
            <method name="UnregisterApplication">
            <arg direction="in" name="application" type="o"/>
            </method>
        </interface>
        <interface name="org.bluez.LEAdvertisingManager1">
            <method name="RegisterAdvertisement">
            <arg direction="in" name="advertisement" type="o"/>
            <arg direction="in" name="options" type="a{sv}"/>
            </method>
            <method name="UnregisterAdvertisement">
            <arg direction="in" name="service" type="o"/>
            </method>
            <property access="read" name="ActiveInstances" type="y"/>
            <property access="read" name="SupportedInstances" type="y"/>
            <property access="read" name="SupportedIncludes" type="as"/>
            <property access="read" name="SupportedSecondaryChannels" type="as"/>
        </interface>
        <interface name="org.bluez.Media1">
            <method name="RegisterEndpoint">
            <arg direction="in" name="endpoint" type="o"/>
            <arg direction="in" name="properties" type="a{sv}"/>
            </method>
            <method name="UnregisterEndpoint">
            <arg direction="in" name="endpoint" type="o"/>
            </method>
            <method name="RegisterPlayer">
            <arg direction="in" name="player" type="o"/>
            <arg direction="in" name="properties" type="a{sv}"/>
            </method>
            <method name="UnregisterPlayer">
            <arg direction="in" name="player" type="o"/>
            </method>
            <method name="RegisterApplication">
            <arg direction="in" name="application" type="o"/>
            <arg direction="in" name="options" type="a{sv}"/>
            </method>
            <method name="UnregisterApplication">
            <arg direction="in" name="application" type="o"/>
            </method>
        </interface>
        <interface name="org.bluez.NetworkServer1">
            <method name="Register">
            <arg direction="in" name="uuid" type="s"/>
            <arg direction="in" name="bridge" type="s"/>
            </method>
            <method name="Unregister">
            <arg direction="in" name="uuid" type="s"/>
            </method>
        </interface>
    </node>
    '''
    introspection = ET.fromstring(intro_xml)

    @staticmethod
    def list():
        l = []
        for c in BluezObjectManager.get_childs(only_direct=True):
            try:
                name = c.split('/')[-1]
                l.append(Adapter(name))
            except:
                pass
        return l

    @bz.convertBluezError
    def __init__(self, name):
        try:
            super().__init__('/org/bluez/{}'.format(name), name)

        except (bz.BluezDoesNotExistError, bz.DBusUnknownObjectError):
            raise bz.BluezDoesNotExistError(
                'Adapter not found \'{}\''.format(name)) from None

        try:
            if not bz.getBluezPropOrRaise(self._proxy, 'Powered'):
                self._proxy.Powered = True

        except (bz.BluezDoesNotExistError, bz.DBusUnknownObjectError):
            raise bz.BluezDoesNotExistError(
                'Adapter not found \'{}\''.format(name)) from None



    @bz.convertBluezError
    def scan(self, enable=True, filters=None):
        '''
            enable:  enable/disable scanning
            filters: dict with scan filters, see bluez 'SetDiscoveryFilter' API:
                        'UUIDs': list with UUID strings
                        'Transport': string 'le', 'bredr' or 'auto'
        '''
        if enable:
            if filters and isinstance(filters, dict):
                # convert to Variants (for supported)
                if 'UUIDs' in filters and not isinstance(filters['UUIDs'], Variant):
                    filters['UUIDs'] = Variant('as', filters['UUIDs'])
                if 'Transport' in filters and not isinstance(filters['Transport'], Variant):
                    filters['Transport'] = Variant('s', filters['Transport'])

                bz.callBluezFunction(self._proxy.SetDiscoveryFilter, filters)
            try:
                bz.callBluezFunction(self._proxy.StartDiscovery)
            except bz.BluezInProgressError:
                pass
        else:
            try:
                bz.callBluezFunction(self._proxy.StopDiscovery)
            except bz.BluezFailedError:
                pass

        return bz.getBluezPropOrNone(self._proxy, 'Discovering', fail_ret=False)


    @property
    def scanning(self):
        return bz.getBluezPropOrNone(self._proxy, 'Discovering', fail_ret=False)


    @bz.convertBluezError
    def devices(self):
        '''
            returns list with all scanned/connected/paired devices
        '''
        l = []
        for obj in BluezObjectManager.get_childs(self.obj, only_direct=True):
            try:
                l.append(Device(adapter=self, obj=obj))
            except:
                pass
        return l

    def onDeviceAdded(self, func, *args, init=False, **kwargs):
        '''
            Registers callback for new device added/discovered

            func: callback function(device: Device, properties: dict, *args, **kwargs)
            init: set to True, to call func on all already existing devices
        '''
        om = BluezObjectManager.get()
        if func:
            def onDeviceAddedCallback(self_adapter, added_obj, added_if, *cbargs, **cbkwargs):
                if Device.iface in added_if:
                    addr = None
                    properties = added_if[Device.iface]
                    if 'Address' in added_if[Device.iface]:
                        addr = added_if[Device.iface]['Address']
                    device = Device(self_adapter, addr=addr, obj=added_obj)
                    if 'filter_interfaces' in cbkwargs:
                        del cbkwargs['filter_interfaces']

                    self.logger.debug('call onDeviceAddedCallback: func: %s(%s,%s,%s)', str(func), str(device), str(cbargs), str(cbkwargs))
                    func(device, properties, *cbargs, **cbkwargs)

            self.logger.debug('add onDeviceAddedCallback: func: %s(%s,%s,%s)', str(onDeviceAddedCallback), str(self), str(args), str(kwargs))
            om.onObjectAdded(self, onDeviceAddedCallback, *args, filter_interfaces=Device.iface, **kwargs)
            if init:
                dev_objs = om.childs(self, only_direct=True)
                for d in dev_objs:
                    try:
                        dev = Device(self, obj=d)
                        props = dev.properties
                    except:
                        continue
                    func(dev, props, *args, **kwargs)

        else:
            om.onObjectAdded(None, None)

    def onDeviceRemoved(self, func, *args, **kwargs):
        '''
            Registers callback for device removed (either removed explicitly or scanning cache timeout)
        '''
        om = BluezObjectManager.get()
        if func:
            def onDeviceAddedCallback(self_ref, removed_obj, removed_if, *cbargs, **cbkwargs):
                if Device.iface in removed_if:
                    if 'filter_interfaces' in cbkwargs:
                        del cbkwargs['filter_interfaces']

                    self.logger.debug('call onDeviceAddedCallback: func: %s(%s,%s,%s)', str(func), str(removed_obj), str(cbargs), str(cbkwargs))
                    func(removed_obj, *cbargs, **cbkwargs)

            self.logger.debug('add onDeviceAddedCallback: func: %s(%s,%s,%s)', str(onDeviceAddedCallback), str(self), str(args), str(kwargs))
            om.onObjectAdded(self, onDeviceAddedCallback, *args, filter_interfaces=Device.iface, **kwargs)
        else:
            om.onObjectAdded(None, None)


    @bz.convertBluezError
    def paired_devices(self):
        devs = self.devices()
        paired_devs = []
        for dev in devs:
            try:
                if dev.paired:
                    paired_devs.append(dev)
            except Exception:
                pass

        return paired_devs


    @bz.convertBluezError
    def remove_device(self, dev_obj):
        '''
            remove device: disconnect, remove pairing keys, delete gatt db cache (in bluez)
        '''
        self._proxy.RemoveDevice(dev_obj)



class Device(BluezInterfaceObject):

    iface = 'org.bluez.{}1'.format(__qualname__)
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
        <interface name="org.bluez.Device1">
            <method name="Disconnect"/>
            <method name="Connect"/>
            <method name="ConnectProfile">
            <arg direction="in" name="UUID" type="s"/>
            </method>
            <method name="DisconnectProfile">
            <arg direction="in" name="UUID" type="s"/>
            </method>
            <method name="Pair"/>
            <method name="CancelPairing"/>
            <property access="read" name="Address" type="s"/>
            <property access="read" name="AddressType" type="s"/>
            <property access="read" name="Name" type="s"/>
            <property access="readwrite" name="Alias" type="s"/>
            <property access="read" name="Class" type="u"/>
            <property access="read" name="Appearance" type="q"/>
            <property access="read" name="Icon" type="s"/>
            <property access="read" name="Paired" type="b"/>
            <property access="readwrite" name="Trusted" type="b"/>
            <property access="readwrite" name="Blocked" type="b"/>
            <property access="read" name="LegacyPairing" type="b"/>
            <property access="read" name="RSSI" type="n"/>
            <property access="read" name="Connected" type="b"/>
            <property access="read" name="UUIDs" type="as"/>
            <property access="read" name="Modalias" type="s"/>
            <property access="read" name="Adapter" type="o"/>
            <property access="read" name="ManufacturerData" type="a{qv}"/>
            <property access="read" name="ServiceData" type="a{sv}"/>
            <property access="read" name="TxPower" type="n"/>
            <property access="read" name="ServicesResolved" type="b"/>
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


    @bz.convertBluezError
    def __init__(self, adapter=None, addr=None, obj=None):
        super().__init__(obj, addr)
        if obj and not addr:
            if addr:
                self.name = addr
            else:
                self.name = self._getBluezPropOrNone('Address')
                if not self.name:
                    try:
                        self.name = obj.split('/')[4][4:].replace('_', ':')
                    except Exception:
                        pass

        if not adapter and obj:
            adapter = Adapter(obj.split('/')[3])
        self.adapter = adapter


    @bz.convertBluezError
    def pair(self):
        try:
            return bz.callBluezFunction(self._proxy.Pair)

        except bz.BluezAlreadyExistsError:
            self.logger.warning('Already paired: %s', str(self))
            return self.paired

        return False


    @property
    def paired(self):
        return self._getBluezPropOrNone('Paired', fail_ret=False)

    @property
    def connected(self):
        return self._getBluezPropOrNone('Connected', fail_ret=False)

    @bz.convertBluezError
    def connect_async(self, done_cb, err_cb, data, timeout=30):
        if done_cb:
            def _done_cb(obj, res, user_data):
                done_cb(self, res, user_data)
        else:
            _done_cb = None

        if err_cb:
            def _err_cb(obj, res, user_data):
                try:
                    bz.getDBusError(res)
                except Exception as e:
                    res = e
                err_cb(self, res, user_data)
        else:
            _err_cb = None

        self._proxy.ConnectAsync(_done_cb, _err_cb, data, timeout=timeout)


    @bz.convertBluezError
    def connect(self):
        try:
            self._proxy.Connect(timeout=10)
        except Exception as e:
            self.logger.error(str(e))
            pass


    @bz.convertBluezError
    def disconnect(self):
        try:
            bz.callBluezFunction(self._proxy.Disconnect)
        except bz.BluezInProgressError:
            return not self.connected
        except bz.DBusUnknownObjectError:
            pass

        return False


    @bz.convertBluezError
    def remove(self):
        if self.obj:
            ad_name = self.obj.split('/')[3]
            try:
                ad = Adapter(ad_name)
                ad.remove_device(self.obj)
            except bz.BluezError:
                pass



    # @bz.convertBluezError
    # def address(self):
    #     return self.name

    @property
    def address(self):
        return self.name


    @property
    def rssi(self):
        return self._getBluezPropOrNone('RSSI')


    @property
    def services_resolved(self):
        return self._getBluezPropOrNone('ServicesResolved', fail_ret=False)


    @bz.convertBluezError
    def wait_services_resolved(self, wait_resolved_sec):
        waitfor = 0

        self.logger.debug('resolved: %s',self._proxy.ServicesResolved)
        while not self.services_resolved and waitfor < wait_resolved_sec:
            if not self._proxy.Connected:
                raise bz.BluezNotConnectedError('Not connected')
            #waitfor -= 1
            waitfor += 1
            sleep(1)
        self.logger.info('Waited %s for resolving gatt DB uuids', waitfor)
        return self.services_resolved


    @property
    def device_name(self):
        return self._getBluezPropOrNone('Name')

    @property
    def trusted(self):
        return self._getBluezPropOrNone('Trusted', fail_ret=False)


    @bz.convertBluezError
    def trust(self, on=True):
        self._proxy.Trusted = on
        return self.trusted


__all__ = ('Device', 'Adapter')
