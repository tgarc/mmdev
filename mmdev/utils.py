import StringIO
import os
import ctypes

_bruijn32lookup = [0, 1, 28, 2, 29, 14, 24, 3, 30, 22, 20, 15, 25, 17, 4, 8,
                    31, 27, 13, 23, 21, 19, 16, 7, 26, 12, 18, 6, 11, 5, 10, 9]


def get_mask_offset(mask):
    cmask = ctypes.c_uint32(mask).value
    # calculate the bit offset from the mask using a debruijn hash function
    # use ctypes to truncate the result to a uint32
    # TODO: change to a 64 bit version of the lookup
    return _bruijn32lookup[ctypes.c_uint32((mask & -mask) * 0x077cb531).value >> 27]


def from_devfile(devfile, file_format=None, raiseErr=True, **kwargs):
    """
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


class HexValue(int):
    def __new__(cls, x, bitwidth=0, base=None):
        if base is None:
            newint = int.__new__(cls, x)
        else:
            newint = int.__new__(cls, x, base=base)
        if bitwidth == 0:
            bitwidth = newint.bit_length()
        div, mod = divmod(bitwidth, 4)
        newint._fmt = ("{:#0%dx}" % (div + bool(mod) + 2)).format
        newint._width = bitwidth
        newint._mask = (1 << bitwidth) - 1
        return newint

    def __invert__(self):
        return HexValue(int.__invert__(self), self._width)

    def __lshift__(self, other):
        return HexValue(int.__lshift__(self, int(other)), self._width)
    def __rshift__(self, other):
        return HexValue(int.__rshift__(self, int(other)), self._width)
    def __and__(self, other):
        return HexValue(int.__and__(self, int(other)), self._width)
    def __xor__(self, other):
        return HexValue(int.__xor__(self, int(other)), self._width)
    def __or__(self, other):
        return HexValue(int.__or__(self, int(other)), self._width)

    def __repr__(self):
        return self._fmt(self if self >= 0 else self&self._mask)
    def __str__(self):
        return self._fmt(self if self >= 0 else self&self._mask)


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

