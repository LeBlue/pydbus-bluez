
from pydbus import SystemBus
from xml.etree import ElementTree as ET

from . import error as bzerror
from .bzutils import ORG_BLUEZ, BluezInterfaceObject
import logging


class BluezObjectManager(object):
    bus = SystemBus()
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    manager = None

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
        <interface name="org.freedesktop.DBus.ObjectManager">
            <method name="GetManagedObjects">
            <arg direction="out" name="objects" type="a{oa{sa{sv}}}"/>
            </method>
            <signal name="InterfacesAdded">
            <arg name="object" type="o"/>
            <arg name="interfaces" type="a{sa{sv}}"/>
            </signal>
            <signal name="InterfacesRemoved">
            <arg name="object" type="o"/>
            <arg name="interfaces" type="as"/>
            </signal>
        </interface>
        </node>
    '''
    introspection = ET.fromstring(intro_xml)

    def __init__(self):
        self._proxy = BluezObjectManager.bus.construct(self.introspection, ORG_BLUEZ, '/')
        self.obj = '/'
        self.interfaces_added_cbs = {}
        self.interfaces_removed_cbs = {}


    @classmethod
    def get(cls):
        if not cls.manager:
            cls.manager = BluezObjectManager()

        return cls.manager

    @classmethod
    def objects(cls):
        try:
            objs = cls.get()._proxy.GetManagedObjects()
        except Exception:
            objs = []
        return objs


    @classmethod
    def get_childs(cls, parent='/org/bluez', only_direct=False):

        if isinstance(parent, BluezInterfaceObject):
            if not parent.obj:
                raise TypeError("parent's 'obj' property is not set")
            filter = parent.obj + '/'
        else:
            filter = parent + '/'

        objs = cls.objects()


        if only_direct:
            pathlen = len(filter.split('/'))
            return [ obj for obj in objs if obj.startswith(filter) and pathlen == len(obj.split('/')) ]

        return [ obj for obj in objs if obj.startswith(filter) ]

    def childs(self, parent, only_direct=False):
        if isinstance(parent, BluezInterfaceObject):
            if not parent.obj:
                raise TypeError("parent's 'obj' property is not set")
            filter = parent.obj + '/'
        else:
            filter = parent + '/'

        objs = self.__class__.objects()


        if only_direct:
            pathlen = len(filter.split('/'))
            return [ obj for obj in objs if obj.startswith(filter) and pathlen == len(obj.split('/')) ]


        return [ obj for obj in objs if obj.startswith(filter) ]


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

            def onObjectAddedCallback(added_obj_path, added_interfaces):

                if filter_interface and filter_interface not in added_interfaces:
                    return

                self.logger.debug('%s, %s', added_obj_path, added_interfaces)
                self.logger.debug('call onObjectAddedCallback: func: %s(%s,%s,%s,%s)', str(func), str(parent_obj), str(added_obj_path), str(args), str(kwargs))

                func(parent_obj, added_obj_path, added_interfaces, *args, **kwargs)

            self.interfaces_added_cbs[filter] = onObjectAddedCallback
            self.logger.debug('added interface (%s) specific callback: %s', str(filter), str(onObjectAddedCallback))

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


    def onObjectRemoved(self, obj, func, *args, filter_interface=None, **kwargs):

        filter = obj.obj
        # callback gets added
        if func:
            add_cb = False
            if not self.interfaces_removed_cbs:
                add_cb = True
            self.logger.debug('add onObjectRemovedCallback: func: %s(%s,%s,%s)', func, obj, args, kwargs)

            def onObjectRemovedCallback(removed_obj_path, removed_interfaces):
                if filter_interface and filter_interface not in removed_interfaces:
                    return

                self.logger.debug('%s, %s', removed_obj_path, removed_interfaces)
                self.logger.debug('call onObjectRemovedCallback: func: %s(%s,%s,%s,%s)', str(func), str(obj), str(removed_obj_path), str(args), str(kwargs))
                return func(removed_obj_path, removed_interfaces, *args, **kwargs)

            self.interfaces_removed_cbs[filter] = onObjectRemovedCallback
            self.logger.debug('removed interface specific %s cb %s', str(filter), str(onObjectRemovedCallback))


            if add_cb:
                self._proxy.onInterfacesRemoved = self._interfaces_removed

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

