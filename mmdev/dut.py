from mmdev.blocks import RootBlockNode
from collections import OrderedDict
from itertools import imap
import json


class DUT(RootBlockNode):
    _fmt="{name:s} ({mnemonic:s}, {width:d}-bit, vendor={vendor:s})"

    def __init__(self, mnemonic, fullname='', descr='', width=32, vendor=''):
        super(DUT, self).__init__(mnemonic, fullname=fullname, descr=descr)
        self.width = width
        self.vendor = vendor or 'Unknown'
        self._fields += ['width', 'vendor']
        
    def _sort(self):
        self._nodes = sorted(self._nodes, key=lambda blk: blk.addr, reverse=True)
        for blkd in self._nodes:
            blkd._nodes = sorted(blkd._nodes, key=lambda blk: blk.addr, reverse=True)
            for regd in blkd._nodes:
                regd._nodes = sorted(regd._nodes, key=lambda blk: blk.mask, reverse=True)

    def to_gdbinit(self):
        blkfmt = "set $%s = (unsigned long *) 0x%08x"
        bitfmt = "set $%s = (unsigned long) 0x%08x"    
        batchstr = ''
        for blkname, blk in self.iteritems():
            batchstr += '#', blkname, blk.name
            batchstr += '#', '='*58
            batchstr += blkfmt % (blkname.lower(), blk.addr)
            batchstr += '\n'
            for regname, reg in blk.iteritems():
                batchstr += '#', regname.lower(), reg.name.lower()
                batchstr += '#', '-'*(len(regname)+len(reg.name)+1)
                batchstr += blkfmt % (regname.lower(),reg.addr)
                for bfname, bits in reg.iteritems():
                    batchstr += bitfmt % (bfname.lower(), bits.mask)
                batchstr += '\n'
        return batchstr
    
    def to_json(self, **kwargs):
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
            blkd['addr'] = "0x%08x" % blk.addr
            blknames.append(blkname)

            regnames = []
            for regname, reg in blk.iteritems():
                regd = OrderedDict()
                regd['mnemonic'] = reg.mnemonic
                regd['name'] = reg.name
                regd['descr'] = reg.descr
                regd['addr'] = "0x%08x" % reg.addr
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

        return json.dumps(dev, **kwargs)

    @staticmethod
    def from_pyconfig(devfile):
        """
        pyconfig DUT definition files are required to have three
        dict-like objects:

        BLK_MAP, REG_MAP
        ----------------
        Maps a block/register mnemonic to its address for all hardware
        blocks/registers on device

        BIT_MAP
        -------
        Maps a bitfield mnemonic to a bitmask for all registers on device


        These definition files also have some optional fields:

        mnemonic
        --------
        Shorthand name for DUT (e.g. armv7m). Defaults to definition file
        name.

        name
        --------
        Full name of DUT. Defaults to "DUT".

        BLK_NAME, REG_NAME, BIT_NAME
        ------------------
        Maps a block/register/bitfield mnemonic to its full name (e.g., ITM :
        Instrumentation Trace Macrocell).

        BLK_DESCR, REG_DESCR, BIT_DESCR
        -------------------------------
        Maps a block/register/bitfield mnemonic to a description.
        """
        if isinstance(devfile, basestring):
            try:
                devfile = __import__('mmdev.'+devfile, fromlist=[''])
            except ImportError:
                import imp, os
                devfile = imp.load_source(os.path.basename(devfile), devfile)

        name = getattr(devfile, 'name', 'DUT')
        mnem = getattr(devfile, 'mnemonic', devfile.__name__)
        descr = getattr(devfile, 'descr', '')
        width = getattr(devfile, 'width', 32)
        vendor = getattr(devfile, 'vendor', '')        

        dut = DUT(mnem, fullname=name, descr=descr, width=width, vendor=vendor)
        for blkname, blkaddr in devfile.BLK_MAP.iteritems():
            pph = dut._create_peripheral(blkname, blkaddr,
                                         fullname=devfile.BLK_NAME.get(blkname,'Block'),
                                         descr=devfile.BLK_DESCR.get(blkname,''))
            for regname, regaddr in devfile.REG_MAP.get(blkname,{}).iteritems():
                reg = pph._create_register(regname, regaddr,
                                           fullname=devfile.REG_NAME.get(regname,'Register'),
                                           descr=devfile.REG_DESCR.get(regname,''))
                for bitname, bitmask in devfile.BIT_MAP.get(regname,{}).iteritems():
                    reg._create_bitfield(bitname, bitmask,
                                         fullname=devfile.BIT_NAME.get(bitname,'BitField'),
                                         descr=devfile.BIT_DESCR.get(regname,{}).get(bitname,''))
        dut._sort()
        return dut


    @staticmethod
    def from_json(devfile, **kwargs):
        if isinstance(devfile, basestring):
            import re
            fname = re.sub('\..*', '', devfile)
            with open(devfile) as fh:
                devfile = json.load(fh, **kwargs)
        else:
            fname = fh.name
            devfile = json.load(fh, **kwargs)

        name = devfile.get('name', 'DUT')
        mnem = devfile['mnemonic'] if devfile.get('mnemonic', '') else fname
        descr = devfile.get('descr', '')
        width = devfile.get('width',32)
        vendor = devfile.get('vendor', '')

        dut = DUT(mnem, fullname=name, descr=descr, width=width, vendor=vendor)
        for blkname, blkd in devfile['blocks'].iteritems():
            try:
                blkaddr = int(blkd['addr'])
            except ValueError:
                blkaddr = int(blkd['addr'], 16)
            pph = dut._create_peripheral(blkname, blkaddr,
                                         fullname=blkd.get('name','Block'),
                                         descr=blkd.get('descr',''))
            for regd in imap(devfile['registers'].get, blkd['registers']):
                try:
                    regaddr = int(regd['addr'])
                except ValueError:
                    regaddr = int(regd['addr'], 16)
                reg = pph._create_register(regd['mnemonic'], regaddr,
                                           fullname=regd.get('name','Register'),
                                           descr=regd.get('descr',''))
                for bitsd in imap(devfile['bitfields'].get, regd['bitfields']):
                    try:
                        bitmask = int(bitsd['mask'])
                    except ValueError:
                        bitmask = int(bitsd['mask'], 16)
                    reg._create_bitfield(bitsd['mnemonic'], bitmask,
                                         fullname=bitsd.get('name','BitField'),
                                         descr=bitsd.get('descr',''))
        dut._sort()
        return dut
