
from pydbus import SystemBus
from pydbus.proxy import ProxyMixin, CompositeInterface, Interface
from pydbus.auto_names import auto_bus_name, auto_object_path
from xml.etree import ElementTree as ET

from . import error as bzerror
import logging

from pydbus.proxy import ProxyMethod
from .pydbus_backfill import InterfaceBackfilled, construct, backfill_async_dbus_methods


ProxyMixin.construct = construct
Interface = InterfaceBackfilled

ORG_BLUEZ = 'org.bluez'

class BluezInterfaceObject(object):
    """All bluez dbus interfaces with the same name (org.bluez.NAME1)

        Should not be used directly, derived classes must provide the
        class property 'introspection' with a ElementTree parsed introspection xml
    """
    bus = SystemBus()
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    iface = '{}.{}1'.format(ORG_BLUEZ, __name__)
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
        </node>
    '''
    introspection = ET.fromstring(intro_xml)

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
            self._proxy = self.bus.construct(self.introspection, ORG_BLUEZ, obj)
            try:
                _ = self._proxy.GetAsync
            except AttributeError:
                backfill_async_dbus_methods(self._proxy, self.introspection)
        else:
            try:
                self.onPropertiesChanged(None)
            except Exception:
                pass
            self._obj = None
            self._proxy = None

    def _def_iface_name(self):
        return '{}.{}1'.format(ORG_BLUEZ, self.__class__.__name__)

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
                prop_proxy = self.bus.construct(self.introspection, ORG_BLUEZ, self.obj)
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
                # arg[2] invalidated propertes
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
        # if not exists, return just None/ret_fail
        except (bzerror.BluezDoesNotExistError, bzerror.DBusUnknownObjectError):
            pass

        return fail_ret

    def clear(self):
        self.obj = None


    def __str__(self):
        return '{}(obj=\'{}\',name=\'{}\')'.format(self.__class__.__name__.split('.')[-1], self.obj, self.name)
