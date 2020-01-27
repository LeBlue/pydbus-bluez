from prautils.format import *
from array import array

def test_uints():

    tt = [
        {
            'cls': FormatUint8,
            'vals': [
                (0, b'\x00', '0'),
                (255, b'\xff', '255'),
            ]
        },
        {
            'cls': FormatUint16,
            'vals': [
                (0, b'\x00\x00', '0'),
                (255, b'\xff\x00', '255'),
                (65535, b'\xff\xff', '65535'),
            ]
        },
        {
            'cls': FormatUint24,
            'vals': [
                (0, b'\x00\x00\x00', '0'),
                (255, b'\xff\x00\x00', '255'),
                (16777215, b'\xff\xff\xff', '16777215'),
            ]
        },
                {
            'cls': FormatUint32,
            'vals': [
                (0, b'\x00\x00\x00\x00', '0'),
                (255, b'\xff\x00\x00\x00', '255'),
                (4294967295, b'\xff\xff\xff\xff', '4294967295'),
            ]
        },
        {
            'cls': FormatUint64,
            'vals': [
                (0, b'\x00\x00\x00\x00\x00\x00\x00\x00', '0'),
                (255, b'\xff\x00\x00\x00\x00\x00\x00\x00', '255'),
                (18446744073709551615, b'\xff\xff\xff\xff\xff\xff\xff\xff',
                 '18446744073709551615'),
            ]
        },
        {
            'cls': FormatSint8,
            'vals': [
                (0, b'\x00', '0'),
                (127, b'\x7f', '127'),
                (-128, b'\x80', '-128'),
                (-1, b'\xff', '-1'),
            ]
        },
        {
            'cls': FormatSint16,
            'vals': [
                (0, b'\x00\x00', '0'),
                (255, b'\xff\x00', '255'),
                (32767, b'\xff\x7f', '32767'),
                (-32768, b'\00\x80', '-32768'),
                (-1, b'\xff\xff', '-1'),
            ]
        },
        {
            'cls': FormatSint32,
            'vals': [
                (0, b'\x00\x00\x00\x00', '0'),
                (255, b'\xff\x00\x00\x00', '255'),
                (32767, b'\xff\x7f\x00\x00', '32767'),
                (-32768, b'\00\x80\xff\xff', '-32768'),
                (65535, b'\xff\xff\x00\x00', '65535'),
                (2147483647, b'\xff\xff\xff\x7f', '2147483647'),
                (-2147483648, b'\00\00\00\x80', '-2147483648'),
                (-1, b'\xff\xff\xff\xff', '-1'),
            ]
        },
        {
            'cls': FormatSint64,
            'vals': [
                (0, b'\x00\x00\x00\x00\x00\x00\x00\x00', '0'),
                (255, b'\xff\x00\x00\x00\x00\x00\x00\x00', '255'),
                (32767, b'\xff\x7f\x00\x00\x00\x00\x00\x00', '32767'),
                (-32768, b'\00\x80\xff\xff\xff\xff\xff\xff', '-32768'),
                (-32767, b'\01\x80\xff\xff\xff\xff\xff\xff', '-32767'),
                (65535, b'\xff\xff\x00\x00\x00\x00\x00\x00', '65535'),
                (2147483647, b'\xff\xff\xff\x7f\x00\x00\x00\x00', '2147483647'),
                (-2147483648, b'\00\00\00\x80\xff\xff\xff\xff', '-2147483648'),
                (-2147483647, b'\01\00\00\x80\xff\xff\xff\xff', '-2147483647'),
                (9223372036854775807, b'\xff\xff\xff\xff\xff\xff\xff\x7f',
                 '9223372036854775807'),
                (-9223372036854775808, b'\x00\x00\x00\x00\00\00\00\x80',
                 '-9223372036854775808'),
                (-1, b'\xff\xff\xff\xff\xff\xff\xff\xff', '-1'),
            ]
        },
    ]

    for t_format in tt:
        print('')
        t_cls = t_format['cls']
        print(t_cls.__name__)

        for val in t_format['vals']:
            print('Testing:', val)
            n0 = t_cls(val[0])
            assert n0.encode() == val[1], 'assert {} == {}'.format(n0.encode(),val[1])
            assert str(n0) == val[2], 'assert {} == {}'.format(str(n0), val[2])
            assert n0.value == val[0], 'assert {} == {}'.format(n0.value, val[0])
            print('obj:     ', n0.__repr__())
            print('obj.val: ', str(n0.value))
            print('str(obj):', str(n0))
            n1 = t_cls.decode(array('B', val[1]))
            # n1 = t_cls.decode(val[1])
            assert n1.value == val[0], 'assert {} == {}'.format(n1.value, val[0])

            assert str(n1) == str(n0), 'assert {} == {}'.format(str(n1), str(n0))
            assert str(n1) == val[2], 'assert {} == {}'.format(str(n1), val[2])
            # print('obj:     ', n.__repr__())
            # print('obj.val: ', str(n.value))
            # print('str(obj):', str(n))

            # n_enc = n.encode()
            # print('enc str: ', str(n_enc))
        print('')


    # just for testing
if __name__ == "__main__":


    test_uints()



    # print('FormatBitField:')
    # n = FormatBitField(7)

    # print('obj:     ', n.__repr__())
    # print('obj.val: ', str(n.value))
    # print('str(obj):', str(n))

    # n_enc = n.encode()
    # print('enc str: ', str(n_enc))

    # n_dec = FormatBitField.decode(array('B', [0xf]))
    # print('dec str: ', str(n_dec))

    # print('')

    # print('FormatASCII:')
    # n = FormatASCII('123456')

    # print('obj:     ', n.__repr__())
    # print('obj.val: ', str(n.value))
    # print('str(obj):', str(n))

    # n_enc = n.encode()
    # print('enc str: ', str(n_enc))

    # n_dec = FormatASCII.decode(array('B', [0x31, 0x32, 0x33,0x34, 0x35, 0x36]))
    # print('dec str: ', str(n_dec))

    # print('')

    # print('FormatUtf8s:')
    # n = FormatUtf8s('123456')

    # print('obj:     ', n.__repr__())
    # print('obj.val: ', str(n.value))
    # print('str(obj):', str(n))

    # n_enc = n.encode()
    # print('enc str: ', str(n_enc))

    # n_dec = FormatUtf8s.decode(
    #     array('B', [0x31, 0x32, 0x33, 0x34, 0x35, 0x36]))
    # print('dec str: ', str(n_dec))

    # print('')
