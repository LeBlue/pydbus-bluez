from struct import Struct
from types import new_class

# class init => python type to obj, value = python type
# obj encode: obj to bytes/array
# classmethod decode: bytes array (array('B', [0, 2, 255, ..])) to python type
# str obj to str, mostly str(value)
# self.value is bytes on Base class


class MetaBluezFormat(type):
    def __str__(self):
        return "{}".format(self.__name__)


class MetaBluezFormatInt(type):
    def __str__(self):
        return "{}(len={},exponent={})".format(self.__name__, self.len, self.exponent)


class FormatBase(object, metaclass=MetaBluezFormat):

    # __metaclass__ = MetaFormatInt
    # 0 means variable length
    len = 0

    # for all numeric
    exponent = 0

    native_types = bytes

    # init takes native python type as arg (depends on formatBase, base is 'bytes' type)
    def __init__(self, value):
        if not isinstance(value, self.native_types):
            raise TypeError(
                "{}, wrong type: {}, expected: {}".format(
                    self.__class__.__name__, type(value), self.native_types
                )
            )

        self.value = value
        try:
            _ = self.encode()
        except Exception as ex:
            # keep exception raised by 'encode', but add this one
            raise ValueError(f"{self.__class__.__name__}: {str(ex)}")

    @classmethod
    def decode(cls, value):
        return cls(bytes(value))

    def encode(self):
        return self.value

    def __str__(self):
        return str(self.value)

    def __eq__(self, other):
        if isinstance(other, FormatBase):
            return self.value == other.value
        return self.value == other


# alias
class FormatRaw(FormatBase):
    pass


# base only for non-power two uints
class FormatUint(FormatBase):

    exponent = 0
    len = 1

    native_types = (int, float)

    @classmethod
    def decode(cls, value):
        acc = 0
        for idx, v in enumerate(value):
            if idx == cls.len:
                break
            acc += int(v) * pow(2, 8 * idx)

        if cls.exponent:
            n = float(acc) * pow(10, cls.exponent)
            if cls.exponent:
                n = round(n, cls.exponent * -1)
            return cls(n)
        return cls(acc)

    def encode(self):
        if self.exponent:
            v = int(self.value / pow(10, self.exponent))
        else:
            v = self.value
        b = []
        for idx in range(0, self.len):
            b.append(v % 256)
            v = int(v / 256)
        return bytes(b)


class FormatUint24(FormatUint):
    len = 3


class FormatUint40(FormatUint):
    len = 5


class FormatUint48(FormatUint):
    len = 6


_endian = "="
# works only as base for powers of 2 sints
class FormatPacked(FormatBase):

    exponent = 0
    len = 1

    # adds float for native type (self.value), but pack/unpack always the/to int
    native_types = (int, float)

    pck_fmt = Struct(_endian + "B")

    @classmethod
    def decode(cls, value):
        v = bytes(value)
        if len(v) < cls.len:
            v = bytes(value) + bytes([0] * (cls.len - len(v)))

        # acc = unpack(cls.endian + cls.pck_fmt, v)
        acc = cls.pck_fmt.unpack(v)
        if cls.exponent:
            return cls(round(float(acc[0]) * pow(10, cls.exponent), cls.exponent * -1))
        return cls(acc[0])

    def encode(self):
        if self.exponent:
            v = int(self.value / pow(10, self.exponent))
        else:
            v = int(self.value)

        return self.pck_fmt.pack(v)

    def __int__(self):
        return int(self.value)

    def __float__(self):
        return float(self.value)


class FormatUint8(FormatPacked):
    pck_fmt = Struct(_endian + "B")


class FormatUint8Enum(FormatUint8):
    pass


class FormatUint16(FormatPacked):
    len = 2
    pck_fmt = Struct(_endian + "H")


class FormatUint32(FormatPacked):
    len = 4
    pck_fmt = Struct(_endian + "I")


class FormatUint64(FormatPacked):
    len = 8
    pck_fmt = Struct(_endian + "Q")


class FormatSint8(FormatPacked):
    pck_fmt = Struct(_endian + "b")


class FormatSint16(FormatPacked):
    len = 2
    pck_fmt = Struct(_endian + "h")


class FormatSint32(FormatPacked):
    len = 4
    pck_fmt = Struct(_endian + "i")


class FormatSint64(FormatPacked):
    len = 2
    pck_fmt = Struct(_endian + "q")


class FormatFloat32(FormatPacked):
    len = 4
    pck_fmt = Struct(_endian + "f")


class FormatFloat64(FormatPacked):
    len = 8
    pck_fmt = Struct(_endian + "d")


