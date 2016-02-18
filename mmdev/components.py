from mmdev import blocks
from mmdev import utils


_levels = {'device': 0,
           'peripheral': 1,
           'register': 2,
           'bitfield': 3,
           'enumeratedvalue': 4}


class CPU(blocks.LeafBlock):
    _attrs = 'revision', 'endian', 'mpuPresent', 'fpuPresent'

    def __init__(self, mnemonic, revision, endian, mpuPresent, fpuPresent, displayName='', descr='', kwattrs={}):
        super(CPU, self).__init__(mnemonic, displayName=displayName, descr=descr, kwattrs=kwattrs)
        self._revision = revision
        self._endian = endian
        self._mpuPresent = mpuPresent
        self._fpuPresent = fpuPresent


class Device(blocks.DeviceBlock):
    """
    Models a generic hardware block that defines a single memory address space
    and its data bus.

    Parameters
    ----------
    mnemonic : str
        Shorthand or abbreviated name of block.
    subblocks : list-like
        All the children of this block.
    laneWidth : int
        Defines the number of data bits uniquely selected by each address. For
        example, a value of 8 denotes that the device is byte-addressable.
    busWidth : int
        Defines the bit-width of the maximum single data transfer supported by
        the bus infrastructure. For example, a value of 32 denotes that the
        device bus can transfer a maximum of 32 bits in a single transfer.
    bind : bool
        Tells the constructor whether or not to bind the subblocks as attributes
        of the Block instance.
    displayName : str
        Expanded name or display name of block.
    descr : str
        A string describing functionality, usage, and other relevant notes about
        the block.
    """
    _attrs = 'vendor'


    def __init__(self, mnemonic, subblocks, laneWidth, busWidth, 
                 bind=True, displayName='', descr='', vendor='', kwattrs={}):
        super(Device, self).__init__(mnemonic, subblocks, laneWidth, busWidth,
                                     bind=bind, displayName=displayName,
                                     descr=descr, kwattrs=kwattrs)
        self._vendor = vendor

        # purely for readability, set the address width for peripherals and
        # registers
        for blk in self.walk(d=2):
            blk._macrovalue = utils.HexValue(blk._macrovalue, self._busWidth)

        # register all the nodes into a map for searching
        self._map = {}
        for blk in self.walk():
            key = blk._mnemonic
            if key in self._map:
                if not isinstance(self._map[key], list):
                    self._map[key] = [self._map[key]]
                self._map[key].append(blk)
            else:
                self._map[key] = blk

    def set_format(self, blocktype, fmt):
        for blk in self.walk(d=1, l=_levels[blocktype.lower()]):
            blk._fmt = fmt

    def find(self, key):
        res = self.findall(key)
        if len(res):
            return res[0]
        else:
            raise ValueError("%s was not found")

    def findall(self, key):
        res = self._map.get(key)
        if res is None:
            return ()
        return tuple(res) if isinstance(res, list) else (res,)


class Peripheral(blocks.MemoryMappedBlock):
    """
    Models a generic hardware block that is mapped into a memory space. This
    class serve primarily as container for groups of registers.

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
        ``laneWidth``. (see help for ``mmdev.components.Device``). e.g., For a
        byte-addressable device, size should be in byte units. The end address
        of an address block results from the sum of address and (size - 1).
    bind : bool
        Tells the constructor whether or not to bind subblocks as attributes of
        the Block instance.
    displayName : str
        Expanded name or display name of block.
    descr : str
        A string describing functionality, usage, and other relevant notes about
        the block.
    """
    _dynamicBinding = True

    def __init__(self, mnemonic, registers, address, size, bind=True,
                 displayName='', descr='', kwattrs={}):
        super(Peripheral, self).__init__(mnemonic, registers,
                                         address, size, bind=bind,
                                         displayName=displayName, descr=descr,
                                         kwattrs=kwattrs)

        self._size = utils.HexValue(self._size)
        self._address = utils.HexValue(self._address)

        # purely for readability, set the data width for registers
        for reg in self:
            reg._address = utils.HexValue(reg._address, int.bit_length(self._size-1))


class Port(Peripheral):
    """
    Models a generic hardware block that lives in an address space *and* defines
    it's own independent address space.

    Parameters
    ----------
    mnemonic : str
        Shorthand or abbreviated name of block.
    subblocks : list-like
        All the children of this block.
    port : int
        The 'port' address of this block.
    byte_size : int
        Size of block in bytes.
    laneWidth : int
        Defines the number of data bits uniquely selected by each address. For
        example, a value of 8 denotes that the device is byte-addressable.
    busWidth : int
        Defines the bit-width of the maximum single data transfer supported by
        the bus infrastructure. For example, a value of 32 denotes that the
        device bus can transfer a maximum of 32 bits in a single transfer.
    bind : bool
        Tells the constructor whether or not to bind the subblocks as attributes
        of the Block instance.
    displayName : str
        Expanded name or display name of block.
    descr : str
        A string describing functionality, usage, and other relevant notes about
        the block.
    """
    _dynamicBinding = True
    _fmt="{displayName} ({mnemonic}, {port})"
    _alias = { 'port' : 'address' }
    _attrs = 'laneWidth', 'busWidth'

    def __init__(self, mnemonic, registers, port, byte_size, laneWidth, busWidth,
                 bind=True, displayName='', descr='', kwattrs={}):
        super(Port, self).__init__(mnemonic, registers, port, byte_size,
                                   bind=bind, displayName=displayName, descr=descr,
                                   kwattrs=kwattrs)
        self._laneWidth = laneWidth
        self._busWidth = busWidth

        for blk in self.walk():
            blk.root = self


