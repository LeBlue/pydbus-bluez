from types import MethodType

from pydbus.proxy import ProxyObject, ProxyMixin, Interface, CompositeInterface
from pydbus.proxy_method import ProxyMethod, put_signature_in_doc
from pydbus.proxy_property import ProxyProperty
from pydbus.proxy_signal import ProxySignal, OnSignal
from pydbus.auto_names import auto_bus_name, auto_object_path
from pydbus.timeout import timeout_to_glib

from gi.repository.GLib import Variant, VariantType

def construct(self, introspection_et, bus_name, object_path=None):
    """Construct proxy for remote object.

    This works exactly like .get() but constructs the proxy
    from static introspection provided as additional parameter

    In contrast to .get() the dbus object does not need to exist on the bus and
    the introspection data can be cached by the application or statically be provided

    Parameters
    ----------
    introspection_et : ElementTree node object containing introspection data

    >>> from xml.etree import ElementTree as ET
    >>> intro = ET.fromstring(SystemBus().get('org.bluez').Introspect()[0])
    >>> o = SystemBus.get(intro, 'org.bluez')

    """
    bus_name = auto_bus_name(bus_name)
    object_path = auto_object_path(bus_name, object_path)
    ci = CompositeInterface(introspection_et)(self, bus_name, object_path)
    backfill_async_dbus_methods(ci, introspection_et)
    return ci

ProxyMixin.construct = construct

class ProxyMethodAsync(object):
	def __init__(self, iface_name, method):
		self._iface_name = iface_name
		self.__name__ = method.__name__ + 'Async'
		self.__qualname__ = self._iface_name + "." + self.__name__

		self._inargs  = method._inargs
		self._outargs = method._outargs
		self._sinargs  = method._sinargs
		self._soutargs = method._soutargs

		self.__signature__ = method.__signature__

		if put_signature_in_doc:
			self.__doc__ = self.__name__ + str(self.__signature__)

	def __call__(self, instance, call_done_cb, call_error_cb, user_data, *args, **kwargs):
		argdiff = len(args) - len(self._inargs)
		if argdiff != 0:
			dbg_args = {
				"instance": instance,
				"call_done_cb": call_done_cb,
				"call_error_cb": call_error_cb,
				"user_data": user_data,
				"args": args,
				"kwargs": kwargs,
			}
		if argdiff < 0:
			raise TypeError(self.__qualname__ + " missing {} required positional argument(s), expected: {}, given: {}".format(-argdiff, len(self._inargs), dbg_args))

		elif argdiff > 0:
			raise TypeError(self.__qualname__ + " takes {} positional argument(s) but {} was/were given: {}".format(len(self._inargs), len(args), dbg_args))

		timeout = kwargs.get("timeout", None)

		def done_cb(obj, res, data):
			try:
				ret = obj.call_finish(res)
				if call_done_cb:
					call_done_cb(instance, ret, data)
			except Exception as e:
				if call_error_cb:
					call_error_cb(instance, e, data)

		ret = instance._bus.con.call(
			instance._bus_name, instance._path,
			self._iface_name, self.__name__[0:-len('Async')], Variant(self._sinargs, args), VariantType.new(self._soutargs),
			0, timeout_to_glib(timeout), None, done_cb, user_data)

		return ret

	def __get__(self, instance, owner):
		if instance is None:
			return self

		return MethodType(self, instance)

	def __repr__(self):
		return "<function " + self.__qualname__ + " at 0x" + format(id(self), "x") + ">"


def InterfaceBackfilled(obj, iface):

	if_name = iface.attrib["name"]
	for member in iface:
		matching_bases = [base for base in type(obj).__bases__ if base.__name__ == if_name]

		if len(matching_bases) == 0:
			raise KeyError(iface)
		assert(len(matching_bases) == 1)
		iface_class = matching_bases[0]

		member_name = member.attrib["name"]
		if member.tag == "method":
			method = getattr(iface_class, member_name, None)
			if method:
				setattr(iface_class, member_name + 'Async', ProxyMethodAsync(if_name, method))

	return obj


def backfill_async_dbus_methods(obj, introspection):

	ifaces = sorted([x for x in introspection if x.tag == "interface"],
					key=lambda x: int(x.attrib["name"].startswith("org.freedesktop.DBus.")))

	for iface in ifaces:
		InterfaceBackfilled(obj, iface)

