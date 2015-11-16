import sys
import re
from mmdev.block import BlockNode, MemoryMappedBlock
from collections import OrderedDict
import json
from itertools import imap




class DUT(BlockNode):
    """
    Create a DUT device from a device definition file.


    DUT definition files are required to have three dict-like objects:

    BLK_MAP, REG_MAP
    ----------------
    Maps a block/register mnemonic to its address for all hardware
    blocks/registers on device

    BIT_MAP
    -------
    Maps a bitfield mnemonic to a bitmask for all registers on device


    Definition files also have some optional fields:

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
    @staticmethod
    def from_pyconfig(devfile):
        if isinstance(devfile, basestring):
            try:
                devfile = __import__('mmdev.'+devfile, fromlist=[''])
            except ImportError:
                import imp, os
                devfile = imp.load_source(os.path.basename(devfile), devfile)

        name = getattr(devfile, 'name', 'DUT')
        mnem = getattr(devfile, 'mnemonic', devfile.__name__)
        descr = getattr(devfile, 'descr', '')

        dut = DUT(mnem, parent=None, fullname=name, descr=descr)
        for blkname, blkaddr in devfile.BLK_MAP.iteritems():
            blk = dut._create_subblock(MemoryMappedBlock, blkname, blkaddr,
                                        fullname=devfile.BLK_NAME.get(blkname,'Block'),
                                        descr=devfile.BLK_DESCR.get(blkname,''))
            for regname, regaddr in devfile.REG_MAP.get(blkname,{}).iteritems():
                reg = blk._create_register(regname, regaddr,
                                           fullname=devfile.REG_NAME.get(regname,'Register'),
                                           descr=devfile.REG_DESCR.get(regname,''))
                for bitname, bitmask in devfile.BIT_MAP.get(regname,{}).iteritems():
                    reg._create_bitfield(bitname, bitmask,
                                         fullname=devfile.BIT_NAME.get(bitname,'BitField'),
                                         descr=devfile.BIT_DESCR.get(regname,{}).get(bitname,''))
        dut._sort()
        return dut

    def _sort(self):
        self._blocks = sorted(self._blocks, key=lambda blk: blk.addr, reverse=True)
        for blkd in self._blocks:
            blkd._blocks = sorted(blkd._blocks, key=lambda blk: blk.addr, reverse=True)
            for regd in blkd._blocks:
                regd._blocks = sorted(regd._blocks, key=lambda blk: blk.mask, reverse=True)

    @staticmethod
    def from_json(devfile, **kwargs):
        if isinstance(devfile, basestring):
            fname = re.sub('\..*', '', devfile)
            with open(devfile) as fh:
                devfile = json.load(fh, **kwargs)
        else:
            fname = fh.name
            devfile = json.load(fh, **kwargs)

        name = devfile.get('name', 'DUT')
        mnem = devfile['mnemonic'] if devfile.get('mnemonic', '') else fname
        descr = devfile.get('descr', '')

        dut = DUT(mnem, parent=None, fullname=name, descr=descr)
        for blkname, blkd in devfile['blocks'].iteritems():
            try:
                blkaddr = int(blkd['addr'])
            except ValueError:
                blkaddr = int(blkd['addr'], 16)
            blk = dut._create_subblock(MemoryMappedBlock, blkname, blkaddr,
                                        fullname=blkd.get('name','Block'),
                                        descr=blkd.get('descr',''))
            for regd in imap(devfile['registers'].get, blkd['registers']):
                try:
                    regaddr = int(regd['addr'])
                except ValueError:
                    regaddr = int(regd['addr'], 16)
                reg = blk._create_register(regd['mnemonic'], regaddr,
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
