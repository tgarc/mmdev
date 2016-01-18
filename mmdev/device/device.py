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
        self._link = link.Link()

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

    def write(self, address, value, transfer_size=None):
        if transfer_size is None:
            transfer_size = self._width
        self._link.write(address, value, transfer_size=transfer_size)

    def read(self, address, transfer_size=None):
        if transfer_size is None:
            transfer_size = self._width
        return utils.HexValue(self._link.read(address, transfer_size=transfer_size), transfer_size)

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
