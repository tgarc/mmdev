from mmdev.dut import DUT
import sys

def gdb_regdefs(dut, out=sys.stdout):
    if not isinstance(dut, DUT):
        dut = DUT(dut)

    linefmt = "set $%s=0x%08x"
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
