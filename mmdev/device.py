import ctypes
import mmdev.blocks as blocks
import mmdev.link as link
import utils


_bruijn32lookup = [0, 1, 28, 2, 29, 14, 24, 3, 30, 22, 20, 15, 25, 17, 4, 8, 
                   31, 27, 13, 23, 21, 19, 16, 7, 26, 12, 18, 6, 11, 5, 10, 9]

_levels = {'device': 0,
           'peripheral': 1,
           'register': 2,
           'bitfield': 3}


class CPU(blocks.LeafBlock):
    _attrs = blocks.Block._attrs + ['revision', 'endian', 'mpuPresent', 'fpuPresent', 'vtorPresent', 'nvicPrioBits']

    def __init__(self, mnemonic, revision, endian, mpuPresent, fpuPresent, nvicPrioBits, vtorPresent=True, kwattrs={}):
        super(CPU, self).__init__(mnemonic, kwattrs=kwattrs)
        self._revision = revision
        self._endian = endian
        self._mpuPresent = mpuPresent
        self._fpuPresent = fpuPresent
        self._vtorPresent = vtorPresent
        self._nvicPrioBits = nvicPrioBits


class Device(blocks.Block):
    _fmt = "{name} ({mnemonic}, {vendor})"
    _attrs = blocks.Block._attrs + ['vendor']

    def __init__(self, mnemonic, blocks, cpu=None, fullname='', descr='', width=32, addressbits=8, vendor='Unknown Vendor', kwattrs={}):
        super(Device, self).__init__(mnemonic, blocks, fullname=fullname, descr=descr, kwattrs=kwattrs)
        self._link = link.Link()

        self.cpu = cpu
        self._width = width
        self._addressbits = addressbits
        self._vendor = vendor or 'Unknown Vendor'
        
        self._map = {}
        for blk in self.walk():
            key = blk._mnemonic
            if key in self._map:
                if not isinstance(self._map[key], list):
                    self._map[key] = [self._map[key]]
                self._map[key].append(blk)
            else:
                self._map[key] = blk

        for blk in self.walk(3, l=0):
            blk._sort(key=lambda blk: blk._address)

            
    def set_format(self, blocktype, fmt):
        for blk in self.walk(d=1, l=_levels[blocktype]):
            blk._fmt = fmt

    def findall(self, key):
        res = self._map[key]
        return tuple(res) if isinstance(res, list) else (res,)

    def write(self, address, value):
        self._link.write(address, value)

    def read(self, address):
        return utils.HexValue(self._link.read(address), self.root._width)

    @staticmethod
    def from_devfile(devfile, file_format):
        """
        Parse a device file using the given file format
        """
        from mmdev import parsers
        parse = parsers.PARSERS[file_format]
        return parse(devfile)

    @classmethod
    def from_json(cls, devfile):
        return cls.from_devfile(devfile, 'json')

    @classmethod
    def from_pycfg(cls, devfile):
        return cls.from_devfile(devfile, 'pycfg')

    @classmethod
    def from_svd(cls, devfile):
        return cls.from_devfile(devfile, 'svd')
    

def Peripheral(mnemonic, address, subblocks, fullname='', descr='', kwattrs={}):
    class Peripheral(blocks.MemoryMappedBlock):
        _dynamic = True

        def __init__(self, mnemonic, address, subblocks, fullname='', descr='', interrupts=None, kwattrs={}):
            super(Peripheral, self).__init__(mnemonic, address, subblocks,
                                             fullname=fullname, descr=descr)
            self.interrupts = interrupts

    return Peripheral(mnemonic, address, subblocks, fullname=fullname, descr=descr, kwattrs=kwattrs)


def Register(mnemonic, address, subblocks, resetValue, resetMask, fullname='', descr='', kwattrs={}):
    class Register(blocks.DescriptorMixin, blocks.MemoryMappedBlock):
        _dynamic = True
        _attrs = blocks.MemoryMappedBlock._attrs + ['resetValue', 'resetMask']

        def __new__(cls, mnemonic, address, subblocks, resetValue, resetMask,
                     fullname='', descr='', kwattrs={}):
            return super(Register, cls).__new__(cls, mnemonic, address, subblocks,
                                                fullname=fullname, descr=descr, kwattrs=kwattrs)

        def __init__(self, mnemonic, address, subblocks, resetValue, resetMask,
                     fullname='', descr='', kwattrs={}):
            super(Register, self).__init__(mnemonic, address, subblocks, fullname=fullname, descr=descr, kwattrs=kwattrs)
            self._resetValue = utils.HexValue(resetValue)
            self._resetMask = utils.HexValue(resetMask)
            
        def _read(self):
            return self.root.read(self._address)

        def _write(self, value):
            return self.root.write(self._address, value)

    return Register(mnemonic, address, subblocks, resetValue, resetMask, fullname=fullname, descr=descr, kwattrs={})


class BitField(blocks.DescriptorMixin, blocks.Block):
    _fmt = "{name} ({mnemonic}, 0x{mask:08X})"
    _subfmt="0x{mask:08X} {mnemonic:s}"
    _attrs = blocks.Block._attrs + ['mask', 'address']

    def __new__(cls, mnemonic, mask, values=[], fullname='', descr='', kwattrs={}):
        return super(BitField, cls).__new__(cls, mnemonic, values, fullname=fullname, descr=descr, kwattrs=kwattrs)

    def __init__(self, mnemonic, mask, values=[], fullname='', descr='', kwattrs={}):
        # calculate the bit offset from the mask using a debruijn hash function
        # use ctypes to truncate the result to a uint32
        # TODO: change to a 64 bit version of the lookup
        super(BitField, self).__init__(mnemonic, [], fullname=fullname, descr=descr, kwattrs=kwattrs)
        self._mask = utils.HexValue(mask)
        self._address = utils.HexValue(_bruijn32lookup[ctypes.c_uint32((mask & -mask) * 0x077cb531).value >> 27])

        self._nodes = values
        for blk in self._nodes:
            blk.root = blk.parent = self

    def _read(self):
        return (self.parent.value & self._mask) >> self._address

    def _write(self, value):
        self.parent.value = (self.parent.value & ~self._mask) | (value << self._address)

    def __repr__(self):
        return "<{:s} '{:s}' in {:s} '{:s}' & 0x{:08x}>".format(self._typename, 
                                                                self._mnemonic,
                                                                self.parent._typename,
                                                                self.parent._mnemonic, 
                                                                self._mask)

class EnumeratedValue(blocks.LeafBlock):
    _fmt = "{mnemonic} (value={value}): {description}"
    _attrs = blocks.LeafBlock._attrs + ['value']

    def __init__(self, mnemonic, value, fullname='', descr='', kwattrs={}):
        # calculate the bit offset from the mask using a debruijn hash function
        # use ctypes to truncate the result to a uint32
        # TODO: change to a 64 bit version of the lookup
        super(EnumeratedValue, self).__init__(mnemonic, fullname=fullname, descr=descr, kwattrs=kwattrs)
        self._value = value

    def __repr__(self):
        return "<{:s} '{:s}' in {:s} '{:s}'>".format(self._typename,
                                                     self._mnemonic,
                                                     self.parent._typename,
                                                     self.parent._mnemonic)
