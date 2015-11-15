import ctypes as _ctypes

_bruijn32lookup = [0, 1, 28, 2, 29, 14, 24, 3, 30, 22, 20, 15, 25, 17, 4, 8, 
                   31, 27, 13, 23, 21, 19, 16, 7, 26, 12, 18, 6, 11, 5, 10, 9]



class Block(object):
    _fmt="{name:s} ({mnemonic:s})"
    _subfmt="{_type:s} {mnemonic:s}"
    
    def __init__(self, mnemonic, fullname='', descr=''):
        self.mnemonic = mnemonic
        self.name = fullname
        self.descr = descr
        self._type = self.__class__.__name__
        self._fields = ['mnemonic', 'name', 'descr', '_type']

        if descr:
            self.__doc__ = "{}\n\n{}".format(fullname or mnemonic, descr)

    @property
    def _fmtdict(self):
        return {fn: getattr(self, fn) for fn in self._fields}

    def __repr__(self):
        return self._fmt.format(**self._fmtdict)

    # def __repr__(self):
    #     return "<{:s} '{:s}'>".format(self.__class__.__name__, self.mnemonic)


class BlockNode(Block):

    def __init__(self, mnemonic, parent=None, fullname='', descr=''):
        super(BlockNode, self).__init__(mnemonic, fullname=fullname, descr=descr)
        self.parent = parent
        self._fields += ['parent']

        self.root = self
        self._blocks = []
        self._map = {}

        if parent is not None:
            p = parent
            while p.parent is not None:
                p = p.parent
            self.root = p
            self._map = self.root._map

    def __getitem__(self, key):
        try:
            return self._map[key.lower()]
        except KeyError:
            raise KeyError(key)

    def _create_subblock(self, blocktype, mnemonic, addr=None, fullname='', descr=''):
        if addr is None:
            subblock = blocktype(mnemonic, parent=self, fullname=fullname, descr=descr)
        else:
            subblock = blocktype(mnemonic, addr, parent=self, fullname=fullname, descr=descr)
        setattr(self, mnemonic.lower(), subblock)

        if hasattr(subblock, 'mask'):
            setattr(self, mnemonic.upper(), subblock.mask)
        elif hasattr(subblock, 'addr'):
            setattr(self, mnemonic.upper(), subblock.addr)

        self._blocks.append(subblock)
        self._map[mnemonic.lower()] = subblock

        return subblock

    def iterkeys(self):
        return iter(blk.mnemonic for blk in self._blocks)

    def keys(self):
        return list(self.iterkeys())

    def iteritems(self):
        return iter((blk.mnemonic, blk) for blk in self._blocks)

    def items(self):
        return list(self.iteritems())

    def values(self):
        return list(self._blocks)

    def itervalues(self):
        return iter(self._blocks)

    @property
    def tree(self):
        dstr = self._fmt.format(**self._fmtdict)
        substr = '\n'.join(map(repr,self._blocks))
        print dstr + '\n' + substr if substr else dstr

    def __repr__(self):
        dstr = self._fmt.format(**self._fmtdict)
        substr = "\n\t".join([blk._subfmt.format(**blk._fmtdict) for blk in self._blocks])
        return dstr + '\n\t' + substr if substr else dstr

    def _write(self, addr, value):
        print "0x%08x <= 0x%08x" % (addr, value)

    def _read(self, addr):
        value = 0xdeadbeef
        print "0x%08x => 0x%08x" % (addr, value)
        return value

    # def __repr__(self):
    #     if self.parent is None:
    #         return "<{:s} '{:s}'>".format(self.__class__.__name__, self.mnemonic)
    #     else:
    #         return "<{:s} '{:s}' in {:s} '{:s}'>".format(self.__class__.__name__, self.mnemonic, self.parent.__class__.__name__,'.'.join([p.mnemonic for p in self.parents[::-1]]))


class MemoryMappedBlock(BlockNode):
    _fmt="{name:s} ({mnemonic:s}, 0x{addr:08X})"
    _subfmt="0x{addr:08X} {mnemonic:s}"

    def __init__(self, mnemonic, addr, parent, fullname='', descr=''):
        super(MemoryMappedBlock, self).__init__(mnemonic, parent=parent, fullname=fullname, descr=descr)

        self.addr = addr
        self._fields += ['addr']

    def _create_register(self, mnemonic, addr, fullname='', descr='', fmt=None):
        return self._create_subblock(Register, mnemonic, addr=addr, fullname=fullname, descr=descr)

    # def __repr__(self):
    #     return "<{:s} '{:s}' in {:s} '{:s}' at 0x{:08x}>".format(self.__class__.__name__, self.mnemonic, self.parent.__class__.__name__, self.parent.mnemonic, self.addr)


class RegisterValue(object):
    def __get__(self, inst, cls):
        return inst._read(inst.addr)

    def __set__(self, inst, value):
        inst._write(inst.addr, value)


class BitFieldValue(object):
    def __get__(self, inst, cls):
        return (inst._read(inst.parent.addr+inst.addr) & inst.mask) >> inst.addr

    def __set__(self, inst, value):
        addr = inst.parent.addr+inst.addr
        value = (inst._read(addr) & ~inst.mask) | (value << inst.addr)
        inst._write(addr, value)


class Register(MemoryMappedBlock):
    value = RegisterValue()

    def _create_bitfield(self, mnemonic, addr, fullname='', descr=''):
        return self._create_subblock(BitField, mnemonic, addr=addr, fullname=fullname, descr=descr)


class BitField(Block):
    _fmt="{name:s} ({mnemonic:s}, 0x{mask:08X})"
    _subfmt="0x{mask:08X} {mnemonic:s}"
    value = BitFieldValue()

    def __init__(self, mnemonic, mask, parent, fullname='', descr=''):
        # calculate the bit offset from the mask using a debruijn hash function
        # use ctypes to truncate the result to a uint32
        # TODO: change to a 64 bit version of the lookup
        super(BitField, self).__init__(mnemonic, fullname=fullname, descr=descr)
        self.parent = parent
        self.addr = _bruijn32lookup[_ctypes.c_uint32((mask & -mask) * 0x077cb531).value >> 27]
        self.mask = mask
        self._fields += ['mask', 'addr', 'parent']
        self._read = parent._read
        self._write = parent._write

    # def __repr__(self):
    #     return "<{:s} '{:s}' in Register '{:s}' & 0x{:08x}>".format(self.__class__.__name__, self.mnemonic,self.parent.mnemonic,self.mask)
