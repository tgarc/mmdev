import StringIO
import os
import ctypes


_bruijn32lookup = [0, 1, 28, 2, 29, 14, 24, 3, 30, 22, 20, 15, 25, 17, 4, 8,
                    31, 27, 13, 23, 21, 19, 16, 7, 26, 12, 18, 6, 11, 5, 10, 9]


#TODO: change to a 64 bit version of the lookup
def get_mask_offset(mask):
    """\
    Calculate the offset of the first non-zero bit of a number using a debruijn
    hash function.
    """
    # use ctypes to truncate the result to a uint32
    cmask = ctypes.c_uint32(mask).value
    return _bruijn32lookup[ctypes.c_uint32((mask & -mask) * 0x077cb531).value >> 27]


def from_devfile(devfile, file_format=None, raiseErr=True, **kwargs):
    """\
    Parse a device file using the given file format. If file format is not
    given, file extension will be used.

    Supported Formats:
        + 'json' : JSON
        + 'svd'  : CMSIS-SVD
    """
    from mmdev import parsers
    if file_format is None:
        file_format = os.path.splitext(devfile)[1][1:]
    try:
        parsercls = parsers.PARSERS[file_format]
    except KeyError:
        raise KeyError("File extension '%s' not recognized" % file_format)

    return parsercls(devfile, raiseErr=raiseErr, **kwargs)

class _IntValue(int):
    def __new__(cls, x=0, bitwidth=None, base=None):
        if base is None:
            newint = int.__new__(cls, x)
        else:
            newint = int.__new__(cls, x, base=base)

        if isinstance(x, cls) and bitwidth is None:
            newint.width = x.width
        elif bitwidth is not None:
            newint.width = bitwidth
        else:
            newint.width = x.bit_length()

        newint.fmt = "{:0%dd}" % newint.width
        newint._mask = (1 << newint.width) - 1

        return newint

    def __invert__(self):
        return self.__class__(int.__invert__(self), self.width)

    def __lshift__(self, other):
        return self.__class__( int.__lshift__(self, int(other)), self.width)
    def __rshift__(self, other):
        return self.__class__( int.__rshift__(self, int(other)), self.width)
    def __and__(self, other):
        return self.__class__( int.__and__(self, int(other)), self.width)
    def __xor__(self, other):
        return self.__class__( int.__xor__(self, int(other)), self.width)
    def __or__(self, other):
        return self.__class__( int.__or__(self, int(other)), self.width)
    def __add__(self, other):
        return self.__class__( int.__add__(self, int(other)), self.width)
    def __sub__(self, other):
        return self.__class__( int.__sub__(self, int(other)), self.width)
    def __mod__(self, other):
        return self.__class__( int.__mod__(self, int(other)), self.width)
    def __mul__(self, other):
        return self.__class__( int.__mul__(self, int(other)), self.width)
    def __div__(self, other):
        return self.__class__( int.__div__(self, int(other)), self.width)
    def __floordiv__(self, other):
        return self.__class__( int.__floordiv__(self, int(other)), self.width)

    def __rlshift__(self, other):
        return self.__class__( int.__lshift__(self, int(other)), self.width)
    def __rrshift__(self, other):
        return self.__class__( int.__rshift__(self, int(other)), self.width)
    def __rand__(self, other):
        return self.__class__( int.__and__(self, int(other)), self.width)
    def __rxor__(self, other):
        return self.__class__( int.__xor__(self, int(other)), self.width)
    def __ror__(self, other):
        return self.__class__( int.__or__(self, int(other)), self.width)
    def __radd__(self, other):
        return self.__class__( int.__add__(self, int(other)), self.width)
    def __rsub__(self, other):
        return self.__class__( int.__sub__(self, int(other)), self.width)
    def __rmod__(self, other):
        return self.__class__( int.__mod__(self, int(other)), self.width)
    def __rmul__(self, other):
        return self.__class__( int.__mul__(self, int(other)), self.width)
    def __rdiv__(self, other):
        return self.__class__( int.__div__(self, int(other)), self.width)
    def __rfloordiv__(self, other):
        return self.__class__( int.__floordiv__(self, int(other)), self.width)

    def __repr__(self):
        return self.fmt.format(self)
    def __str__(self):
        return self.fmt.format(self)


class BinValue(_IntValue):
    def __new__(cls, x=0, bitwidth=None, base=None):
        newint = super(BinValue, cls).__new__(cls, x=x, bitwidth=bitwidth, base=base)

        newint.fmt = "0b{:0%db}" % newint.width
        newint._mask = (1 << newint.width) - 1

        return newint


class HexValue(_IntValue):
    def __new__(cls, x=0, bitwidth=None, base=None, fmt=None):
        newint = super(HexValue, cls).__new__(cls, x=x, bitwidth=bitwidth, base=base)

        if isinstance(x, cls) and fmt is None:
            fmt = x.fmt[-2]
        elif fmt is None:
            fmt = 'x'
        else:
            assert fmt == 'x' or fmt == 'X'

        div, mod = divmod(newint.width, 4)
        newint.fmt = "0x{:0%d%s}" % (div + bool(mod), fmt)
        newint._mask = (1 << newint.width) - 1

        return newint


def to_gdbinit(dev):
    fh = StringIO.StringIO()
    blkfmt = "set $%s = (unsigned long *) 0x%08x"
    bitfmt = "set $%s = (unsigned long) 0x%08x"    
    for blkname, blk in dev.iteritems():
        print >> fh, '#', blkname, blk.attrs['name']
        print >> fh, '#', '='*58
        print >> fh, blkfmt % (blkname.lower(), blk.attrs['address'])
        print >> fh
        for regname, reg in blk.iteritems():
            print >> fh, '#', regname.lower(), reg.attrs['name'].lower()
            print >> fh, '#', '-'*(len(regname)+len(reg.attrs['name'])+1)
            print >> fh, blkfmt % (regname.lower(),reg.attrs['address'])
            for bfname, bits in reg.iteritems():
                print >> fh, bitfmt % (bfname.lower(), bits.attrs['mask'])
            print >> fh
    gdbinit = fh.getvalue()
    fh.close()

    return gdbinit

