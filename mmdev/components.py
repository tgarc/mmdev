import blocks
from mmdev import utils

_levels = {'device': 0,
           'peripheral': 1,
           'register': 2,
           'bitfield': 3,
           'enumeratedvalue': 4}


class CPU(blocks.LeafBlock):
    _attrs = 'revision', 'endian', 'mpuPresent', 'fpuPresent'

    def __init__(self, mnemonic, revision, endian, mpuPresent, fpuPresent, displayName='', description='', kwattrs={}):
        super(CPU, self).__init__(mnemonic, description=description, kwattrs=kwattrs)
        self.revision = revision
        self.endian = endian
        self.mpuPresent = mpuPresent
        self.fpuPresent = fpuPresent


class Device(blocks.DeviceBlock):
    """\
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
    description : str
        A string describing functionality, usage, and other relevant notes about
        the block.
    """ 
    _attrs = 'vendor'


    def __init__(self, mnemonic, subblocks, laneWidth, busWidth, cpu=None,
                 bind=True, displayName='', description='', vendor='', kwattrs={}):
        super(Device, self).__init__(mnemonic, subblocks, laneWidth, busWidth,
                                     bind=bind, displayName=displayName,
                                     description=description, kwattrs=kwattrs)
        self.vendor = vendor
        self.cpu = cpu

        # purely for readability, set the address width for peripherals and
        # registers
        for blk in self.walk(d=2):
            blk._macrovalue = utils.HexValue(blk._macrovalue, self.busWidth)

        # register all the nodes into a map for searching
        self._map = {}
        for blk in self.walk():
            blk.root = self
            key = blk.mnemonic
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
            raise ValueError("%s was not found" % key)

    def findall(self, key):
        res = self._map.get(key)
        if res is None:
            return ()
        return tuple(res) if isinstance(res, list) else (res,)


class Peripheral(blocks.Block):
    """\
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
    description : str
        A string describing functionality, usage, and other relevant notes about
        the block.
    """
    _dynamicBinding = True
    _macrokey = 'address'
    _attrs = 'address', 'size'

    def __init__(self, mnemonic, registers, address, size, bind=True,
                 displayName='', description='', kwattrs={}):
        super(Peripheral, self).__init__(mnemonic, registers,
                                         displayName=displayName,
                                         description=description,
                                         kwattrs=kwattrs)

        self.address = utils.HexValue(address)
        self.size = utils.HexValue(size)

        # purely for readability, set the data width for registers
        for reg in self:
            reg.address = utils.HexValue(reg.address, int.bit_length(self.size-1))
            
    def __repr__(self):
        return "<{:s} '{:s}' @ {}>".format(self._typename, self.mnemonic, self.address)

class Port(blocks.DeviceBlock):
    """\
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
    description : str
        A string describing functionality, usage, and other relevant notes about
        the block.
    """
    _dynamicBinding = True
    _fmt = "{displayName} ({mnemonic}, {port})"
    _attrs = 'port', 'size'
    _macrokey = 'port'

    def __init__(self, mnemonic, registers, port, byte_size, laneWidth, busWidth,
                 bind=True, displayName='', description='', kwattrs={}):
        super(Port, self).__init__(mnemonic, registers, laneWidth, busWidth,
                                   bind=bind, displayName=displayName,
                                   description=description, kwattrs=kwattrs)
        self.port = utils.HexValue(port)
        self.size = utils.HexValue(byte_size)

        for blk in self.walk():
            blk.root = self

        # purely for readability, set the data width for registers
        for reg in self:
            reg.address = utils.HexValue(reg.address, int.bit_length(self.size-1))


    def __repr__(self):
        return "<{:s} '{:s}' @ {}>".format(self._typename, self.mnemonic, self.port)
                                           


class AccessPort(Port):
    # IDR = IDR # all access ports require an IDR

    def _read(self, address, size):
        self.root.apselect(self.port, (address&0xF0) >> 4)
        return self.root._read(1, address&0xF)

    def _write(self, address, value, size):
        self.root.apselect(self.port, (address&0xF0) >> 4)
        self.root._write(1, address&0xF, value)


class DebugPort(Port):

    def _read(self, address, size):
        return self.root._read(0, address)

    def _write(self, address, value, size):
        self.root._write(0, address, value)


