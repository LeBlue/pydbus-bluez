
from pydbus import SystemBus
from pydbus.proxy import ProxyMixin, CompositeInterface, Interface
from pydbus.auto_names import auto_bus_name, auto_object_path
from xml.etree import ElementTree as ET

from . import error as bzerror
import logging


def get_managed_objects(sys_bus, obj_filter='/org/bluez/'):

    _proxy = sys_bus.get(
        'org.bluez', '/')

    return [obj for obj in _proxy.GetManagedObjects() if obj.startswith(obj_filter) ]




class BluezObjectManager(object):
    bus = SystemBus()
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    manager = None


    def __init__(self):
        self._proxy = BluezObjectManager.bus.get(
            'org.bluez', '/')
        self.obj = '/'
        self.interfaces_added_cbs = {}
        self.interfaces_removed_cbs = {}


    @classmethod
    def get(cls):
        if not cls.manager:
            cls.manager = BluezObjectManager()

        return cls.manager


    # def onAdapterAdded(self, func, obj, *args, **kwargs):
    #     self.onObjectAdded(func, obj, args)


    def onAdapterAdded(self, func, name, *args, **kwargs):
        obj = '/org/bluez/' + name
        self.onObjectAdded(self, func, obj, *args, filter_interface='org.bluez.Adapter1', **kwargs)

    def onObjectAdded(self, parent_obj, func, *args, filter_interface=None, **kwargs):

        filter = parent_obj.obj

        # callback gets added
        if func:
            add_cb = False
            if not self.interfaces_added_cbs:
                add_cb = True
            self.logger.debug('add onObjectAddedCallback: func: %s(%s,%s,%s)', func, parent_obj, args, kwargs)

            def onObjectAddedCallback(added_obj_path, added_interfaces, *cbargs, **cbkwargs):
                if filter_interface and filter_interface not in added_interfaces:
                    return

                self.logger.debug('%s, %s', added_obj_path, added_interfaces)
                self.logger.debug('call onObjectAddedCallback: func: %s(%s,%s,%s,%s)', str(func), str(parent_obj), str(added_obj_path), str(args), str(kwargs))
                self.logger.debug('call onObjectAddedCallback: ignored:(%s, %s)', str(cbargs), str(cbkwargs))

                return func(parent_obj, added_obj_path, added_interfaces, *args, **kwargs)

            self.interfaces_added_cbs[filter] = onObjectAddedCallback
            self.logger.debug('added interface specific %s cb %s', str(filter), str(onObjectAddedCallback))

            if add_cb:
                self._proxy.onInterfacesAdded = self._interfaces_added

        # callback gets removed
        else:
            self.interfaces_added_cbs[filter] = None
            del self.interfaces_added_cbs[filter]
            self.logger.debug('Deleted interface specific %s cb', filter)
            if not self.interfaces_added_cbs:
                self._proxy.onInterfacesAdded = None



    # manage callbacks for different objects
    def _interfaces_added(self, added_obj, added_interfaces):
        self.logger.debug('added obj %s', str(added_obj))
        self.logger.debug('added interfaces %s', str(added_interfaces))

        cbs = []
        for filter, callback in self.interfaces_added_cbs.items():
            if callback:
                if added_obj.startswith(filter):
                    cbs.append(callback)

        # for cbs manipulating the interfaces_added_cbs
        for cb in cbs:
            cb(added_obj, added_interfaces)


    def onInterfaceRemoved(self, obj, func, *args, filter_interface=None, **kwargs):
        filter = parent_obj.obj

        # callback gets added
        if func:
            add_cb = False
            if not self.interfaces_removed_cbs:
                add_cb = True
            self.logger.debug('add onObjectRemovedCallback: func: %s(%s,%s,%s)', func, parent_obj, args, kwargs)

            def onObjectRemovedCallback(removed_obj_path, removed_interfaces, *cbargs, **cbkwargs):
                if filter_interface and filter_interface not in removed_interfaces:
                    return

                self.logger.debug('%s, %s', removed_obj_path, removed_interfaces)
                self.logger.debug('call onObjectRemovedCallback: func: %s(%s,%s,%s,%s)', str(func), str(parent_obj), str(removed_obj_path), str(args), str(kwargs))
                self.logger.debug('call onObjectRemovedCallback: ignored:(%s, %s)', str(cbargs), str(cbkwargs))

                return func(parent_obj, removed_obj_path, removed_interfaces, *args, **kwargs)

            self.interfaces_removed_cbs[filter] = onObjectRemovedCallback
            self.logger.debug('removed interface specific %s cb %s', str(filter), str(onObjectRemovedCallback))


            if add_cb:
                self._proxy.onInterfacesAdded = self._interfaces_removed

        # callback gets removed
        else:
            self.interfaces_removed_cbs[filter] = None
            del self.interfaces_removed_cbs[filter]
            self.logger.debug('Deleted interface specific %s cb', filter)
            if not self.interfaces_removed_cbs:
                self._proxy.onInterfacesRemoved = None

    # manage callbacks for different objects
    def _interfaces_removed(self, removed_obj, removed_interfaces):
        self.logger.debug('removed obj %s', str(removed_obj))
        self.logger.debug('removed interfaces %s', str(removed_interfaces))

        for filter, callback in self.interfaces_removed_cbs.items():
            if callback:
                if removed_obj.startswith(filter):
                    callback(removed_obj, removed_interfaces)

