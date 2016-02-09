from mmdev import blocks
from mmdev import utils
import os


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
    lane_width : int
        Defines the number of data bits uniquely selected by each address. For
        example, a value of 8 denotes that the device is byte-addressable.
    bus_width : int
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

    def __init__(self, mnemonic, peripherals, lane_width, bus_width, cpu=None, vendor='Unknown Vendor', **kwargs):
        blocks.DeviceBlock.__init__(self, mnemonic, peripherals, lane_width, bus_width, **kwargs)

        self.cpu = cpu
        self._vendor = vendor
        
        self._map = {}
        for blk in self.walk():
            key = blk._mnemonic
            if key in self._map:
                if not isinstance(self._map[key], list):
                    self._map[key] = [self._map[key]]
                self._map[key].append(blk)
            else:
                self._map[key] = blk

        # purely for readability, set the address width for peripherals and
        # registers
        for blk in self.walk(d=2):
            blk._macrovalue = utils.HexValue(blk._macrovalue, self._bus_width)

        for blk in self.walk():
            blk.root = self

        self.link = None

    def connect(self, link=None):
        assert link is not None or self.link is not None, "No link has yet been specified."
        if link is not None:
            self.link = link
        self.link.connect()

    def disconnect(self):
        self.link.disconnect()

    def reset(self):
        self.link.disconnect()
        self.link.connect()

    # defer to a DeviceLink to read/write memory
    def _write(self, address, value, accessSize=None):
        if accessSize is None:
            accessSize = self._bus_width
        self.link.memWrite(address, value, accessSize)
    write = _write
    
    def _read(self, address, accessSize=None):
        if accessSize is None:
            accessSize = self._bus_width
        return utils.HexValue(self.link.memRead(address, accessSize), accessSize)
    read = _read

    # def read(self, address, bitlen):
    #     data = []

    #     # First align the address
    #     modbits = address % self._lane_width
    #     address -= modbits
    #     bitlen -= modbits
    #     xferlen = align*bool(modbits)
    #     data += self.link.memRead(address, xferlen)
    #     address += xferlen

    #     # Read the rest of the data in the largest aligned transfers possible
    #     xferwidth = self._bus_width
    #     while bitlen:
    #         xferlen = xferwidth * (bitlen // xferwidth)
    #         data += self.link.memRead(address, xferlen)
    #         bitlen -= xferlen
    #         address += xferlen
    #         xferwidth >>= 1

    #     return data

    # def write(self, address, data, bitlen):
    #     # First align the address
    #     modbits = address % self._lane_width
    #     address -= modbits
    #     bitlen -= modbits
    #     xferlen = align*bool(modbits)
    #     self.link.memWrite(address, data.pop(), xferlen)
    #     address += xferlen

    #     # Read the rest of the data in the largest aligned transfers possible
    #     xferwidth = self._bus_width
    #     while bitlen:
    #         xferlen = xferwidth * (bitlen // xferwidth)
    #         self.link.memWrite(address, data.pop(), xferlen)
    #         bitlen -= xferlen
    #         address += xferlen
    #         xferwidth >>= 1

    #     return data

    def set_format(self, blocktype, fmt):
        for blk in self.walk(d=1, l=_levels[blocktype.lower()]):
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

    @staticmethod
    def from_devfile(devfile, file_format=None, raiseErr=True):
        """
        Parse a device file using the given file format. If file format is not
        given, file extension will be used.

        Supported Formats:
            + 'json' : JSON
            + 'svd'  : CMSIS-SVD
        """
        from mmdev import parsers

        if file_format is None:
            file_format = os.path.splitext(devfile)[1][1:]
        try:
            parse = parsers.PARSERS[file_format]
        except KeyError:
            raise KeyError("Extension '%s' not recognized" % file_format)
        return parse(devfile, raiseErr=raiseErr)

    def to_devfile(self, file_format):
        """
        Parse a device file using the given file format. If file format is not
        given, file extension will be used.

        Supported Formats:
            + 'json' : JSON
        """
        from mmdev import dumpers
        try:
            dump = dumpers.DUMPERS[file_format]
        except KeyError:
            raise KeyError("File format '%s' not recognized" % file_format)
        return dump(self)