class Register(blocks.IOBlock):
    """\
    Models a generic hardware register.

    Parameters
    ----------
    mnemonic : str
        Shorthand or abbreviated name of block.
    fields : list-like
        All the bitfields of this block.
    address : int
        The absolute address of this block.
    size : int
        Size of register in bits.
    access : {'read-only','write-only', 'read-write'}
        Describes the read/write permissions for this block.
        'read-only': 
            read access is permitted. Write operations will be ignored.
        'write-only': 
            write access is permitted. Read operations on this block will always return 0.
        'read-write': 
            both read and write accesses are permitted.
    bind : bool
        Tells the constructor whether or not to bind subblocks as attributes of
        the Block instance.
    displayName : str
        Expanded name or display name of block.
    description : str
        A string describing functionality, usage, and other relevant notes about
        the block.
    """
    _dynamicBinding = True
    _macrokey = 'address'
    _attrs = 'resetValue', 'resetMask', 'size', 'address'
    _fmt="{displayName} ({mnemonic}, {address})"

    def __init__(self, mnemonic, fields, address, size, access='read-write',
                 resetMask=0, resetValue=None, bind=True, displayName='',
                 description='', kwattrs={}):
        super(Register, self).__init__(mnemonic, fields, size, access=access,
                                       bind=bind, displayName=displayName,
                                       description=description, kwattrs=kwattrs)
        if resetMask == 0:
            resetValue = 0

        self.resetValue = utils.HexValue(resetValue, self.size)
        self.resetMask = utils.HexValue(resetMask, self.size)
        self.address = utils.HexValue(address)

        for field in self:
            field.mask = utils.HexValue(field.mask, self.size)

    def _read(self):
        return self.root._read(self.address, self.size)

    def _write(self, value):
        return self.root._write(self.address, value, self.size)

    def status(self):
        v = self.value

        headerstr = self._fmt.format(**self.attrs)
        substr = ''
        for blk in self:
            bitval = utils.HexValue((v&blk.mask) >> blk.offset, blk.size)
            substr += "\n\t%s %s %s" % (blk.mask, blk.mnemonic, bitval)

        print headerstr + substr if substr else headerstr

    def pack(self, *args, **kwargs):
        nodesdict = dict(self.items())
        nodes = list((self._nodes[idx], v) for idx, v in enumerate(args)) 
        nodes+= [(nodesdict[k.upper()], v) for k, v in kwargs.items()]

        v = self.value
        for f, a in nodes:
            v = (v & ~f.mask) | ((a << f.address) & f.mask)
        self.value = v

    def unpack(self):
        v = self.value
        return tuple(utils.HexValue((v&f.mask) >> f.offset, f.size) for f in self)

    def __repr__(self):
        return "<{:s} '{:s}' @ {}>".format(self._typename, self.mnemonic, self.address)
                                           


class BitField(blocks.IOBlock):
    """\
    Models a generic bit field.

    Parameters
    ----------
    mnemonic : str
        Shorthand or abbreviated name of block.
    values : list-like
        A list of the defined EnumeratedValues.
    offset : int
        The bit offset of this field.
    size : int
        Size of field in bits.
    access : {'read-only','write-only', 'read-write'}
        Describes the read/write permissions for this block.
        'read-only': 
            read access is permitted. Write operations will be ignored.
        'write-only': 
            write access is permitted. Read operations on this block will always return 0.
        'read-write': 
            both read and write accesses are permitted.
    bind : bool
        Tells the constructor whether or not to bind subblocks as attributes of
        the Block instance.
    displayName : str
        Expanded name or display name of block.
    description : str
        A string describing functionality, usage, and other relevant notes about
        the block.
    """

    _fmt = "{displayName} ({mnemonic}, {access}, {mask})"
    _macrokey = 'mask'
    _attrs = 'mask', 'size', 'offset'

    def __new__(cls, mnemonic, offset, size, values=[], **kwargs):
        kwargs['bind'] = False
        return super(BitField, cls).__new__(cls, mnemonic, values, **kwargs)

    def __init__(self, mnemonic, offset, size, values=[], access='read-write',
                 displayName='', description='', kwattrs={}):
        super(BitField, self).__init__(mnemonic, values, size, access=access,
                                       bind=False, displayName=displayName,
                                       description=description, kwattrs=kwattrs)
        self.offset = offset
        self.size = size
        self.mask = utils.HexValue(((1 << self.size) - 1) << self.offset)

        for enumval in self:
            enumval.value = utils.HexValue(enumval.value, self.size)

    def _read(self):
        # return (self.root.read(self.parent.offset + self.offset, self.size) & self.mask) >> self.offset
        return (self.parent.value & self.mask) >> self.offset

    # notice that writing a bitfield requires a read of the register first
    def _write(self, value):
        # v = (self.root.read(self.parent.offset + self.offset, self.size) & self.mask) >> self.offset
        # self.root.write(self.parent.offset + self.offset, (value << self.offset) & self.mask, self.size)
        self.parent.value = (self.parent.value & ~self.mask) | ((value << self.offset) & self.mask)

    def __ilshift__(self, other):
        regval = self.parent.value 
        bitval = (regval & self.mask) << other
        self.parent.value = (regval & ~self.mask) | (bitval & self.mask)
    def __irshift__(self, other):
        regval = self.parent.value 
        bitval = (regval & self.mask) >> other
        self.parent.value = (regval & ~self.mask) | (bitval & self.mask)
    def __iand__(self, other):
        regval = self.parent.value 
        bitval = (regval & self.mask) & (other << self.offset)
        self.parent.value = (regval & ~self.mask) | (bitval & self.mask)
    def __ixor__(self, other):
        regval = self.parent.value 
        bitval = (regval & self.mask) ^ (other << self.offset)
        self.parent.value = (regval & ~self.mask) | (bitval & self.mask)
    def __ior__(self, other):
        regval = self.parent.value 
        bitval = (regval & self.mask) | (other << self.offset)
        self.parent.value = (regval & ~self.mask) | (bitval & self.mask)

    def __repr__(self):
        return "<{:s} '{:s}' & {}>".format(self._typename, self.mnemonic, self.mask)
                                           

class EnumeratedValue(blocks.LeafBlock):
    _fmt = "{mnemonic} (value={value})"
    _macrokey = _attrs = 'value'

    def __new__(cls, mnemonic, value, **kwargs):
        return super(EnumeratedValue, cls).__new__(cls, mnemonic, **kwargs)

    def __init__(self, mnemonic, value, description='', kwattrs={}):
        super(EnumeratedValue, self).__init__(mnemonic, description=description, kwattrs=kwattrs)
        self.value = utils.HexValue(value)
