from mmdev import blocks
from mmdev import utils


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
