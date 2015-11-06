from mmdev.dut import DUT
import sys

def gdb_regdefs(dut, out=sys.stdout):
    if not isinstance(dut, DUT):
        dut = DUT(dut)

    linefmt = "set $%s=0x%08x"
    for blkname, blk in dut.iteritems():
        print >> out, '#', blkname
        print >> out, '#', '='*30
        print >> out, linefmt % (blkname.lower(), blk.addr)
        print >> out
        for regname, reg in blk.iteritems():
            print >> out, '#', regname.lower()
            print >> out, '#', '-'*len(regname)
            print >> out, linefmt % (regname.lower(),reg.addr)
            for bfname, bits in reg.iteritems():
                print >> out, linefmt % (bfname.lower(), bits.mask)
            print >> out
