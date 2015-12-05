from collections import OrderedDict
import parsers
import blocks
from link import Link


class Device(blocks.Block):
    _fmt="{name:s} ({mnemonic:s}, {width:d}-bit, vendor={vendor:s})"

    def __init__(self, mnemonic, blocks, fullname='', descr='', width=32, vendor=''):
        super(Device, self).__init__(mnemonic, blocks, fullname=fullname, descr=descr)
        self._link = Link()

        self.width = width
        self.vendor = vendor or 'Unknown'
        self._fields += ['width', 'vendor']

        self._map = {}
        for blk in self.walk():
            key = blk.mnemonic.lower()
            if key in self._map:
                if not isinstance(self._map[key], list):
                    self._map[key] = [self._map[key]]
                self._map[key].append(blk)
            else:
                self._map[key] = blk

        for blk in self.walk(3, root=True):
            blk._sort(key=lambda blk: blk.address)

    def find(self, key):
        return self._map.get(key.lower())

    def write(self, address, value):
        self._link.write(address, value)

    def read(self, address):
        return self._link.read(address)

    def to_gdbinit(self):
        import StringIO

        fh = StringIO.StringIO()
        blkfmt = "set $%s = (unsigned long *) 0x%08x"
        bitfmt = "set $%s = (unsigned long) 0x%08x"    
        for blkname, blk in self.iteritems():
            print >> fh, '#', blkname, blk.name
            print >> fh, '#', '='*58
            print >> fh, blkfmt % (blkname.lower(), blk.address)
            print >> fh
            for regname, reg in blk.iteritems():
                print >> fh, '#', regname.lower(), reg.name.lower()
                print >> fh, '#', '-'*(len(regname)+len(reg.name)+1)
                print >> fh, blkfmt % (regname.lower(),reg.address)
                for bfname, bits in reg.iteritems():
                    print >> fh, bitfmt % (bfname.lower(), bits.mask)
                print >> fh
        gdbinit = fh.getvalue()
        fh.close()

        return gdbinit

    def to_json(self, **kwargs):
        return json.dumps(self.to_ordered_dict(), **kwargs)

    def to_ordered_dict(self):
        dev = OrderedDict()
        dev['mnemonic'] = self.mnemonic
        dev['name'] = self.name
        dev['descr'] = self.descr

        blocks = OrderedDict()
        registers = OrderedDict()
        bitfields = OrderedDict()

        blknames = []
        for blkname, blk in self.iteritems():
            blkd = OrderedDict()
            blkd['mnemonic'] = blk.mnemonic
            blkd['name'] = blk.name
            blkd['descr'] = blk.descr
            blkd['address'] = "0x%08x" % blk.address
            blknames.append(blkname)

            regnames = []
            for regname, reg in blk.iteritems():
                regd = OrderedDict()
                regd['mnemonic'] = reg.mnemonic
                regd['name'] = reg.name
                regd['descr'] = reg.descr
                regd['address'] = "0x%08x" % reg.address
                regnames.append(regname)

                bitnames = []
                for bfname, bits in reg.iteritems():
                    bitsd = OrderedDict()
                    bitsd['mnemonic'] = bits.mnemonic
                    bitsd['name'] = bits.name
                    bitsd['descr'] = bits.descr
                    bitsd['mask'] = "0x%08x" % bits.mask
                    bitnames.append(bfname)

                    bitfields[bfname] = bitsd
                regd['bitfields'] = bitnames
                registers[regname] = regd
            blkd['registers'] = regnames
            blocks[blkname] = blkd

        dev['blocks'] = blocks
        dev['registers'] = registers
        dev['bitfields'] = bitfields

        return dev

    @staticmethod
    def from_devfile(devfile, file_format):
        """
        Parse a device file using the given file format
        """
        parse = parsers.PARSERS[file_format]
        return parse(devfile)

    @classmethod
    def from_json(cls, devfile):
        return cls.from_devfile(devfile, 'json')

    @classmethod
    def from_pycfg(cls, devfile):
        return cls.from_devfile(devfile, 'pycfg')

    @classmethod
    def from_svd(cls, devfile):
        return cls.from_devfile(devfile, 'svd')
