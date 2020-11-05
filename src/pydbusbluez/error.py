from functools import wraps, partial

from gi.repository.GLib import Error as GLibError
from gi.repository import GLib


import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.ERROR)


class BluezError(Exception):
    def __str__(self):
        return "{}: {}".format(
            self.__class__.__name__, self.args[0] if len(self.args) > 0 else ""
        )


class BluezAlreadyExistsError(BluezError):
    pass


class BluezUnknownError(BluezError):
    pass


class BluezInProgressError(BluezError):
    pass


class BluezFailedError(BluezError):
    pass


class BluezNotReadyError(BluezError):
    pass


class BluezAlreadyConnectedError(BluezError):
    pass


class BluezInvalidArgumentsError(BluezError):
    pass


class BluezNotAvailableError(BluezError):
    pass


class BluezNotSupportedError(BluezError):
    pass


class BluezAuthenticationCanceledError(BluezError):
    pass


class BluezAuthenticationFailedError(BluezError):
    pass


class BluezAuthenticationRejectedError(BluezError):
    pass


class BluezAuthenticationTimeoutError(BluezError):
    pass


class BluezConnectionAttemptFailedError(BluezError):
    pass


class BluezDoesNotExistError(BluezError):
    pass


class BluezNotConnectedError(BluezError):
    pass


class BluezNotPermittedError(BluezError):
    pass


class BluezFormatError(BluezError):
    pass


class BluezFormatEncodeError(BluezFormatError):
    pass


class BluezFormatDecodeError(BluezFormatError):
    pass


class DBusError(BluezError):
    pass


class DBusInvalidArgsError(DBusError):
    pass


class DBusUnknownObjectError(DBusError):
    pass


class DBusTimeoutError(DBusError):
    pass


# Todo
"""
NotReady
AlreadyConnected
InvalidArguments
NotAvailable
NotSupported
AuthenticationCanceled
AuthenticationFailed
AuthenticationRejected
AuthenticationTimeout
ConnectionAttemptFailed (from pairs)
DoesNotExist

"""


