from mmdev.dut import DUT
import sys

def gdb_regdefs(regdef, out=sys.stdout):
    if not isinstance(regdef, DUT):
        regdef = DUT(regdef)

    linefmt = "set $%s=0x%08x"
    for blkname, blkaddr in regdef.get_blocks():
        print >> out, linefmt % (blkname.lower(),blkaddr)
        for regname, regaddr in getattr(regdef, blkname.lower()).get_regs():
            print >> out, linefmt % (regname.lower(),regaddr)
            for bfname, mask in getattr(getattr(regdef, blkname.lower()), regname.lower()).get_bits():
                print >> out, linefmt % (bfname.lower(), mask)
            print >> out
