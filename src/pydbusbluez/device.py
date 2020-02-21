
from time import sleep
from pydbus import SystemBus, Variant

from .bzutils import get_managed_objects, BluezInterfaceObject, BluezObjectManager
from . import error as bz

from gi.repository.GLib import Error as GLibError


class Adapter(BluezInterfaceObject):

    iface = 'org.bluez.{}1'.format(__name__)

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
        p_devs = []
        for dev in devs:
            try:
                if dev.paired():
                    p_devs.append(dev)
            except GLibError as e:
                self.logger.error(str(e))
                raise


        return p_devs


    @bz.convertBluezError
    def remove_device(self, dev_obj):
        self._proxy.RemoveDevice(dev_obj)



class Device(BluezInterfaceObject):


    iface = 'org.bluez.{}1'.format(__name__)

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
            self.logger.warn('Already paired: %s', str(self))
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
