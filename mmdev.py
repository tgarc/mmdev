from arm_regs import *


getattrd = lambda obj,x: reduce(getattr,x.split('.'),obj)


class ARM:
    def __init__(self):
        self._mmap = MEM_MAP.keys()
        for k in self._mmap:
            setattr(self,k,Block(k))
            setattr(self,k.lower(),getattr(self,k))
        self._mmap = sorted(self._mmap, key=lambda k: getattrd(self,k+'.addr'), reverse=True)

        self._linefmt = "0x{:08X} {:s}".format

    def __repr__(self):
        return "Blocks:\n\t" + "\n\t".join([self._linefmt(getattrd(self,k+'.addr'),k) for k in self._mmap])


class Block:
    def __init__(self, blockname):
        self.mnemonic = blockname
        self.addr = MEM_MAP[blockname][0]

        self.name = BLK_NAME.get(self.mnemonic,'Block')
        self.descr = BLK_DESCR.get(self.mnemonic,'')

        self._rmap = BLK_MAP.get(self.mnemonic,())
        for k in self._rmap:
            setattr(self,k,Register(k))
            setattr(self,k.lower(),getattr(self,k))            
        self._rmap = sorted(self._rmap, key=lambda k: getattrd(self,k+'.addr'), reverse=True)

        self._linefmt = "0x{:08X} {:s}".format

    def __repr__(self):
        dstr = "{:s} ({:s}, 0x{:08X})\n".format(self.name,self.mnemonic,self.addr)
        dstr+= "Registers:\n\t" + "\n\t".join([self._linefmt(getattrd(self,k+'.addr'),k) for k in self._rmap])
        return dstr

    def __str__(self):
        return "block('{:s}', 0x{:08X})".format(self.mnemonic,self.addr)


class Register:
    def __init__(self, regname):
        self.mnemonic = regname
        self.addr = REG_MAP[self.mnemonic]

        self.name = REG_NAME.get(self.mnemonic,'Register')
        self.descr = REG_DESCR.get(self.mnemonic,'')

        self._bmap = BIT_MAP.get(self.mnemonic,())
        for k in self._bmap:
            setattr(self, k, BitField(self.mnemonic,k))
            setattr(self,k.lower(),getattr(self,k))            
        self._bmap = sorted(self._bmap, key=lambda k: getattrd(self,k+'.offset'), reverse=True)

        self._linefmt = "0x{:08X} {:s}".format

    def __repr__(self):
        dstr = "{:s} ({:s}, 0x{:08X})\n".format(self.name,self.mnemonic,self.addr)
        dstr+= "BitFields:\n\t" + "\n\t".join([self._linefmt(getattrd(self,k+'.mask'),k) for k in self._bmap])
        return dstr

    def __str__(self):
        return "register('{:s}', 0x{:08X})".format(self.mnemonic,self.addr)

class BitField:
    def __init__(self, regname, bfname):
        self.mnemonic = bfname
        self.register = regname
        self.mask, self.offset = BIT_MAP[self.register][self.mnemonic]

        self.name = BIT_NAME.get(self.mnemonic,'BitField')

    def __repr__(self):
        return "bitfield('{:s}', 0x{:08X})".format(self.mnemonic, self.mask)

    def __str__(self):
        return "bitfield('{:s}', 0x{:08X})".format(self.mnemonic, self.mask)