class FormatUtf8s(FormatBase):

    # native 'value' format is unicode string
    native_types = str

    @classmethod
    def decode(cls, value):
        s = bytes(value).decode("utf-8")
        l = len(s)
        # remove trailing NUL
        if l > 0 and s[l - 1] == "\x00":
            s = s[:-1]
        return cls(s)

    def encode(self):
        return self.value.encode("utf-8")


class FormatBitfield(FormatUint8):
    len = 1
    native_types = (int, )

    def __str__(self):
        return "0b{:08b}".format(self.value)


class FormatBitfield16(FormatUint16):
    len = 2

    def __str__(self):
        return "0b{:016b}".format(self.value)


class FormatTuple(FormatBase):

    sub_cls = []
    sub_cls_names = []

    native_types = (list, tuple)
    # here we have a list/tuple as value
    def __init__(self, value):
        try:
            if len(self.sub_cls) != len(value):
                raise ValueError(
                    "Expected {} number of values for format: {} ({}}".format(
                        len(self.sub_cls), self.__class__.__name__, self._sub_str()
                    )
                )
        except TypeError:
            raise TypeError(
                "Expected iterable with {} number of values for format: {} ({})".format(
                    len(self.sub_cls), self.__class__.__name__, self._sub_str()
                )
            ) from None
        self.value = value

    def _sub_str(self):

        scn = self.sub_cls_names if self._is_named() else None

        if scn and len(scn) == len(self):
            d = {}
            for idx, n in enumerate(scn):
                d[n] = self.sub_cls[idx]
            return str(d)
        return "({})".format(",".join([sub_c.__name__ for sub_c in self.sub_cls]))

    def _is_named(self):
        try:
            _ = self.sub_cls_names
        except AttributeError:
            return False
        return bool(self.sub_cls_names)

    # del not suported, wonder if wee need it
    #    def __delitem__(self, key):
    #       self.__delattr__(key)

    def __len__(self):
        return len(self.sub_cls)

    def __getitem__(self, key):
        if isinstance(key, int):
            return self.value[key]
        elif isinstance(key, str):
            if not self._is_named():
                raise TypeError("index must be int")
            try:
                i = self.sub_cls_names.index(key)
            except ValueError:
                raise KeyError(key)
            return self.value[i]
        raise TypeError("index must be str or int")

    def __setitem__(self, key, sub_value):
        if isinstance(key, int):
            self.value[key] = sub_value
        elif isinstance(key, str):
            if not self._is_named():
                raise TypeError("index must be int")
            try:
                i = scn.index(key)
            except ValueError:
                raise KeyError(key)
            self.value[i] = sub_value

        raise TypeError("index must be str or int")

    def keys(self):
        if not self._is_named():
            return []
        return self.sub_cls_names

    def values(self):
        return self.value

    def items(self):
        if not self._is_named():
            return []

        return [
            (self.sub_cls_names[idx], value) for idx, value in enumerate(self.value)
        ]

    @classmethod
    def decode(cls, value):
        dec_vals = []
        for sub in cls.sub_cls:
            # consume bytes suitable for class, or all
            len_get = len(value) if sub.len == 0 else sub.len

            v = value[:len_get]
            value = value[len_get:]
            dec_vals.append(sub.decode(v))

        return cls(cls.native_types[0](dec_vals))

    def encode(self):
        enc_vals = b""
        for idx, val in enumerate(self.value):
            # add bytes for all classes in order, or all
            if isinstance(val, FormatBase):
                enc_vals += val.encode()
            else:
                enc_vals += self.sub_cls[idx](val).encode()

        return enc_vals

    def __str__(self):
        return "(" + ",".join([str(v) for v in self.value]) + ")"

    def __eq__(self, other):
        if isinstance(other, FormatTuple):
            if len(other) != len(self):
                return False
            for idx, value in enumerate(self.values()):
                if value != other[idx]:
                    return False

            return True
        elif not isinstance(other, FormatBase):
            for idx, value in enumerate(self.values()):
                if value != other[idx]:
                    return False

            return True
        return False


__all__ = (
    "FormatBase",
    "FormatRaw",
    "FormatUint",
    "FormatUint8",
    "FormatUint8Enum",
    "FormatUint16",
    "FormatUint24",
    "FormatUint32",
    "FormatUint40",
    "FormatUint48",
    "FormatUint64",
    "FormatSint8",
    "FormatSint16",
    "FormatSint32",
    "FormatSint64",
    "FormatUtf8s",
    "FormatBitfield",
    "FormatTuple",
)