class AccessPort(Port):
    # IDR = IDR # all access ports require an IDR

    def _read(self, address, size):
        self.root.apselect(self._port, (address&0xF0) >> 4)
        return self.root.read(1, address&0xF)

    def _write(self, address, value, size):
        self.root.apselect(self._port, (address&0xF0) >> 4)
        self.root.write(1, address&0xF, value)


class DebugPort(Port):

    def _read(self, address, size):
        return self.root.read(0, address)

    def _write(self, address, value, size):
        self.root.write(0, address, value)


class Register(blocks.IOBlock):
    _dynamicBinding = True
    _attrs = 'resetValue', 'resetMask'

    def __init__(self, mnemonic, fields, address, size, resetMask=0,
                 resetValue=None, access='read-write', bind=True, displayName='',
                 descr='', kwattrs={}):
        super(Register, self).__init__(mnemonic, fields, address, size,
                                       access=access, bind=bind,
                                       displayName=displayName, descr=descr,
                                       kwattrs=kwattrs)
        if resetMask == 0:
            resetValue = 0
        self._resetValue = utils.HexValue(resetValue, self._size)
        self._resetMask = utils.HexValue(resetMask, self._size)
        self._address = utils.HexValue(self._address)

        for field in self:
            field._mask = utils.HexValue(field._mask, self._size)

    def status(self):
        v = self.value

        headerstr = self._fmt.format(**self.attrs)
        substr = ''
        for blk in self:
            bitval = utils.HexValue((v&blk._mask) >> blk._offset, blk._size)
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
        return tuple(utils.HexValue((v&f._mask) >> f._offset, f._size) for f in self)
 

class BitField(blocks.IOBlock):
    _fmt = "{displayName} ({mnemonic}, {access}, {mask})"
    _macrokey = _attrs = 'mask'
    _alias = { 'offset' : "address", 'width' : "size" }

    def __new__(cls, mnemonic, offset, width, values=[], **kwargs):
        return super(BitField, cls).__new__(cls, mnemonic, values, offset, width, bind=False, **kwargs)

    def __init__(self, mnemonic, offset, width, values=[], access='read-write', displayName='', descr='', kwattrs={}):
        super(BitField, self).__init__(mnemonic, values, offset, width,
                                       access=access, bind=False,
                                       displayName=displayName, descr=descr,
                                       kwattrs=kwattrs)

        self._mask = utils.HexValue(((1 << self._size) - 1) << self._offset)

        for enumval in self:
            enumval._value = utils.HexValue(enumval._value, self._width)

    def _read(self):
        # return (self.root.read(self.parent._offset + self._offset, self._size) & self._mask) >> self._offset
        return (self.parent.value & self._mask) >> self._offset

    # notice that writing a bitfield requires a read of the register first
    def _write(self, value):
        # v = (self.root.read(self.parent._offset + self._offset, self._size) & self._mask) >> self._offset
        # self.root.write(self.parent._offset + self._offset, (value << self._offset) & self._mask, self._size)
        self.parent.value = (self.parent.value & ~self._mask) | ((value << self._offset) & self._mask)

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
        bitval = (regval & self._mask) & (other << self._offset)
        self.parent.value = (regval & ~self._mask) | (bitval & self._mask)
    def __ixor__(self, other):
        regval = self.parent.value 
        bitval = (regval & self._mask) ^ (other << self._offset)
        self.parent.value = (regval & ~self._mask) | (bitval & self._mask)
    def __ior__(self, other):
        regval = self.parent.value 
        bitval = (regval & self._mask) | (other << self._offset)
        self.parent.value = (regval & ~self._mask) | (bitval & self._mask)

    def __repr__(self):
        return "<{:s} '{:s}' in {:s} '{:s}' & {}>".format(self._typename, 
                                                          self._mnemonic,
                                                          self.parent._typename,
                                                          self.parent._mnemonic, 
                                                          self._mask)

class EnumeratedValue(blocks.LeafBlock):
    _fmt = "{mnemonic} (value={value})"
    _macrokey = _attrs = 'value'

    def __new__(cls, mnemonic, value, **kwargs):
        return super(EnumeratedValue, cls).__new__(cls, mnemonic, **kwargs)

    def __init__(self, mnemonic, value, displayName='', descr='', kwattrs={}):
        super(EnumeratedValue, self).__init__(mnemonic, displayName=displayName, descr=descr, kwattrs=kwattrs)
        self._value = utils.HexValue(value)

    def __repr__(self):
        return "<{:s} '{:s}' in {:s} '{:s}'>".format(self._typename,
                                                     self._mnemonic,
                                                     self.parent._typename,
                                                     self.parent._mnemonic)

