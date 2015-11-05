getattrd = lambda obj, x1, x2: getattr(getattr(obj, x1), x2)


class DUT:
    def __init__(self, dutdef):
        self.mnemonic = getattr(dutdef, 'mnemonic', 'DUT')
        self.name = getattr(dutdef, 'name', dutdef.__name__)

        self._mmap = dutdef.MEM_MAP.keys()
        for k in self._mmap:
            setattr(self, k.lower(), Block(dutdef, k))
        self._mmap = sorted(self._mmap, key=lambda k: getattrd(self, k.lower(), 'addr'), reverse=True)

        self._linefmt = "0x{:08X} {:s}".format

    def __repr__(self):
        dstr = "{:s}\n".format(self.name)
        dstr+= "Blocks:\n\t" + "\n\t".join([self._linefmt(getattrd(self, k.lower(), 'addr'), k) for k in self._mmap])
        return dstr

    def __str__(self):
        return "dut('{:s}')".format(self.mnemonic)


class Block:
    def __init__(self, dutdef, blockname):
        self.mnemonic = blockname
        self.addr = dutdef.MEM_MAP[blockname]

        self.name = dutdef.BLK_NAME.get(self.mnemonic, 'block')
        self.descr = dutdef.BLK_DESCR.get(self.mnemonic, '')

        self._rmap = dutdef.BLK_MAP.get(self.mnemonic, ())
        for k in self._rmap:
            setattr(self, k.lower(), Register(dutdef, k))
        self._rmap = sorted(self._rmap, key=lambda k: getattrd(self, k.lower(), 'addr'), reverse=True)

        self._linefmt = "0x{:08X} {:s}".format

    def __repr__(self):
        dstr = "{:s} ({:s}, 0x{:08X})\n".format(self.name, self.mnemonic, self.addr)
        dstr+= "Registers:\n\t" + "\n\t".join([self._linefmt(getattrd(self, k.lower(), 'addr'), k) for k in self._rmap])
        return dstr

    def __str__(self):
        return "block('{:s}', 0x{:08X})".format(self.mnemonic, self.addr)


class Register:
    def __init__(self, dutdef, regname):
        self.mnemonic = regname
        self.addr = dutdef.REG_MAP[self.mnemonic]

        self.name = dutdef.REG_NAME.get(self.mnemonic, 'register')
        self.descr = dutdef.REG_DESCR.get(self.mnemonic, '')

        self._bmap = dutdef.BIT_MAP.get(self.mnemonic, ())
        for k in self._bmap:
            setattr(self, k.lower(), BitField(dutdef, self.mnemonic, k))
        self._bmap = sorted(self._bmap, key=lambda k: getattrd(self, k.lower(), 'mask'), reverse=True)

        self._linefmt = "0x{:08X} {:s}".format

    def __repr__(self):
        dstr = "{:s} ({:s}, 0x{:08X})\n".format(self.name, self.mnemonic, self.addr)
        dstr+= "BitFields:\n\t" + "\n\t".join([self._linefmt(getattrd(self, k.lower(), 'mask'), k) for k in self._bmap])
        return dstr

    def __str__(self):
        return "register('{:s}', 0x{:08X})".format(self.mnemonic, self.addr)

class BitField:
    def __init__(self, dutdef, regname, bfname):
        self.mnemonic = bfname
        self.register = regname
        self.mask = dutdef.BIT_MAP[self.register][self.mnemonic]

    def __repr__(self):
        return "bitfield('{:s}', 0x{:08X})".format(self.mnemonic, self.mask)

    def __str__(self):
        return "bitfield('{:s}', 0x{:08X})".format(self.mnemonic, self.mask)
    
