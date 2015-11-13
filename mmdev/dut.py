import ctypes as _ctypes


class Block(object):
    fmt="{name:s} ({mnemonic:s})"

    def __init__(self, mnemonic, addr, parent=None, fullname='', descr='', fmt=None):
        self.mnemonic = mnemonic
        self.addr = addr
        self.name = fullname
        self.descr = descr
        self.fmt = self.__class__.fmt if fmt is None else fmt
        self._blocks = []
        self._map = {}

        self.type = self.__class__.__name__
        self.parent = parent
        self.root = self

        if parent is not None:
            p = parent
            while p.parent is not None:
                p = p.parent
            self.root = p

        self.fields = ['mnemonic', 'name', 'descr', 'addr', 'type', 'parent']

    def __getitem__(self, key):
        try:
            return self.root._map[key.lower()]
        except KeyError:
            raise KeyError(key)

    def _create_subblock(self, mnemonic, addr, blocktype, fullname='', descr='', fmt=None):
        subblock = blocktype(mnemonic, addr, parent=self, fullname=fullname, descr=descr, fmt=fmt)
        setattr(self, mnemonic.lower(), subblock)

        self._blocks.append(subblock)
        self.root._map[mnemonic.lower()] = subblock

        # sort by address
        self._blocks = sorted(self._blocks, key=lambda blk: blk.addr, reverse=True)

        return subblock

    def create_subblock(self, mnemonic, addr, fullname='', descr='', fmt=None):
        return self._create_subblock(mnemonic, addr, SubBlock, fullname=fullname, descr=descr, fmt=fmt)

    @property
    def parents(self):
        parents = []
        p = self.parent
        while p is not None:
            parents.append(p)
            p = p.parent
        return parents

    @property
    def fields(self):
        return self._fields.keys()

    @fields.setter
    def fields(self, fields):
        self._fields = {fn: getattr(self, fn) for fn in fields}

    @fields.deleter
    def fields(self):
        del self._fields

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
        dstr = self.fmt.format(**self._fields) + '\n\t'
        dstr+= "\n\t".join(["0x{addr:08X} {mnemonic:s}".format(**blk._fields) for blk in self._blocks])
        return dstr

    # def __repr__(self):
    #     return "<{:s} '{:s}'>".format(self.type, self.mnemonic)


class SubBlock(Block):
    fmt=' '.join(["{name:s}","({mnemonic:s}, 0x{addr:08X})"])
    def create_register(self, mnemonic, addr, fullname='', descr='', fmt=None):
        return self._create_subblock(mnemonic, addr, Register, fullname=fullname, descr=descr, fmt=fmt)

    # def __repr__(self):
    #     return "<{:s} '{:s}' at 0x{:08X} in '{:s}'>".format(self.type, self.mnemonic, self.addr, '.'.join([p.mnemonic for p in self.parents[::-1]]))


class Register(SubBlock):
    def create_bitfield(self, mnemonic, addr, fullname='', descr='', fmt=None):
        return self._create_subblock(mnemonic, addr, BitField, fullname=fullname, descr=descr, fmt=fmt)


_bruijn32lookup = [0, 1, 28, 2, 29, 14, 24, 3, 30, 22, 20, 15, 25, 17, 4, 8, 
                   31, 27, 13, 23, 21, 19, 16, 7, 26, 12, 18, 6, 11, 5, 10, 9]

class BitField(SubBlock):
    fmt=' '.join(["{name:s}","({mnemonic:s}, 0x{mask:08X})"])
    def __init__(self, mnemonic, mask, parent=None, fullname='', descr='', fmt=None):
        # calculate the bit offset from the mask using a debruijn hash function
        # use ctypes to truncate the result to a uint32
        # TODO: change to a 64 bit version of the lookup
        offset = _bruijn32lookup[_ctypes.c_uint32((mask & -mask) * 0x077cb531).value >> 27]

        super(BitField, self).__init__(mnemonic, offset, parent=parent, fullname=fullname, descr=descr, fmt=fmt)

        self.mask = mask
        self.fields += ['mask']


def DUT(devfile, devfmt=None, blkfmt=None, regfmt=None, bitfmt=None):
    """
    Create a DUT device from a device definition file.


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

    if isinstance(devfile, basestring):
        if devfile.endswith('.py'): # if this is a file path, import it first
            import imp, os
            devfile = imp.load_source(os.path.basename(devfile), devfile)
        else:
            devfile = __import__('mmdev.'+devfile, fromlist=[''])

    name = getattr(devfile, 'name', 'DUT')
    mnem = getattr(devfile, 'mnemonic', devfile.__name__)
    descr = getattr(devfile, 'descr', '')

    dut = Block(mnem, 0, fullname=name, descr=descr, fmt=devfmt)
    for blkname, blkaddr in devfile.BLK_MAP.iteritems():
        blk  = dut.create_subblock(blkname, blkaddr,
                                   fullname=devfile.BLK_NAME.get(blkname,'Block'),
                                   descr=devfile.BLK_DESCR.get(blkname,''),
                                   fmt=blkfmt)
        for regname, regaddr in devfile.REG_MAP.get(blkname,{}).iteritems():
            reg = blk.create_register(regname, regaddr,
                                      fullname=devfile.REG_NAME.get(regname,'Register'),
                                      descr=devfile.REG_DESCR.get(regname,''),
                                      fmt=regfmt)
            for bitname, bitmask in devfile.BIT_MAP.get(regname,{}).iteritems():
                bits = reg.create_bitfield(bitname, bitmask,
                                           fullname=devfile.BIT_NAME.get(bitname,'BitField'),
                                           descr=devfile.BIT_DESCR.get(regname,{}).get(bitname,''),
                                           fmt=bitfmt)

    return dut

