"""
Test integer format conversions
"""
import pytest

from pydbusbluez.format import *
from array import array


PARAMETER_VALUES = (
    (FormatUint8, 0, b"\x00"),
    (FormatUint8, 255, b"\xff"),
    (FormatUint16, 0, b"\x00\x00"),
    (FormatUint16, 255, b"\xff\x00"),
    (FormatUint16, 65535, b"\xff\xff"),
    (FormatUint24, 0, b"\x00\x00\x00"),
    (FormatUint24, 255, b"\xff\x00\x00"),
    (FormatUint24, 16777215, b"\xff\xff\xff"),
    (FormatUint32, 0, b"\x00\x00\x00\x00"),
    (FormatUint32, 255, b"\xff\x00\x00\x00"),
    (FormatUint32, 4294967295, b"\xff\xff\xff\xff"),
    (FormatUint64, 0, b"\x00\x00\x00\x00\x00\x00\x00\x00", "0"),
    (FormatUint64, 255, b"\xff\x00\x00\x00\x00\x00\x00\x00", "255"),
    (FormatUint64, 18446744073709551615, b"\xff\xff\xff\xff\xff\xff\xff\xff"),
    (FormatSint8, 0, b"\x00"),
    (FormatSint8, 127, b"\x7f"),
    (FormatSint8, -128, b"\x80"),
    (FormatSint8, -1, b"\xff"),
    (FormatUint16, 0, b"\x00\x00"),
    (FormatUint16, 255, b"\xff\x00"),
    (FormatUint16, 32767, b"\xff\x7f"),
    (FormatUint16, -32768, b"\x00\x80"),
    (FormatUint16, -1, b"\xff\xff"),
    (FormatSint32, 0, b"\x00\x00\x00\x00"),
    (FormatSint32, 255, b"\xff\x00\x00\x00"),
    (FormatSint32, 32767, b"\xff\x7f\x00\x00"),
    (FormatSint32, -32768, b"\x00\x80\xff\xff"),
    (FormatSint32, 65535, b"\xff\xff\x00\x00"),
    (FormatSint32, 2147483647, b"\xff\xff\xff\x7f"),
    (FormatSint32, -2147483648, b"\x00\x00\x00\x80"),
    (FormatSint32, -1, b"\xff\xff\xff\xff"),
    (FormatSint64, 0, b"\x00\x00\x00\x00\x00\x00\x00\x00"),
    (FormatSint64, 255, b"\xff\x00\x00\x00\x00\x00\x00\x00"),
    (FormatSint64, 32767, b"\xff\x7f\x00\x00\x00\x00\x00\x00"),
    (FormatSint64, -32768, b"\00\x80\xff\xff\xff\xff\xff\xff"),
    (FormatSint64, -32767, b"\01\x80\xff\xff\xff\xff\xff\xff"),
    (FormatSint64, 65535, b"\xff\xff\x00\x00\x00\x00\x00\x00"),
    (FormatSint64, 2147483647, b"\xff\xff\xff\x7f\x00\x00\x00\x00"),
    (FormatSint64, -2147483648, b"\00\00\00\x80\xff\xff\xff\xff"),
    (FormatSint64, -2147483647, b"\01\00\00\x80\xff\xff\xff\xff"),
    (FormatSint64, 9223372036854775807, b"\xff\xff\xff\xff\xff\xff\xff\x7f"),
    (FormatSint64, -9223372036854775808, b"\x00\x00\x00\x00\00\00\00\x80"),
    (FormatSint64, -1, b"\xff\xff\xff\xff\xff\xff\xff\xff"),
)


@pytest.mark.parameterize("format_cls,int_val,bytes_val", PARAMETER_VALUES)
def test_encode_ints(format_cls, int_val, bytes_val):
    fmt = format_cls(int_val)
    assert fmt.encode() == bytes_val
    assert str(fmt) == str(int_val)
    assert fmt.value == int_val


@pytest.mark.parameterize("format_cls,int_val,bytes_val", PARAMETER_VALUES)
def test_decode_ints(format_cls, int_val, bytes_val):
    # fmt = format_cls.decode(array("B", bytes_val))
    fmt = format_cls.decode(bytes_val)
    assert fmt.value == int_val
    assert str(fmt) == str(int_val)
