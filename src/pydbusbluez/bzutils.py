
from pydbus import SystemBus
from . import error as bzerror
import logging

def get_managed_objects(sys_bus, obj_filter='/org/bluez/'):

    _proxy = sys_bus.get(
        'org.bluez', '/')

    return [obj for obj in _proxy.GetManagedObjects() if obj.startswith(obj_filter) ]



class BluezInterfaceObject(object):
    """All bluez dbus interfaces with the same name (org.bluez.NAME1)
    """
    bus = SystemBus()
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)

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
            self._obj = None

    def _def_iface_name(self):
        return 'org.bluez.{}1'.format(self.__class__.__name__)

    @bzerror.convertBluezError
    def onPropertiesChanged(self, func, prop=None, **kwargs):
        if self.obj:
            if self._proxy:
                prop_proxy = self._proxy
            else:
                prop_proxy = self.bus.get('org.bluez', self.obj)
            if not func:

                prop_proxy.onPropertiesChanged = None
                return
            self.logger.debug('Connecting to .PropertiesChanged on %s', self.obj)


            def changed_cb(*args):
                # the callback will be called with *args, arg[0] is Interface, arg[1] is dict with all
                # change propteries as keys (e.g. GattChar 'Value', Device 'Connected', etc.)
                # arg[2] ??, was empty list
                if args[0] == self._def_iface_name():
                    if not prop or prop in args[1]:
                        func(self, args[1], **kwargs)

            prop_proxy.onPropertiesChanged = changed_cb
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

    def __str__(self):
        return '{}(obj={},name={})'.format(self.__class__.__name__, self.obj, self.name)
