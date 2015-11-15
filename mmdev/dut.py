import sys
from mmdev.block import BlockNode, MemoryMappedBlock

class DUT(BlockNode):

    def __init__(self, devfile):
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

        if isinstance(devfile, basestring):
            if devfile.endswith('.py'): # if this is a file path, import it first
                import imp, os
                devfile = imp.load_source(os.path.basename(devfile), devfile)
            else:
                devfile = __import__('mmdev.'+devfile, fromlist=[''])

        name = getattr(devfile, 'name', 'DUT')
        mnem = getattr(devfile, 'mnemonic', devfile.__name__)
        descr = getattr(devfile, 'descr', '')

        super(DUT, self).__init__(mnem, parent=None, fullname=name, descr=descr)
        getval = lambda x: x[1]
        for blkname, blkaddr in sorted(devfile.BLK_MAP.iteritems(),key=getval, reverse=True):
            blk = self._create_subblock(MemoryMappedBlock, blkname, blkaddr,
                                        fullname=devfile.BLK_NAME.get(blkname,'Block'),
                                        descr=devfile.BLK_DESCR.get(blkname,''))
            for regname, regaddr in sorted(devfile.REG_MAP.get(blkname,{}).iteritems(),key=getval, reverse=True):
                reg = blk._create_register(regname, regaddr,
                                           fullname=devfile.REG_NAME.get(regname,'Register'),
                                           descr=devfile.REG_DESCR.get(regname,''))
                for bitname, bitmask in sorted(devfile.BIT_MAP.get(regname,{}).iteritems(),key=getval, reverse=True):
                    reg._create_bitfield(bitname, bitmask,
                                         fullname=devfile.BIT_NAME.get(bitname,'BitField'),
                                         descr=devfile.BIT_DESCR.get(regname,{}).get(bitname,''))

    def to_gdbinit(self, out=sys.stdout):
        blkfmt = "set $%s = (unsigned long *) 0x%08x"
        bitfmt = "set $%s = (unsigned long) 0x%08x"    
        for blkname, blk in self.iteritems():
            print >> out, '#', blkname, blk.name
            print >> out, '#', '='*58
            print >> out, blkfmt % (blkname.lower(), blk.addr)
            print >> out
            for regname, reg in blk.iteritems():
                print >> out, '#', regname.lower(), reg.name.lower()
                print >> out, '#', '-'*(len(regname)+len(reg.name)+1)
                print >> out, blkfmt % (regname.lower(),reg.addr)
                for bfname, bits in reg.iteritems():
                    print >> out, bitfmt % (bfname.lower(), bits.mask)
                print >> out
