#!/usr/bin/env python
from mmdev.dut import Block, DUT
import sys

def gdb_regdefs(dut, out=sys.stdout):
    if not isinstance(dut, Block):
        dut = DUT(dut)

    linefmt = "set $%s = (unsigned long *) 0x%08x"
    for blkname, blk in dut.iteritems():
        print >> out, '#', blkname, blk.name
        print >> out, '#', '='*58
        print >> out, linefmt % (blkname.lower(), blk.addr)
        print >> out
        for regname, reg in blk.iteritems():
            print >> out, '#', regname.lower(), reg.name.lower()
            print >> out, '#', '-'*(len(regname)+len(reg.name)+1)
            print >> out, linefmt % (regname.lower(),reg.addr)
            for bfname, bits in reg.iteritems():
                print >> out, linefmt % (bfname.lower(), bits.mask)
            print >> out

if __name__ == "__main__":
    gdb_regdefs(sys.argv[1], sys.argv[2] if len(sys.argv)>2 else sys.stdout)
