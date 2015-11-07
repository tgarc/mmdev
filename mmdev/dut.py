import ctypes as _ctypes

class Block(object):
    fmt="{name:s} ({mnemonic:s})"

    def __init__(self, name, addr, fullname='', descr='', fmt=None):
        self.mnemonic = name
        self.addr = addr
        self.name = fullname
        self.descr = descr
        self.fmt = self.__class__.fmt if fmt is None else fmt
        self.type = self.__class__.__name__
        self.fields = ['mnemonic', 'name', 'descr', 'addr', 'type']

    @property
    def fields(self):
        return self._fields.keys()

    @fields.setter
    def fields(self, fields):
        self._fields = {fn: getattr(self, fn) for fn in fields}

    @fields.deleter
    def fields(self):
        del self._fields

    def __repr__(self):
        return "<{:s} \"{:s}\" at 0x{:08X}>".format(self.type, self.mnemonic, self.addr)


class DeviceBlock(Block):
    fmt="{name:s} ({mnemonic:s}, 0x{addr:08X})"
    _subclass = Register

    def __init__(self, name, addr, blocks=[], fullname='', descr='', fmt=None):
        super(DeviceBlock, self).__init__(name, addr, fullname=fullname, descr=descr, fmt=fmt)

        for blk in blocks:
            setattr(self, blk.mnemonic.lower(), blk)

        # sort by address
        self._blocks = sorted(blocks, key=lambda blk: blk.addr, reverse=True)
        self._blocks = tuple(self._blocks)

        self._subclass = getattr(self.__class__, '_subclass', DeviceBlock)
        
    def iterkeys(self):
        return iter(blk.mnemonic for blk in self._blocks)

    def keys(self):
        return list(self.iterkeys())

    def iteritems(self):
        return iter((blk.mnemonic, blk) for blk in self._blocks)

    def items(self):
        return list(self.iteritems())

    def values(self):
        return list(self._blocks)

    def itervalues(self):
        return iter(self._blocks)

    @property
    def tree(self):
        dstr = self.fmt.format(**self._fields) + '\n'
        dstr+= "\n".join(map(repr,self._blocks))
        print dstr

    def __repr__(self):
        dstr = self.fmt.format(**self._fields) + '\n'
        dstr+= "%ss:\n\t" % self._subclass.__name__
        dstr+= "\n\t".join(["0x{addr:08X} {mnemonic:s}".format(**blk._fields) for blk in self._blocks])
        return dstr


class Register(DeviceBlock):
    _subclass = BitField
    def __init__(self, regname, addr, bitfields, fullname='', descr='', fmt=None):
        super(Register, self).__init__(regname, addr, bitfields, fullname=fullname, descr=descr, fmt=fmt)

_bruijn32lookup = [0, 1, 28, 2, 29, 14, 24, 3, 30, 22, 20, 15, 25, 17, 4, 8, 
                   31, 27, 13, 23, 21, 19, 16, 7, 26, 12, 18, 6, 11, 5, 10, 9]
class BitField(Block):
    def __init__(self, bfname, mask, fullname='', descr='', fmt=None):
        # cmask = _ctypes.c_uint32(mask).value
        # offset = _bruijn32lookup[_ctypes.c_uint32((mask & -mask) * 0x077cb531).value >> 27]
        super(BitField, self).__init__(bfname, mask, fullname=fullname, descr=descr, fmt=fmt)
        self.mask = mask
        self.fields += ['mask']


class DUT(DeviceBlock):
    _subclass = DeviceBlock
    """
    Create a DUT device from device definition file.


    DUT definition files are required to have three dict-like objects:

    BLK_MAP, REG_MAP
    ----------------
    Maps a block/register mnemonic to its address for all hardware
    blocks/registers on device

    BIT_MAP
    -------
    Maps a bitfield mnemonic to a bitmask for all registers on device


    Definition files also have some optional fields:
    
    mnemonic
    --------
    Shorthand name for DUT (e.g. armv7m). Defaults to definition file
    name.

    name
    --------
    Full name of DUT. Defaults to "DUT".

    BLK_NAME, REG_NAME, BIT_NAME
    ------------------
    Maps a block/register/bitfield mnemonic to its full name (e.g., ITM :
    Instrumentation Trace Macrocell).

    BLK_DESCR, REG_DESCR, BIT_DESCR
    -------------------------------
    Maps a block/register/bitfield mnemonic to a description.
    """
    
    def __init__(self, devfile, devfmt=Block.fmt, blkfmt=None, regfmt=None, bitfmt=None):
        if isinstance(devfile, basestring):
            devfile = __import__('mmdev.'+devfile, fromlist=[''])

        subblocks = []
        for blkname, blkaddr in devfile.MEM_MAP.iteritems():
            registers = []
            for regname in devfile.BLK_MAP.get(blkname,()):
                regaddr = devfile.REG_MAP[regname]
                bitfields = [BitField(bitname, bitmask,
                                      fullname=devfile.BIT_NAME.get(bitname,'BitField'),
                                      descr=devfile.BIT_DESCR.get(bitname,''),
                                      fmt=bitfmt)
                             for bitname, bitmask in devfile.BIT_MAP[regname].iteritems()]

                registers.append(Register(regname, regaddr, bitfields,
                                          fullname=devfile.REG_NAME.get(regname,'Register'),
                                          descr=devfile.REG_DESCR.get(regname,''),
                                          fmt=regfmt))

            subblocks.append(DeviceBlock(blkname, blkaddr, registers,
                                         devfile.BLK_NAME.get(blkname,'Block'),
                                         devfile.BLK_DESCR.get(blkname,''),
                                         fmt=blkfmt))

        name = getattr(devfile, 'name', 'DUT')
        mnem = getattr(devfile, 'mnemonic', devfile.__name__)
        descr = getattr(devfile, 'descr', '')

        super(DUT, self).__init__(mnem, 0, subblocks, fullname=name, descr=descr, fmt=devfmt)