def convertBluezError(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        return callBluezFunction(func, *args, **kwargs)

    return wrapper


def callBluezFunction(func, *args, **kwargs):
    try:
        logger.debug(
            "Calling: %s %s(%s,%s)", func, func.__name__, str(args), str(kwargs)
        )
        return func(*args, **kwargs)
    except (BluezError, DBusError) as e:
        raise e from None
    except Exception as e:
        getDBusError(e)


# This does not work. Only if using this here directly in the @property function, where prop = (self.)_proxy.prop
def getBluezPropOrNone(proxy, prop, fail_ret=None):
    try:
        # first, convert error to own classes
        try:
            return getattr(proxy, prop, fail_ret)
        except (BluezError, DBusError):
            raise
        except Exception as e:
            getDBusError(e)
    # if not exists, return just None/fail_ret
    except (BluezDoesNotExistError, DBusUnknownObjectError):
        pass

    return fail_ret


def getBluezPropOrRaise(proxy, prop):
    # first, convert error to own classes
    try:
        attr = getattr(proxy, prop, None)
    except (BluezError, DBusError):
        raise
    except Exception as e:
        getDBusError(e)
    if attr == None:
        raise BluezDoesNotExistError("property not found: " + prop)
    return attr


def getDBusError(err):
    logger.debug("ErrorDebug: %s", str(err))
    if not isinstance(err, BaseException):
        raise TypeError("Need a BaseException subclass, got: {}".format(str(err)))

    if not isinstance(err, Exception):
        raise err from None

    if isinstance(err, KeyError):
        if not err.args or len(err.args) == 0:
            raise err from None

        # These are errors generated from pydbus, translate them to 'BluezErrors'
        if err.args[0].startswith("no such object") or err.args[0].startswith(
            "object does not export any interfaces"
        ):
            raise BluezDoesNotExistError(err.args[0])

    # GLib.Error: g-io-error-quark: Timeout was reached
    logger.debug("%s, %s", type(err), str(err))

    if (
        isinstance(err, GLib.Error)
        and err.args
        and len(err.args) > 0
        and err.args[0] == "Timeout was reached"
    ):
        raise DBusTimeoutError(err.message)

    if not isinstance(err, GLibError) or not err.message:
        raise err

    ml = err.message.split(":")
    if not ml or not ml[0].endswith("GDBus.Error"):
        # raise err
        raise err from None

    # what is this
    logger.debug("%s", str(ml))

    if len(ml) < 2:
        raise DBusError(":".join(ml[1:]))

    msg = ml[2].strip() if len(ml) > 2 else ""
    msg += " ({})".format(err.code) if err.code else ""

    if ml[1].startswith("org.freedesktop.DBus.Error"):
        if ml[1].endswith(".InvalidArgs"):
            logger.debug('"{}"'.format(ml[2]))

            if ml[2].strip().startswith("No such property"):
                raise BluezDoesNotExistError(msg)
            raise DBusInvalidArgsError(msg)
        if ml[1].endswith(".UnknownObject"):
            raise DBusUnknownObjectError(msg)

    if not ml[1].startswith("org.bluez.Error"):
        raise DBusError(":".join(ml[1:]))

    msg = ml[2].strip() if len(ml) > 2 else ""
    msg += " ({})".format(err.code) if err.code else ""

    if ml[1].endswith(".AlreadyExists"):
        raise BluezAlreadyExistsError(msg)
    if ml[1].endswith(".UnknownError"):
        raise BluezUnknownError(msg)
    if ml[1].endswith(".InProgress"):
        raise BluezInProgressError(msg)
    if ml[1].endswith(".Failed"):
        raise BluezFailedError(msg)
    if ml[1].endswith(".NotReady"):
        raise BluezNotReadyError(msg)
    if ml[1].endswith(".AlreadyConnected"):
        raise BluezAlreadyConnectedError(msg)
    if ml[1].endswith(".InvalidArguments"):
        raise BluezInvalidArgumentsError(msg)
    if ml[1].endswith(".NotAvailable"):
        raise BluezNotAvailableError(msg)
    if ml[1].endswith(".NotSupported"):
        raise BluezNotSupportedError(msg)
    if ml[1].endswith(".AuthenticationCanceled"):
        raise BluezAuthenticationCanceledError(msg)
    if ml[1].endswith(".AuthenticationFailed"):
        raise BluezAuthenticationFailedError(msg)
    if ml[1].endswith(".AuthenticationRejected"):
        raise BluezAuthenticationRejectedError(msg)
    if ml[1].endswith(".AuthenticationTimeout"):
        raise BluezAuthenticationTimeoutError(msg)
    if ml[1].endswith(".ConnectionAttemptFailed"):
        raise BluezConnectionAttemptFailedError(msg)
    if ml[1].endswith(".DoesNotExist"):
        raise BluezDoesNotExistError(msg)
    if ml[1].endswith(".NotConnected"):
        raise BluezNotConnectedError(msg)
    if ml[1].endswith(".NotPermitted"):
        raise BluezNotPermittedError(msg)

    raise BluezError(msg)


__all__ = (
    "DBusError",
    "DBusInvalidArgsError",
    "DBusUnknownObjectError",
    "DBusTimeoutError",
    "BluezError",
    "BluezAlreadyExistsError",
    "BluezUnknownError",
    "BluezInProgressError",
    "BluezFailedError",
    "BluezNotReadyError",
    "BluezAlreadyConnectedError",
    "BluezInvalidArgumentsError",
    "BluezNotAvailableError",
    "BluezNotSupportedError",
    "BluezAuthenticationCanceledError",
    "BluezAuthenticationFailedError",
    "BluezAuthenticationRejectedError",
    "BluezAuthenticationTimeoutError",
    "BluezConnectionAttemptFailedError",
    "BluezDoesNotExistError",
    "BluezNotConnectedError",
    "BluezNotPermittedError",
    "BluezFormatDecodeError",
    "callBluezFunction",
    "convertBluezError",
    "getBluezPropOrNone",
)
