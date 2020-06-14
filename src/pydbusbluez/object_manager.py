
from pydbus import SystemBus
from xml.etree import ElementTree as ET

from . import error as bzerror
from .bzutils import ORG_BLUEZ, BluezInterfaceObject
import logging


class BluezObjectManager(object):
    bus = SystemBus()
    logger = logging.getLogger(__name__)
    logging.basicConfig()
    logger.setLevel(logging.DEBUG)
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
                raise ValueError("parent's 'obj' property is not set")
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

        key = parent_obj.obj
        id(parent_obj)

        # callback gets added
        if func:
            add_cb = False
            if not self.interfaces_added_cbs:
                add_cb = True
            self.logger.debug('add onObjectAddedCallback: func: %s(%s,%s,%s)', func, parent_obj, args, kwargs)

            # self.interfaces_added_cbs[key] = onObjectAddedCallback
            self.interfaces_added_cbs[key] = Callback(func, parent_obj, *args, **kwargs)
            self.logger.debug('added interface (%s) specific callback: %s', str(key), str(func))

            if add_cb:
                self._proxy.onInterfacesAdded = self._interfaces_added

        # callback gets removed
        else:
            # self.interfaces_added_cbs[key] = None
            del self.interfaces_added_cbs[key]
            self.logger.debug('Deleted interface specific %s cb', key)
            if not self.interfaces_added_cbs:
                try:
                    self._proxy.onInterfacesAdded = None
                except AttributeError: # Never was registered
                    pass

    # def onObjectAddedCallback(added_obj_path, added_interfaces):

    #     if filter_interface and filter_interface not in added_interfaces:
    #         return

    #     self.logger.debug('%s, %s', added_obj_path, added_interfaces)
    #     self.logger.debug('call onObjectAddedCallback: func: %s(%s,%s,%s,%s)', str(func), str(parent_obj), str(added_obj_path), str(args), str(kwargs))

    #     func(parent_obj, added_obj_path, added_interfaces, *args, **kwargs)


    # def onObjectAdded(self, parent_obj, func, *args, filter_interface=None, **kwargs):

    #     key = parent_obj.obj
    #     #id(parent_obj)
    #     # callback gets added
    #     if func:
    #         add_cb = False
    #         if not self.interfaces_added_cbs:
    #             add_cb = True
    #         self.logger.debug('add onObjectAddedCallback: func: %s(%s,%s,%s)', func, parent_obj, args, kwargs)

    #         def onObjectAddedCallback(added_obj_path, added_interfaces):

    #             if filter_interface and filter_interface not in added_interfaces:
    #                 return

    #             self.logger.debug('%s, %s', added_obj_path, added_interfaces)
    #             self.logger.debug('call onObjectAddedCallback: func: %s(%s,%s,%s,%s)', str(func), str(parent_obj), str(added_obj_path), str(args), str(kwargs))

    #             func(parent_obj, added_obj_path, added_interfaces, *args, **kwargs)

    #         self.interfaces_added_cbs[key] = onObjectAddedCallback
    #         self.logger.debug('added interface (%s) specific callback: %s', str(key), str(onObjectAddedCallback))

    #         if add_cb:
    #             self._proxy.onInterfacesAdded = self._interfaces_added

    #     # callback gets removed
    #     else:
    #         self.interfaces_added_cbs[key] = None
    #         del self.interfaces_added_cbs[key]
    #         self.logger.debug('Deleted interface specific %s cb', key)
    #         if not self.interfaces_added_cbs:
    #             try:
    #                 self._proxy.onInterfacesAdded = None
    #             except AttributeError: # Never was registered
    #                 pass



    # manage callbacks for different objects
    def _interfaces_added(self, added_obj, added_interfaces):

        self.logger.debug('added obj %s added interfaces %s', str(added_obj), str(added_interfaces))
        for key, callback in self.interfaces_added_cbs.items():
            if added_obj.startswith(key):
                # TODO do not call for every child
                if callback:
                    callback(added_obj, added_interfaces)


    def onObjectRemoved(self, obj, func, *args, **kwargs):

        #key = id(obj)
        key = obj.obj
        # callback gets added
        if func:
            add_cb = False
            if not self.interfaces_removed_cbs:
                add_cb = True
            self.logger.debug('add onObjectRemovedCallback: func: %s(%s,%s,%s)', func, obj, args, kwargs)

            # def onObjectRemovedCallback(removed_obj_path, removed_interfaces):
            #     if obj.iface not in removed_interfaces:
            #         return

            #     print('%s, %s', removed_obj_path, removed_interfaces)
            #     print('call onObjectRemovedCallback: func: %s(%s,%s,%s,%s)', str(func), str(obj), str(removed_obj_path), str(args), str(kwargs))
            #     func(obj, removed_interfaces, *args, **kwargs)
            #     obj.clear()

            # self.interfaces_removed_cbs[key] = onObjectRemovedCallback
            self.interfaces_removed_cbs[key] = Callback(func, obj, *args, **kwargs)
            self.logger.debug('added interface specific %s cb %s', str(key), str(Callback))


            if add_cb:
                self._proxy.onInterfacesRemoved = self._interfaces_removed

        # callback gets removed
        else:
            cb = self.interfaces_removed_cbs.pop(key, None)
            del cb
            self.logger.debug('Deleted interface specific %s cb', key)
            if not self.interfaces_removed_cbs:
                self._proxy.onInterfacesRemoved = None

    # manage callbacks for different objects
    # def _interfaces_removed(self, removed_obj, removed_interfaces):
    #     self.logger.debug('removed obj %s', str(removed_obj))
    #     self.logger.debug('removed interfaces %s', str(removed_interfaces))

    #     if removed_obj in self.interfaces_removed_cbs:
    #         if self.interfaces_removed_cbs[removed_obj]:
    #             self.interfaces_removed_cbs[removed_obj](removed_obj, removed_interfaces)
    #             del self.interfaces_removed_cbs[removed_obj]

    def _interfaces_removed(self, removed_obj, removed_interfaces):
        self.logger.debug('removed obj %s', str(removed_obj))
        self.logger.debug('removed interfaces %s', str(removed_interfaces))

        callback = self.interfaces_removed_cbs.get(removed_obj, None)
        if callback:
            callback(removed_obj, removed_interfaces)
            callback.__self__.clear()
            del self.interfaces_removed_cbs[removed_obj]


class Callback(object):
    __slots__ = ("__cb__", "__self__", "__args__", "__keywords__") # bound method uses ("__func__", "__self__")

    def __init__(self, signal, instance, *args, **keywords):
        self.__cb__ = signal
        self.__self__ = instance
        self.__args__ = args
        self.__keywords__ = keywords


    def __call__(self, *args, **kw):
        """Call callback"""
        print("Calling", str(self))
        self.__cb__(self.__self__, *args, *self.__args__, **{ **self.__keywords__, **kw})

    def __repr__(self):
        return "<bound callback " + str(self.__cb__) + " of " + repr(self.__self__) + ">"

    def __del__(self):
        print('Remove Callback: ' + self.__repr__())