from mmdev import blocks
from mmdev import utils


class CPU(blocks.LeafBlock):
    _attrs = 'revision', 'endian', 'mpuPresent', 'fpuPresent'

    def __init__(self, mnemonic, revision, endian, mpuPresent, fpuPresent, fullname=None, descr='-', kwattrs={}):
        super(CPU, self).__init__(mnemonic, fullname=fullname, descr=descr, kwattrs=kwattrs)
        self._revision = revision
        self._endian = endian
        self._mpuPresent = mpuPresent
        self._fpuPresent = fpuPresent


class Peripheral(blocks.MemoryMappedBlock):
    """
    Models a generic hardware block that is mapped into a memory
    space. Instances of this class serve mostly as an abstraction that
    encapsulate groups of registers.

    Parameters
    ----------
    mnemonic : str
        Shorthand or abbreviated name of block.
    subblocks : list-like
        All the children of this block.
    address : int
        The absolute address of this block.
    size : int
        Specifies the size of the address region being covered by this block in
        units of the root device's minimum addressable block or
        ``lane_width``. (see help for ``mmdev.device.Device``). e.g., For a
        byte-addressable device, size should be in byte units. The end address
        of an address block results from the sum of address and (size - 1).
    bind : bool
        Tells the constructor whether or not to bind subblocks as attributes of
        the Block instance.
    fullname : str
        Expanded name or display name of block.
    descr : str
        A string describing functionality, usage, and other relevant notes about
        the block.
    """
    _dynamicBinding = True

    def __init__(self, mnemonic, registers, address, size, bind=True,
                 fullname=None, descr='-', kwattrs={}):
        super(Peripheral, self).__init__(mnemonic, registers,
                                         address, size, bind=bind,
                                         fullname=fullname, descr=descr,
                                         kwattrs=kwattrs)
        
class Register(blocks.IOBlock):
    _dynamicBinding = True
    _attrs = 'resetValue', 'resetMask'

    def __init__(self, mnemonic, fields, address, size, resetMask=0,
                 resetValue=None, access='read-write', bind=True, fullname=None,
                 descr='-', kwattrs={}):
        super(Register, self).__init__(mnemonic, fields, address, size,
                                       access=access, bind=bind,
                                       fullname=fullname, descr=descr,
                                       kwattrs=kwattrs)
        if resetMask == 0:
            resetValue = 0
        self._resetValue = utils.HexValue(resetValue, self._size)
        self._resetMask = utils.HexValue(resetMask, self._size)

        for field in self:
            field._mask = utils.HexValue(field._mask, self._size)

    def status(self):
        v = self.value

        headerstr = self._fmt.format(**self.attrs)
        substr = ''
        for blk in self:
            bitval = utils.HexValue((v&blk._mask) >> blk._address, blk._size)
            substr += "\n\t%s %s %s" % (blk._mask, blk._mnemonic, bitval)

        print headerstr + substr if substr else headerstr

    def pack(self, *args, **kwargs):
        nodesdict = dict(self.items())
        nodes = list((self._nodes[idx], v) for idx, v in enumerate(args)) 
        nodes+= [(nodesdict[k.upper()], v) for k, v in kwargs.items()]

        v = self.value
        for f, a in nodes:
            v = (v & ~f._mask) | ((a << f._address) & f._mask)
        self.value = v

    def unpack(self):
        v = self.value
        return tuple(utils.HexValue((v&f._mask) >> f._address, f._size) for f in self)
 

class BitField(blocks.IOBlock):
    _fmt = "{name} ({mnemonic}, {access}, {mask})"
    _macrokey = _attrs = 'mask'

    def __new__(cls, mnemonic, offset, width, values=[], **kwargs):
        return super(BitField, cls).__new__(cls, mnemonic, values, offset, bind=False, **kwargs)

    def __init__(self, mnemonic, offset, width, values=[], access='read-write', fullname=None, descr='-', kwattrs={}):
        super(BitField, self).__init__(mnemonic, values, offset, width,
                                       access=access, bind=False,
                                       fullname=fullname, descr=descr,
                                       kwattrs=kwattrs)

        self._mask = utils.HexValue(((1 << self._size) - 1) << self._address)

    def _read(self):
        # return (self.root.read(self.parent._address + self._address, self._size) & self._mask) >> self._address
        return (self.parent.value & self._mask) >> self._address

    # notice that writing a bitfield requires a read of the register first
    def _write(self, value):
        # v = (self.root.read(self.parent._address + self._address, self._size) & self._mask) >> self._address
        # self.root.write(self.parent._address + self._address, (value << self._address) & self._mask, self._size)
        self.parent.value = (self.parent.value & ~self._mask) | ((value << self._address) & self._mask)

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
    _fmt = "{mnemonic} (value={value})"
    _attrs = 'value'
    _macrokey = 'value'

    def __new__(cls, mnemonic, value, **kwargs):
        return super(EnumeratedValue, cls).__new__(cls, mnemonic, **kwargs)

    def __init__(self, mnemonic, value, fullname=None, descr='-', kwattrs={}):
        super(EnumeratedValue, self).__init__(mnemonic, fullname=fullname, descr=descr, kwattrs=kwattrs)
        self._value = utils.HexValue(value)

    def __repr__(self):
        return "<{:s} '{:s}' in {:s} '{:s}'>".format(self._typename,
                                                     self._mnemonic,
                                                     self.parent._typename,
                                                     self.parent._mnemonic)

