from mmdev import blocks
from mmdev import link
from mmdev import utils


_levels = {'device': 0,
           'peripheral': 1,
           'register': 2,
           'bitfield': 3,
           'enumeratedvalue': 4}


class Device(blocks.RootBlock):
    _fmt = "{name} ({mnemonic}, {vendor})"
    _attrs = 'vendor'

    def __new__(cls, mnemonic, addressBits, width, peripherals, cpu=None, vendor='Unknown Vendor', **kwargs):
        return super(Device, cls).__new__(cls, mnemonic, addressBits, width, peripherals, **kwargs)

    def __init__(self, mnemonic, addressBits, width, peripherals, cpu=None, vendor='Unknown Vendor', **kwargs):
        super(Device, self).__init__(mnemonic, addressBits, width, peripherals, **kwargs)

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

        self._link = link.MockLink()
            
    def unlink(self):
        self._link.disconnect()
        self._link = link.MockLink()

    def link(self, link):
        self._link.disconnect()
        self._link = link
        self._link.connect()

    def write(self, address, value, accessSize=None):
        if accessSize is None:
            accessSize = self._width
        self._link.memWrite(address, value, accessSize=accessSize)

    def read(self, address, accessSize=None):
        if accessSize is None:
            accessSize = self._width
        return utils.HexValue(self._link.memRead(address, accessSize=accessSize), accessSize)

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
