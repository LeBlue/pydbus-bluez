
from pydbus import SystemBus
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
        self.interfaces_added_cbs = {}
        self.interfaces_removed_cbs = {}


    @classmethod
    def get(cls):
        if not cls.manager:
            cls.manager = BluezObjectManager()

        return cls.manager


    def onAdapterAdded(self, func, obj, *args, **kwargs):
        self.onObjectAdded(func, obj, args)

    def onObjectAdded(self, parent_obj, func, *args, filter_interface=None, **kwargs):

        filter = parent_obj.obj

        # callback gets added
        if func:
            add_cb = False
            if not self.interfaces_added_cbs:
                add_cb = True
            self.logger.debug('add onObjectAddedCallback: func:', func, '(', parent_obj,',', args,',', kwargs, ')')

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

        for filter, callback in self.interfaces_added_cbs.items():
            if callback:
                if added_obj.startswith(filter):
                    callback(added_obj, added_interfaces)


    def onInterfaceRemoved(self, obj, func, *args, filter_interface=None, **kwargs):
        filter = parent_obj.obj

        # callback gets added
        if func:
            add_cb = False
            if not self.interfaces_removed_cbs:
                add_cb = True
            self.logger.debug('add onObjectRemovedCallback: func:', func, '(', parent_obj,',', args,',', kwargs, ')')

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


    def get_managed_(self, obj_filter='/org/bluez/'):

        return [obj for obj in self._proxy.GetManagedObjects() if obj.startswith(obj_filter) ]

    def get_childs(self, obj):
        if isinstanceof(obj, BluezInterfaceObject):
            obj_filter = obj.obj
        else:
            obj_filter = obj
        return [obj for obj in self._proxy.GetManagedObjects() if obj.startswith(obj_filter) ]


class BluezInterfaceObject(object):
    """All bluez dbus interfaces with the same name (org.bluez.NAME1)
    """
    bus = SystemBus()
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    iface = 'org.bluez.{}1'.format(__name__)

    @bzerror.convertBluezError
    def __init__(self, obj=None, name=None):
        self._proxy = None
        self._obj = None
        self.obj = obj
        self.name = name


    @property
    def obj(self):
        return self._obj

    @obj.setter
    def obj(self, obj):
        self._obj = obj
        if obj:
            self._proxy = self.bus.get(
                'org.bluez', obj, self._def_iface_name())
        else:
            try:
                self.onPropertiesChanged(None)
            except Exception:
                pass
            self._obj = None
            self._proxy = None


    def _def_iface_name(self):
        return 'org.bluez.{}1'.format(self.__class__.__name__)

    @bzerror.convertBluezError
    def onPropertiesChanged(self, func, *args, prop=None, **kwargs):
        """

        :param      func:    The function
        :type       func:    signature (self, prop_dict, *args, **kwargs)
        :param      args:    The arguments passed to func
        :type       args:    positional arguments to func
        :param      prop:    The property, triggering func, or None for triggering for all changed properties
        :type       prop:    str
        :param      kwargs:  The keywords arguments to func
        :type       kwargs:  dictionary
        """
        if self.obj:
            if self._proxy:
                prop_proxy = self._proxy
            else:
                prop_proxy = self.bus.get('org.bluez', self.obj)
            if not func:
                try:
                    prop_proxy.onPropertiesChanged = None
                except AttributeError:
                    pass
                return
            self.logger.debug('Connecting to .PropertiesChanged on %s', self.obj)


            def onPropertiesChangedCallback(iface, new_values, *args_int):
                # the callback will be called with *args, arg[0] is Interface, arg[1] is dict with all
                # change propteries as keys (e.g. GattChar 'Value', Device 'Connected', etc.)
                # arg[2] ??, was empty list
                if iface == self._def_iface_name():
                    if not prop or prop in new_values:
                        self.logger.debug('call onPropertiesChangedCallback: func: %s(%s,%s,%s,%s)', str(func), str(self), str(new_values), str(args), str(kwargs))
                        func(self, new_values, *args, **kwargs)

            prop_proxy.onPropertiesChanged = onPropertiesChangedCallback
        else:
            raise bzerror.BluezDoesNotExistError(
                'Object not set for {}'.format(str(self)))


    def _getBluezPropOrNone(self, prop, fail_ret=None):
        try:
            # first, convert error to own classes
            try:
                return getattr(self._proxy, prop, fail_ret)
            except (bzerror.BluezError, bzerror.DBusError):
                raise
            except Exception as e:
                bzerror.getDBusError(e)
        #if ont exists, return just None
        except (bzerror.BluezDoesNotExistError, bzerror.DBusUnknownObjectError):
            pass

        return fail_ret

    def clear(self):
        self.obj = None


    def __str__(self):
        return '{}(obj=\'{}\',name=\'{}\')'.format(self.__class__.__name__.split('.')[-1], self.obj, self.name)
