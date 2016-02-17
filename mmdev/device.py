from mmdev import blocks, utils


_levels = {'device': 0,
           'peripheral': 1,
           'register': 2,
           'bitfield': 3,
           'enumeratedvalue': 4}


class Device(blocks.DeviceBlock):
    """
    Models an SVD-like device that defines a single memory address space and its
    data bus.

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
    displayname : str
        Expanded name or display name of block.
    descr : str
        A string describing functionality, usage, and other relevant notes about
        the block.
    """
    _fmt = "{displayName} ({mnemonic}, {vendor})"
    _attrs = 'vendor'

    def __init__(self, mnemonic, peripherals, laneWidth, busWidth, cpu=None, vendor='Unknown Vendor', **kwargs):
        blocks.DeviceBlock.__init__(self, mnemonic, peripherals, laneWidth, busWidth, **kwargs)

        self.cpu = cpu
        self._vendor = vendor
        
        # purely for readability, set the address width for peripherals and
        # registers
        for blk in self.walk(d=2):
            blk._macrovalue = utils.HexValue(blk._macrovalue, self._busWidth)

        for blk in self.walk():
            blk.root = self

    def set_format(self, blocktype, fmt):
        for blk in self.walk(d=1, l=_levels[blocktype.lower()]):
            blk._fmt = fmt
