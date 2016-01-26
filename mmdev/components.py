from mmdev import blocks
from mmdev import utils


accessKeys = ['read', 'write', 'read-write']

class CPU(blocks.LeafBlock):
    _attrs = 'revision', 'endian', 'mpuPresent', 'fpuPresent'

    def __init__(self, mnemonic, revision, endian, mpuPresent, fpuPresent, fullname=None, descr='-', kwattrs={}):
        super(CPU, self).__init__(mnemonic, fullname=fullname, descr=descr, kwattrs=kwattrs)
        self._revision = revision
        self._endian = endian
        self._mpuPresent = mpuPresent
        self._fpuPresent = fpuPresent


class Peripheral(blocks.MemoryMappedBlock):
    _dynamicBinding = True

    def __init__(self, mnemonic, registers, baseAddress, bind=True, fullname=None, descr='-', kwattrs={}):
        super(Peripheral, self).__init__(mnemonic, registers, baseAddress, bind=bind, fullname=fullname, descr=descr, kwattrs=kwattrs)


class Register(blocks.IOBlock):
    _dynamicBinding = True
    _attrs = 'resetValue', 'resetMask', 'width'

    def __init__(self, mnemonic, fields, address, width, resetMask=0,
                 resetValue=None, access='read-write', bind=True, fullname=None,
                 descr='-', kwattrs={}):
        super(Register, self).__init__(mnemonic, fields, address, access=access,
                                       bind=bind, fullname=fullname, descr=descr, kwattrs=kwattrs)
        if resetMask == 0:
            resetValue = 0
        self._width = width
        self._resetValue = utils.HexValue(resetValue, width)
        self._resetMask = utils.HexValue(resetMask, width)

    def _read(self):
        return self.root.read(self._address, self._width)

    def _write(self, value):
        return self.root.write(self._address, value, self._width)

    def __invert__(self):
        return ~self.value

    def __lshift__(self, other):
        return self.value << other
    def __rshift__(self, other):
        return self.value >> other
    def __and__(self, other):
        return self.value & other
    def __xor__(self, other):
        return self.value ^ other
    def __or__(self, other):
        return self.value | other

    def __rlshift__(self, other):
        return self.value << other
    def __rrshift__(self, other):
        return self.value >> other
    def __rand__(self, other):
        return self.value & other
    def __rxor__(self, other):
        return self.value ^ other
    def __ror__(self, other):
        return self.value | other


class BitField(blocks.IOBlock):
    _fmt = "{name} ({mnemonic}, {mask})"
    _subfmt="{mask} {mnemonic}"
    _attrs = 'mask', 'width'

    def __new__(cls, mnemonic, offset, width, values=[], **kwargs):
        return super(BitField, cls).__new__(cls, mnemonic, values, offset, bind=False, **kwargs)

    def __init__(self, mnemonic, offset, width, values=[], access='read-write', fullname=None, descr='-', kwattrs={}):
        super(BitField, self).__init__(mnemonic, values, offset, access=access,
                                       bind=False, fullname=fullname,
                                       descr=descr, kwattrs=kwattrs)

        self._mask = utils.HexValue(((1 << width) - 1) << offset)
        self._width = width

    @property
    def _key(self):
        return self._mask

    def _set_width(self, width):
        self._mask = utils.HexValue(self._mask, width)

    def _read(self):
        return (self.parent.value & self._mask) >> self._address

    # notice that writing a bitfield requires a read of the register first
    def _write(self, value):
        self.parent.value = (self.parent.value & ~self._mask) | (value << self._address)

    def __invert__(self):
        return ~self._key

    def __lshift__(self, other):
        return self._key << other
    def __rshift__(self, other):
        return self._key >> other
    def __and__(self, other):
        return self._key & other
    def __xor__(self, other):
        return self._key ^ other
    def __or__(self, other):
        return self._key | other

    def __rlshift__(self, other):
        return self._key << other
    def __rrshift__(self, other):
        return self._key >> other
    def __rand__(self, other):
        return self._key & other
    def __rxor__(self, other):
        return self._key ^ other
    def __ror__(self, other):
        return self._key | other

    def __repr__(self):
        return "<{:s} '{:s}' in {:s} '{:s}' & {}>".format(self._typename, 
                                                          self._mnemonic,
                                                          self.parent._typename,
                                                          self.parent._mnemonic, 
                                                          self._mask)

class EnumeratedValue(blocks.LeafBlock):
    _fmt = "{mnemonic} (value={value})"
    _subfmt="{value} {mnemonic}"
    _attrs = 'value'

    def __new__(cls, mnemonic, value, **kwargs):
        return super(EnumeratedValue, cls).__new__(cls, mnemonic, **kwargs)

    def __init__(self, mnemonic, value, fullname=None, descr='-', kwattrs={}):
        super(EnumeratedValue, self).__init__(mnemonic, fullname=fullname, descr=descr, kwattrs=kwattrs)
        self._value = utils.HexValue(value)

    @property
    def _key(self):
        return self._value

    def __repr__(self):
        return "<{:s} '{:s}' in {:s} '{:s}'>".format(self._typename,
                                                     self._mnemonic,
                                                     self.parent._typename,
                                                     self.parent._mnemonic)
