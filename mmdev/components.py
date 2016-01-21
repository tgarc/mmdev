from mmdev import blocks
from mmdev import utils


class CPU(blocks.LeafBlock):
    _attrs = 'revision', 'endian', 'mpuPresent', 'fpuPresent'

    def __init__(self, mnemonic, revision, endian, mpuPresent, fpuPresent, **kwargs):
        super(CPU, self).__init__(mnemonic, **kwargs)
        self._revision = revision
        self._endian = endian
        self._mpuPresent = mpuPresent
        self._fpuPresent = fpuPresent


class Peripheral(blocks.MemoryMappedBlock):
    _dynamicBinding = True

    def __new__(cls, *args, **kwargs):
        return super(Peripheral, cls).__new__(cls, *args, bind=True, **kwargs)


class Register(blocks.IOBlock):
    _dynamicBinding = True
    _attrs = 'resetValue', 'resetMask', 'width'

    def __new__(cls, mnemonic, width, address, subblocks, resetMask=0, resetValue=None, **kwargs):
        return super(Register, cls).__new__(cls, mnemonic, address, subblocks, **kwargs)

    def __init__(self, mnemonic, width, address, subblocks, resetMask=0, resetValue=None, **kwargs):
        super(Register, self).__init__(mnemonic, address, subblocks, **kwargs)
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
    _subfmt="{mask} {mnemonic}"
    _attrs = 'mask'

    def __new__(cls, mnemonic, width, offset, values=[], **kwargs):
        return super(BitField, cls).__new__(cls, mnemonic, offset, values, bind=False, **kwargs)

    def __init__(self, mnemonic, width, offset, values=[], **kwargs):
        super(BitField, self).__init__(mnemonic, offset, values, bind=False, **kwargs)
        self._mask = utils.HexValue(((1 << width) - 1) << offset)
        self._width = width

    @property
    def _key(self):
        return self._mask

    def _set_width(self, width):
        self._mask = utils.HexValue(self._mask, width)

    def _read(self):
        return (self.parent.value & self._mask) >> self._address

    def _write(self, value):
        self.parent.value = (self.parent.value & ~self._mask) | (value << self._address)

    def __ilshift__(self, other):
        regval = self.parent.value 
        bitval = (regval & self._mask) << other
        self.parent.value = (regval & ~self._mask) | (bitval & self._mask)
    def __irshift__(self, other):
        regval = self.parent.value 
        bitval = (regval & self._mask) >> other
        self.parent.value = (regval & ~self._mask) | (bitval & self._mask)
    def __iand__(self, other):
        regval = self.parent.value 
        bitval = (regval & self._mask) & (other << self._address)
        self.parent.value = (regval & ~self._mask) | (bitval & self._mask)
    def __ixor__(self, other):
        regval = self.parent.value 
        bitval = (regval & self._mask) ^ (other << self._address)
        self.parent.value = (regval & ~self._mask) | (bitval & self._mask)
    def __ior__(self, other):
        regval = self.parent.value 
        bitval = (regval & self._mask) | (other << self._address)
        self.parent.value = (regval & ~self._mask) | (bitval & self._mask)

    def __repr__(self):
        return "<{:s} '{:s}' in {:s} '{:s}' & {}>".format(self._typename, 
                                                          self._mnemonic,
                                                          self.parent._typename,
                                                          self.parent._mnemonic, 
                                                          self._mask)

class EnumeratedValue(blocks.LeafBlock):
    _fmt = "{mnemonic} (value={value}): {description}"
    _attrs = 'value'

    def __init__(self, mnemonic, value, **kwargs):
        super(EnumeratedValue, self).__init__(mnemonic, **kwargs)
        self._value = utils.HexValue(value)

    @property
    def _key(self):
        return self._value

    def __repr__(self):
        return "<{:s} '{:s}' in {:s} '{:s}'>".format(self._typename,
                                                     self._mnemonic,
                                                     self.parent._typename,
                                                     self.parent._mnemonic)
