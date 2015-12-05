import ctypes as _ctypes
from collections import OrderedDict as _OrderedDict
from mmdev.blocks import Block, DescriptorBlock, MemoryMappedBlock
from mmdev.link import Link

_bruijn32lookup = [0, 1, 28, 2, 29, 14, 24, 3, 30, 22, 20, 15, 25, 17, 4, 8, 
                   31, 27, 13, 23, 21, 19, 16, 7, 26, 12, 18, 6, 11, 5, 10, 9]


class Device(Block):
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
        dev = _OrderedDict()
        dev['mnemonic'] = self.mnemonic
        dev['name'] = self.name
        dev['descr'] = self.descr

        blocks = _OrderedDict()
        registers = _OrderedDict()
        bitfields = _OrderedDict()

        blknames = []
        for blkname, blk in self.iteritems():
            blkd = _OrderedDict()
            blkd['mnemonic'] = blk.mnemonic
            blkd['name'] = blk.name
            blkd['descr'] = blk.descr
            blkd['address'] = "0x%08x" % blk.address
            blknames.append(blkname)

            regnames = []
            for regname, reg in blk.iteritems():
                regd = _OrderedDict()
                regd['mnemonic'] = reg.mnemonic
                regd['name'] = reg.name
                regd['descr'] = reg.descr
                regd['address'] = "0x%08x" % reg.address
                regnames.append(regname)

                bitnames = []
                for bfname, bits in reg.iteritems():
                    bitsd = _OrderedDict()
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
        from mmdev import parsers
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


def Peripheral(mnemonic, address, subblocks, fullname='', descr=''):
    class Peripheral(MemoryMappedBlock):
        pass
    Peripheral._attach_subblocks(subblocks)
    return Peripheral(mnemonic, address, subblocks, fullname=fullname, descr=descr, dynamic=True)


def Register(mnemonic, address, subblocks, fullname='', descr=''):
    class Register(MemoryMappedBlock, DescriptorBlock):
        def _read(self):
            return self.root.read(self.address)
        def _write(self, value):
            return self.root.write(self.address, value)
    Register._attach_subblocks(subblocks)
    return Register(mnemonic, address, subblocks, fullname=fullname, descr=descr, dynamic=True)


class BitField(DescriptorBlock):
    _fmt="{name:s} ({mnemonic:s}, 0x{mask:08X})"
    _subfmt="0x{mask:08X} {mnemonic:s}"

    def __init__(self, mnemonic, mask, fullname='', descr=''):
        # calculate the bit offset from the mask using a debruijn hash function
        # use ctypes to truncate the result to a uint32
        # TODO: change to a 64 bit version of the lookup
        super(BitField, self).__init__(mnemonic, fullname=fullname, descr=descr)
        self.mask = mask
        self.address = _bruijn32lookup[_ctypes.c_uint32((mask & -mask) * 0x077cb531).value >> 27]
        self._fields += ['mask', 'address']

    def _read(self):
        return (self.parent.value & self.mask) >> self.address

    def _write(self, value):
        regvalue = (self.parent.value & ~self.mask) | (value << self.address)
        self.parent.value = regvalue

    def __repr__(self):
        return "<{:s} '{:s}' in Register '{:s}' & 0x{:08x}>".format(self.typename, 
                                                                    self.mnemonic, 
                                                                    self.parent.mnemonic, 
                                                                    self.mask)
