class Block(object):
    fmt="{name:s} ({mnemonic:s})"

    def __init__(self, name, fullname='', descr='', fmt=None):
        self.mnemonic = name
        self.name = fullname
        self.descr = descr
        self.fmt = self.__class__.fmt if fmt is None else fmt
        self.fields = ['mnemonic','name','descr']

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
        return self.fmt.format(**self._fields)

    def __str__(self):
        return "{:s}('{:s}')".format(self.__class__.__name__, self.mnemonic)


class DeviceBlock(Block):
    fmt="0x{addr:08X} {mnemonic:s}"

    def __init__(self, name, addr, blocks=[], fullname='', descr='', fmt=None):
        super(DeviceBlock, self).__init__(name, fullname=fullname, descr=descr, fmt=fmt)

        self.addr = addr
        self.fields += ['addr']
        self.blocks = tuple(blocks)

        for blk in self.blocks:
            setattr(self, blk.mnemonic.lower(), blk)

        # sort by address
        self.blocks = sorted(self.blocks, key=lambda blk: blk.addr, reverse=True)
        self.blocks = tuple(self.blocks)

    def iterkeys(self):
        return iter(self.blocks)

    def keys(self):
        return list(self.blocks)

    def iteritems(self):
        return iter((blk.mnemonic, blk) for blk in self.blocks)

    def items(self):
        return list(self.iteritems())

    def __repr__(self):
        dstr = self.fmt.format(**self._fields) + '\n'
        dstr+= "Registers:\n\t"
        dstr+= "\n\t".join([reg.fmt.format(**reg._fields) for reg in self.blocks])
        return dstr

    def __str__(self):
        return "{:s}('{:s}', 0x{:08X})".format(self.__class__.__name__, self.mnemonic, self.addr)


class Register(DeviceBlock):
    def __init__(self, regname, addr, bitfields, fullname='', descr='', fmt=None):
        super(Register, self).__init__(regname, addr, bitfields, fullname=fullname, descr=descr, fmt=fmt)

    def __repr__(self):
        dstr = self.fmt.format(**self._fields) + '\n'
        dstr+= "BitFields:\n\t"
        dstr+= "\n\t".join([bf.fmt.format(**bf._fields) for bf in self.blocks])
        return dstr

class BitField(Block):
    fmt="0x{mask:08X} {mnemonic:s}"

    def __init__(self, bfname, mask, fullname='', descr='', fmt=None):
        super(BitField, self).__init__(bfname, fullname=fullname, descr=descr, fmt=fmt)
        self.mask = mask
        self.addr = mask
        self.fields += ['mask',]

    def __str__(self):
        return "{:s}('{:s}', 0x{:08X})".format(self.__class__.__name__, self.mnemonic, self.mask)

class DUT(DeviceBlock):
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

    BLK_NAME, REG_NAME
    ------------------
    Maps a block/register mnemonic to its full name (e.g., ITM :
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
                                      fullname=devfile.BIT_NAME.get(bitname,'bitfield'),
                                      descr=devfile.BIT_DESCR.get(bitname,''),
                                      fmt=bitfmt)
                             for bitname, bitmask in devfile.BIT_MAP[regname].iteritems()]

                registers.append(Register(regname, regaddr, bitfields,
                                          fullname=devfile.REG_NAME.get(regname,'register'),
                                          descr=devfile.REG_DESCR.get(regname,''),
                                          fmt=regfmt))

            subblocks.append(DeviceBlock(blkname, blkaddr, registers,
                                         devfile.BLK_NAME.get(blkname,'block'),
                                         devfile.BLK_DESCR.get(blkname,''),
                                         fmt=blkfmt))

        name = getattr(devfile, 'name', devfile.__name__)
        mnem = getattr(devfile, 'mnemonic', 'DUT')
        descr = getattr(devfile, 'descr', '')

        super(DUT, self).__init__(mnem, 0, subblocks, fullname=name, descr=descr, fmt=devfmt)

    def __repr__(self):
        dstr = self.fmt.format(**self._fields) + '\n'
        dstr+= "Blocks:\n\t"
        dstr+= "\n\t".join([blk.fmt.format(**blk._fields) for blk in self.blocks])
        return dstr

    def __str__(self):
        return "{:s}('{:s}', 0x{:08X})".format(self.__class__.__name__, self.mnemonic, self.addr)
