from struct import Struct

# class init => python type to obj, value = python type
# obj encode: obj to bytes/array
# classmethod decode: bytes array (array('B', [0, 2, 255, ..])) to python type
# str obj to str, mostly str(value)
# self.value is bytes on Base class


class FormatBase(object):

    # 0 means variable length
    len = 0

    # for all numeric
    exponent = 0

    native_types = bytes

    # init takes native python type as arg (depends on formatBase, base is 'bytes' type)
    def __init__(self, value):
        if not isinstance(value, self.native_types):
            raise TypeError('{}, wrong type: {}, expected: {}'.format(self.__class__.__name__, type(value), self.native_types))

        self.value = value
        try:
            _ =  self.encode()
        except Exception:
            # keep exception raised by 'encode', but add this one
            raise TypeError('{}, wrong type: {}, expected: {}'.format(
                self.__class__.__name__, type(value), self.native_types))


    @classmethod
    def decode(cls, value):
        return cls(bytes(value))

    def encode(self):
        return self.value

    def __str__(self):
        return str(self.value)

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
            acc += int(v) * pow(2, 8*idx)

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
            v = int(v/256)
        return bytes(b)


class FormatUint24(FormatUint):
    len = 3

class FormatUint40(FormatUint):
    len = 5

class FormatUint48(FormatUint):
    len = 6

_endian = '='
# works only as base for powers of 2 sints
class FormatPacked(FormatBase):

    exponent = 0
    len = 1

    # adds float for native type (self.value), but pack/unpack always the/to int
    native_types = (int, float)

    pck_fmt = Struct(_endian + 'B')

    @classmethod
    def decode(cls, value):
        v = bytes(value)
        if len(v) < cls.len:
            v = bytes(value) + bytes([0] * (cls.len - len(v)))


        # acc = unpack(cls.endian + cls.pck_fmt, v)
        acc = cls.pck_fmt.unpack(v)
        #print(acc)
        if cls.exponent:
            return cls(round(float(acc[0]) * pow(10, cls.exponent), cls.exponent * -1))
        return cls(acc[0])


    def encode(self):
        if self.exponent:
            v = int(self.value / pow(10, self.exponent))
        else:
            v = int(self.value)
        #print(v)
        return self.pck_fmt.pack(v)

    # def __str__(self):
    #     return str(self.value)



class FormatUint8(FormatPacked):
    pck_fmt = Struct(_endian + 'B')

class FormatUint8Enum(FormatUint8):
    pass

class FormatUint16(FormatPacked):
    len = 2
    pck_fmt = Struct(_endian + 'H')

class FormatUint32(FormatPacked):
    len = 4
    pck_fmt = Struct(_endian + 'I')

class FormatUint64(FormatPacked):
    len = 8
    pck_fmt = Struct(_endian + 'Q')

class FormatSint8(FormatPacked):
    pck_fmt = Struct(_endian + 'b')

class FormatSint16(FormatPacked):
    len = 2
    pck_fmt = Struct(_endian + 'h')

class FormatSint32(FormatPacked):
    len = 4
    pck_fmt = Struct(_endian + 'i')

class FormatSint64(FormatPacked):
    len = 2
    pck_fmt = Struct(_endian + 'q')

class FormatFloat32(FormatPacked):
    len = 4
    pck_fmt = Struct(_endian + 'f')

class FormatFloat64(FormatPacked):
    len = 8
    pck_fmt = Struct(_endian + 'd')


class FormatUtf8s(FormatBase):

    #native 'value' format is unicode string
    native_types = str

    @classmethod
    def decode(cls, value):
        s = bytes(value).decode('utf-8')
        l = len(s)
        # remove trailing NUL
        if l > 0 and s[l-1] == '\x00':
            s = s[:-1]
        return cls(s)

    def encode(self):
        return self.value.encode('utf-8')

class FormatBitfield(FormatUint8):
    len = 1
    #native 'value' format is bytes

    def __str__(self):
        return '0b{:08b}'.format(self.value)



class FormatTuple(FormatBase):

    sub_cls = []
    native_types = (tuple, list)
    # here we have a list as value
    def __init__(self, value):
        try:
            if len(self.sub_cls) != len(value):
                raise ValueError(
                    'Expected {} number of values for format: {} ({}}'.format(len(self.sub_cls), self.__class__.__name__, self._sub_str()))
        except TypeError:
            raise TypeError(
                'Expected list with {} number of values for format: {} ({})'.format(len(self.sub_cls), self.__class__.__name__, self._sub_str())) from None
        self.value = value

    def _sub_str(self):
        scn = None
        try:
            scn = self.sub_cls_names
        except AttributeError:
            pass

        if scn and len(scn) == len(self):
            d = {}
            for idx, n in enumerate(scn):
                d[n] = self.sub_cls[idx]
            return str(d)
        return '({})'.format(','.join([ sub_c.__name__ for sub_c in self.sub_cls]))

# del not suported, wonder if wee need it
#    def __delitem__(self, key):
#       self.__delattr__(key)

    def __len__(self):
        return len(self.sub_cls)

    def __getitem__(self, key):
        return self.value[key]

    def __setitem__(self, key, sub_value):
        self.value[key] = sub_value

    # @property
    # def value(self):
    #     return self.decode()

    # @value.setter
    # def value(self, value):
    #     self._value = value


    @classmethod
    def decode(cls, value):
        dec_vals = []
        for sub in cls.sub_cls:
            # consume bytes suitable for class, or all
            len_get = len(value) if sub.len == 0 else sub.len

            v = value[:len_get]
            value = value[len_get:]
            dec_vals.append(sub.decode(v))

        return cls(dec_vals)

    def encode(self):
        enc_vals = b''
        for idx, val in enumerate(self.value):
            # add bytes for all classes in order, or all
            if isinstance(val, FormatBase):
                enc_vals += val.encode()
            else:
                enc_vals += self.sub_cls[idx](val).encode()

        return enc_vals

    def __str__(self):
        return '(' + ','.join([ str(v) for v in self.value ]) + ')'


__all__ = (
    'FormatBase',
    'FormatRaw',
    'FormatUint',
    'FormatUint8',
    'FormatUint8Enum',
    'FormatUint16',
    'FormatUint24',
    'FormatUint32',
    'FormatUint40',
    'FormatUint48',
    'FormatUint64',
    'FormatSint8',
    'FormatSint16',
    'FormatSint32',
    'FormatSint64',
    'FormatUtf8s',
    'FormatBitfield',
    'FormatTuple',
)


