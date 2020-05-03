import pydbusbluez.format as fmt
from types import new_class


class FormatTemperatureCelsius(fmt.FormatSint16):
    exponent = -1
    pass


class FormatBatteryPowerState(fmt.FormatBitfield):
    pass


class FormatBatteryLevelState(fmt.FormatTuple):
    len = 2
    sub_cls = [fmt.FormatUint8, FormatBatteryPowerState]



class FormatCCC(fmt.FormatTuple):
    sub_cls = (fmt.FormatUint8, fmt.FormatUint8)

CCC = {
    'name': 'CCC',
    'uuid': '2902',
    'fmt': FormatCCC
}

class FormatAutoCRF(fmt.FormatBase):

    _keys = {
        1: fmt.FormatUint8,
        2: fmt.FormatUint8,
        3: fmt.FormatUint8,
        4: fmt.FormatUint8,
        12: fmt.FormatSint8,
        14: fmt.FormatSint16,
        25: fmt.FormatUtf8s
    }

    @classmethod
    def fromCRF(cls, char_name_id, crf):
        fmt = crf[0].value
        exp = crf[1].value
        unit = crf[2].value
        ns = crf[3].value
        description = str(crf[4])
        fmt_cls_base = fmt.FormatBase
        if fmt == 0 or fmt >= 27:
            raise ValueError('Reserved "format" value in CRF')
        elif fmt not in cls._keys:
            raise ValueError('unsupported "format" value: {} in CRF'.format(fmt))


        cls_name = 'FormatCRF{}'.format(char_name_id)
        fmt_cls = new_class(cls_name, (cls._keys[fmt], ))
        fmt_cls.exponent = exp
        fmt_cls.__doc__ = 'unit: {} ns: {}, description: {}'.format(unit, ns, description)
        # fmt_cls.__metaclass__ = MetaFormatInt
        return fmt_cls