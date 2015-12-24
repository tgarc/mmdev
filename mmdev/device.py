import ctypes as _ctypes
import mmdev.blocks as blocks
import mmdev.link as link
import utils

_bruijn32lookup = [0, 1, 28, 2, 29, 14, 24, 3, 30, 22, 20, 15, 25, 17, 4, 8, 
                   31, 27, 13, 23, 21, 19, 16, 7, 26, 12, 18, 6, 11, 5, 10, 9]

_levels = {'device': 0,
           'peripheral': 1,
           'register': 2,
           'bitfield': 3}


class Device(blocks.Block):
    _fmt = "{name} ({mnemonic}, {vendor})"

    def __init__(self, mnemonic, blocks, fullname='', descr='', width=32, addressbits=8, vendor='Unknown Vendor'):
        super(Device, self).__init__(mnemonic, blocks, fullname=fullname, descr=descr)
        self._link = link.Link()

        self._width = width
        self._addressbits = addressbits
        self.vendor = vendor or 'Unknown Vendor'
        
        self._fields += ['vendor']

        self._map = {}
        for blk in self.walk():
            key = blk.mnemonic.lower()
            if key in self._map:
                if not isinstance(self._map[key], list):
                    self._map[key] = [self._map[key]]
                self._map[key].append(blk)
            else:
                self._map[key] = blk

        for blk in self.walk(3, l=0):
            blk._sort(key=lambda blk: blk.address)

    def set_format(self, blocktype, fmt):
        for blk in self.walk(d=1, l=_levels[blocktype.lower()]):
            blk._fmt = fmt

    def find(self, key):
        return self._map.get(key.lower())

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
    

def Peripheral(mnemonic, address, subblocks, fullname='', descr=''):
    class Peripheral(blocks.MemoryMappedBlock):
        _dynamic = True

        def __init__(self, mnemonic, address, subblocks, fullname='', descr='', interrupts=None):
            super(Peripheral, self).__init__(mnemonic, address, subblocks,
                                             fullname=fullname, descr=descr)
            self.interrupts = interrupts

    return Peripheral(mnemonic, address, subblocks, fullname=fullname, descr=descr)


def Register(mnemonic, address, subblocks, resetValue, resetMask, fullname='', descr=''):
    class Register(blocks.DescriptorMixin, blocks.MemoryMappedBlock):
        _dynamic = True

        def __new__(cls, mnemonic, address, subblocks, resetValue, resetMask,
                     fullname='', descr=''):
            return super(Register, cls).__new__(cls, mnemonic, address, subblocks,
                                                fullname=fullname, descr=descr)

        def __init__(self, mnemonic, address, subblocks, resetValue, resetMask,
                     fullname='', descr=''):
            super(Register, self).__init__(mnemonic, address, subblocks, fullname=fullname, descr=descr)
            self.resetValue = utils.HexValue(resetValue)
            self.resetMask = utils.HexValue(resetMask)
            self._fields += ['resetValue', 'resetMask']
            
        def _read(self):
            return self.root.read(self.address)

        def _write(self, value):
            return self.root.write(self.address, value)

    return Register(mnemonic, address, subblocks, resetValue, resetMask, fullname=fullname, descr=descr)


class BitField(blocks.DescriptorMixin, blocks.LeafBlock):
    _fmt = "{name} ({mnemonic}, 0x{mask:08X})"
    _subfmt="0x{mask:08X} {mnemonic:s}"

    def __init__(self, mnemonic, mask, fullname='', descr=''):
        # calculate the bit offset from the mask using a debruijn hash function
        # use ctypes to truncate the result to a uint32
        # TODO: change to a 64 bit version of the lookup
        super(BitField, self).__init__(mnemonic, fullname=fullname, descr=descr)
        self.mask = utils.HexValue(mask)
        self.address = _bruijn32lookup[_ctypes.c_uint32((mask & -mask) * 0x077cb531).value >> 27]
        self._fields += ['mask', 'address']

    def _read(self):
        return (self.parent.value & self.mask) >> self.address

    def _write(self, value):
        self.parent.value = (self.parent.value & ~self.mask) | (value << self.address)

    def __repr__(self):
        return "<{:s} '{:s}' in {:s} '{:s}' & 0x{:08x}>".format(self.typename, 
                                                                self.mnemonic,
                                                                self.parent.typename,
                                                                self.parent.mnemonic, 
                                                                self.mask)
