
from time import sleep
from pydbus import SystemBus, Variant

from .bzutils import BluezInterfaceObject
from .object_manager import get_managed_objects, BluezObjectManager
from . import error as bz
from .pydbus_backfill import ProxyMethodAsync

from gi.repository.GLib import Error as GLibError
from xml.etree import ElementTree as ET



class Adapter(BluezInterfaceObject):

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

    @bz.convertBluezError
    def __init__(self, name):
        try:
            super().__init__('/org/bluez/{}'.format(name), name)

        # try:
        #     self._proxy = bz.callBluezFunction(self.bus.get, 'org.bluez', self._obj, iface='org.bluez.Adapter1')
        except bz.BluezDoesNotExistError:
            raise bz.BluezDoesNotExistError(
                'Adapter not found \'{}\''.format(name)) from None

        if not self._proxy.Powered:
            self._proxy.Powered = True


    @bz.convertBluezError
    def scan(self, enable=True, args=None):
        if enable:
            if args:
                # convert to Variants (for supported)
                if 'UUIDs' in args and not isinstance(args['UUIDs'], Variant):
                    args['UUIDs'] = Variant('as', args['UUIDs'])
                if 'Transport' in args and not isinstance(args['Transport'], Variant):
                    args['Transport'] = Variant('s', args['Transport'])

                bz.callBluezFunction(self._proxy.SetDiscoveryFilter, args)
            try:
                bz.callBluezFunction(self._proxy.StartDiscovery)
            except bz.BluezInProgressError:
                pass
        else:
            try:
                bz.callBluezFunction(self._proxy.StopDiscovery)
            except bz.BluezFailedError:
                pass

        return self._proxy.Discovering


    @bz.convertBluezError
    def scanning(self):
        return self._proxy.Discovering


    @bz.convertBluezError
    def devices(self):
        return [ Device(adapter=self, obj=obj) for obj in get_managed_objects(self.bus, self.obj + '/dev') if len(obj.split('/')) == 5 ]


    def onDeviceAdded(self, func, *args, **kwargs):
        om = BluezObjectManager.get()
        if func:
            def onDeviceAddedCallback(self_ref, added_obj, added_if, *cbargs, **cbkwargs):
                if Device.iface in added_if:
                    addr = None
                    if 'Address' in added_if[iface]:
                        addr = added_if[iface]['Address']
                    d = Device(self, addr=addr, obj=added_obj)
                    if 'filter_interfaces' in cbkwargs:
                        del cbkwargs['filter_interfaces']

                    self.logger.debug('call onDeviceAddedCallback: func: %s(%s,%s,%s)', str(func), str(d), str(cbargs), str(cbkwargs))
                    func(d, *cbargs, **cbkwargs)

            self.logger.debug('add onDeviceAddedCallback: func: %s(%s,%s,%s)', str(onDeviceAddedCallback), str(self), str(args), str(kwargs))
            om.onObjectAdded(self, onDeviceAddedCallback, *args, filter_interfaces=Device.iface, **kwargs)
        else:
            om.onObjectAdded(None, None)

    def onDeviceRemoved(self, func, *args, **kwargs):
        om = BluezObjectManager.get()
        if func:
            def onDeviceAddedCallback(self_ref, removed_obj, removed_if, *cbargs, **cbkwargs):
                if Device.iface in removed_if:
                    addr = None
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
                try:
                    self.name = self._proxy.Address
                except DBusError as e:
                    raise BluezDoesNotExistError(str(e)) from None
        self.adapter = adapter


    @bz.convertBluezError
    def pair(self):
        try:
            return bz.callBluezFunction(self._proxy.Pair)

        except bz.BluezAlreadyExistsError:
            self.logger.warning('Already paired: %s', str(self))
            return self.paired()

        return False


    @bz.convertBluezError
    def paired(self):
        return self._getBluezPropOrNone('Paired', fail_ret=False)


    @bz.convertBluezError
    def connected(self):
        return self._getBluezPropOrNone('Connected', fail_ret=False)

    @bz.convertBluezError
    def connect(self):
        self._proxy.Connect()

        return self.connected()

    @bz.convertBluezError
    def connect_async(self):
        try:
            self._proxy.Connect(timeout=3)
        except Exception as e:
            self.logger.error(str(e))
            pass


    @bz.convertBluezError
    def disconnect(self):
        try:
            bz.callBluezFunction(self._proxy.Disconnect)
        except bz.BluezInProgressError:
            return not self.connected()
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



    @bz.convertBluezError
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


    @bz.convertBluezError
    def trusted(self):
        return self._getBluezPropOrNone('Trusted', fail_ret=False)


    @bz.convertBluezError
    def trust(self, on=True):
        self._proxy.Trusted = on
        return self.trusted()


__all__ = ('Device', 'Adapter')
