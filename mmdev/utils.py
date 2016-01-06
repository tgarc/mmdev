import collections
import json

class HexValue(int):
    def __new__(cls, x, bitwidth=0, base=None):
        if base is None:
            newint = super(HexValue, cls).__new__(cls, x)
        else:
            newint = super(HexValue, cls).__new__(cls, x, base=base)
        div, mod = divmod(bitwidth, 4)
        newint._fmt = ("0x{:0%dx}" % (div + bool(mod))).format
        return newint

    def __repr__(self):
        return self._fmt(self)
    def __str__(self):
        return self._fmt(self)

def to_gdbinit(dev):
    import StringIO

    fh = StringIO.StringIO()
    blkfmt = "set $%s = (unsigned long *) 0x%08x"
    bitfmt = "set $%s = (unsigned long) 0x%08x"    
    for blkname, blk in dev.iteritems():
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

def export(devnode, glbls):
    glbls.update(devnode.iteritems())

def to_json(dev, **kwargs):
    return json.dumps(dev.to_dict(), **kwargs)
