from mmdev import blocks
from mmdev import link
from mmdev import utils


_levels = {'device': 0,
           'peripheral': 1,
           'register': 2,
           'bitfield': 3}


class Device(blocks.Block):
    _fmt = "{name} ({mnemonic}, {vendor})"
    _attrs = blocks.Block._attrs + ['vendor', 'width', 'addressbits']

    def __new__(cls, mnemonic, width, addressbits, blocks, cpu=None, fullname=None, descr='', vendor='Unknown Vendor', kwattrs={}):
        return super(Device, cls).__new__(cls, mnemonic, blocks, fullname=fullname, descr=descr, kwattrs=kwattrs)

    def __init__(self, mnemonic, width, addressbits, blocks, cpu=None, fullname=None, descr='', vendor='Unknown Vendor', kwattrs={}):
        super(Device, self).__init__(mnemonic, blocks, fullname=fullname, descr=descr, kwattrs=kwattrs)

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

        # walk through all parent nodes
        for blk in self.walk(3, l=0):
            blk._sort(key=lambda blk: blk._address)

        for blk in self.walk(3):
            blk._set_width(self._width)
        self._link = link.MockLink()
            
    def unlink(self):
        self._link.disconnect()
        self._link = link.MockLink()

    def link(self, link):
        self._link.disconnect()
        self._link = link
        self._link.connect()

    def set_format(self, blocktype, fmt):
        for blk in self.walk(d=1, l=_levels[blocktype]):
            blk._fmt = fmt

    def find(self, key):
        res = self.findall(key)
        if len(res):
            return res[0]
        return res

    def findall(self, key):
        res = self._map.get(key)
        if res is None:
            return ()
        return tuple(res) if isinstance(res, list) else (res,)

    def write(self, address, value, accessSize=None):
        if accessSize is None:
            accessSize = self._width
        self._link.writeMem(address, value, accessSize=accessSize)

    def read(self, address, accessSize=None):
        if accessSize is None:
            accessSize = self._width
        return utils.HexValue(self._link.readMem(address, accessSize=accessSize), accessSize)

    @staticmethod
    def from_devfile(devfile, file_format, raiseErr=True):
        """
        Parse a device file using the given file format
        """
        from mmdev import parsers
        parse = parsers.PARSERS[file_format]
        return parse(devfile, raiseErr=raiseErr)

    # @classmethod
    # def from_json(cls, devfile):
    #     return cls.from_devfile(devfile, 'json')

    # @classmethod
    # def from_pycfg(cls, devfile):
    #     return cls.from_devfile(devfile, 'pycfg')

    @classmethod
    def from_svd(cls, devfile, **kwargs):
        return cls.from_devfile(devfile, 'svd', **kwargs)


class CPU(blocks.LeafBlock):
    _attrs = blocks.LeafBlock._attrs + ['revision', 'endian', 'mpuPresent', 'fpuPresent']

    def __init__(self, mnemonic, revision, endian, mpuPresent, fpuPresent, kwattrs={}):
        super(CPU, self).__init__(mnemonic, kwattrs=kwattrs)
        self._revision = revision
        self._endian = endian
        self._mpuPresent = mpuPresent
        self._fpuPresent = fpuPresent


class Peripheral(blocks.MemoryMappedBlock):
    _dynamicBinding = True

    def __new__(cls, mnemonic, address, subblocks, fullname=None, descr='', kwattrs={}):
        return super(Peripheral, cls).__new__(cls, mnemonic, address, subblocks, fullname=fullname, descr=descr, kwattrs=kwattrs, bind=True)

    def __init__(self, mnemonic, address, subblocks, fullname=None, descr='', kwattrs={}):
        super(Peripheral, self).__init__(mnemonic, address, subblocks, fullname=fullname, descr=descr, kwattrs=kwattrs, bind=True)
        self._address = utils.HexValue(address)


class Register(blocks.IOBlock):
    _dynamicBinding = True
    _attrs = blocks.IOBlock._attrs + ['resetValue', 'resetMask', 'width']

    def __new__(cls, mnemonic, width, address, subblocks, resetMask=0, resetValue=None,
                fullname=None, descr='', kwattrs={}):
        return super(Register, cls).__new__(cls, mnemonic, address, subblocks,
                                            fullname=fullname, descr=descr, kwattrs=kwattrs)

    def __init__(self, mnemonic, width, address, subblocks, resetMask=0, resetValue=None,
                fullname=None, descr='', kwattrs={}):
        super(Register, self).__init__(mnemonic, address, subblocks, 
                                       fullname=fullname, descr=descr, kwattrs=kwattrs)
        if resetMask == 0:
            resetValue = 0
        self._width = width
        self._resetValue = utils.HexValue(resetValue, width)
        self._resetMask = utils.HexValue(resetMask, width)

    def _read(self):
        return self.root.read(self._address, self._width)

    def _write(self, value):
        return self.root.write(self._address, value, self._width)


class BitField(blocks.IOBlock):
    _fmt = "{name} ({mnemonic}, {mask})"
    _subfmt="{mask} {mnemonic:s}"
    _attrs = blocks.IOBlock._attrs + ['mask']

    def __new__(cls, mnemonic, width, offset, values=[], fullname=None, descr='', kwattrs={}):
        return super(BitField, cls).__new__(cls, mnemonic, offset, values, fullname=fullname, descr=descr, kwattrs=kwattrs, bind=False)

    def __init__(self, mnemonic, width, offset, values=[], fullname=None, descr='', kwattrs={}):
        super(BitField, self).__init__(mnemonic, offset, values, fullname=fullname, descr=descr, kwattrs=kwattrs, bind=False)
        self._mask = utils.HexValue(((1 << width) - 1) << offset)

    def _set_width(self, width):
        self._mask = utils.HexValue(self._mask, width)

    def _read(self):
        return (self.parent.value & self._mask) >> self._address

    def _write(self, value):
        self.parent.value = (self.parent.value & ~self._mask) | (value << self._address)

    def __repr__(self):
        return "<{:s} '{:s}' in {:s} '{:s}' & {}>".format(self._typename, 
                                                          self._mnemonic,
                                                          self.parent._typename,
                                                          self.parent._mnemonic, 
                                                          self._mask)

class EnumeratedValue(blocks.LeafBlock):
    _fmt = "{mnemonic} (value={value}): {description}"
    _attrs = blocks.LeafBlock._attrs + ['value']

    def __init__(self, mnemonic, value, fullname=None, descr='', kwattrs={}):
        super(EnumeratedValue, self).__init__(mnemonic, fullname=fullname, descr=descr, kwattrs=kwattrs)
        self._value = utils.HexValue(value)

    def __repr__(self):
        return "<{:s} '{:s}' in {:s} '{:s}'>".format(self._typename,
                                                     self._mnemonic,
                                                     self.parent._typename,
                                                     self.parent._mnemonic)
