import ctypes as _ctypes
from link import Link

_bruijn32lookup = [0, 1, 28, 2, 29, 14, 24, 3, 30, 22, 20, 15, 25, 17, 4, 8, 
                   31, 27, 13, 23, 21, 19, 16, 7, 26, 12, 18, 6, 11, 5, 10, 9]


class LeafBlockNode(object):
    _fmt="{name:s} ({mnemonic:s})"
    _subfmt="{_type:s} {mnemonic:s}"
    
    def __init__(self, mnemonic, fullname='', descr=''):
        self.mnemonic = mnemonic
        self.name = fullname
        self.descr = descr
        self._type = self.__class__.__name__
        self.parent = None # parent is None until attached to another block
        self.root = self
        self._fields = ['mnemonic', 'name', 'descr', '_type', 'parent']

        if descr:
            self.__doc__ = descr

    @property
    def _fmtdict(self):
        return {fn: getattr(self, fn) for fn in self._fields}

    def _ls(self):
        return self._fmt.format(**self._fmtdict)

    @property
    def ls(self):
        print self._ls()

    def __repr__(self):
        return "<{:s} '{:s}'>".format(self.__class__.__name__, self.mnemonic)


class BitFieldValue(object):
    def __get__(self, inst, cls):
        return (inst.root.read(inst.parent.addr+inst.addr) & inst.mask) >> inst.addr
    def __set__(self, inst, value):
        addr = inst.parent.addr+inst.addr
        value = (inst.root.read(addr) & ~inst.mask) | (value << inst.addr)
        inst.root.write(addr, value)

class BitField(LeafBlockNode):
    _fmt="{name:s} ({mnemonic:s}, 0x{mask:08X})"
    _subfmt="0x{mask:08X} {mnemonic:s}"
    value = BitFieldValue()

    def __init__(self, mnemonic, mask, fullname='', descr=''):
        # calculate the bit offset from the mask using a debruijn hash function
        # use ctypes to truncate the result to a uint32
        # TODO: change to a 64 bit version of the lookup
        super(BitField, self).__init__(mnemonic, fullname=fullname, descr=descr)
        self.mask = mask
        self.addr = _bruijn32lookup[_ctypes.c_uint32((mask & -mask) * 0x077cb531).value >> 27]
        self._fields += ['mask', 'addr']

    def __repr__(self):
        return "<{:s} '{:s}' in Register '{:s}' & 0x{:08x}>".format(self.__class__.__name__, self.mnemonic,self.parent.mnemonic,self.mask)

    
class BlockNode(LeafBlockNode):
    def __init__(self, mnemonic, fullname='', descr=''):
        super(BlockNode, self).__init__(mnemonic, fullname=fullname, descr=descr)
        self._nodes = []

    def _attach_subblock(self, subblock):
        """
        Attach a sub-block to this parent block
        """
        try: # check to see if this will overwrite an already existing attribute
            getattr(self, subblock.mnemonic.lower())
        except AttributeError:
            setattr(self, subblock.mnemonic.lower(), subblock)
        else:
            raise Exception("Block '%s' would overwrite existing attribute or "\
                            "subblock by the same name in '%s'." % (subblock.mnemonic, self.mnemonic))

        self._nodes.append(subblock)

        p = subblock.parent = self
        while p.parent is not None: p = p.parent
        subblock.root = p

        # Ugly hack so root can find all nodes
        if isinstance(self.root, RootBlockNode):
            self.root._map[subblock.mnemonic.lower()] = subblock

    def iterkeys(self):
        return iter(blk.mnemonic for blk in self._nodes)

    def keys(self):
        return list(self.iterkeys())

    def iteritems(self):
        return iter((blk.mnemonic, blk) for blk in self._nodes)

    def items(self):
        return list(self.iteritems())

    def values(self):
        return list(self._nodes)

    def itervalues(self):
        return iter(self._nodes)

    @property
    def tree(self):
        dstr = self._fmt.format(**self._fmtdict)
        substr = '\n'.join([blk._ls() for blk in self._nodes])
        print dstr + '\n' + substr if substr else dstr

    def _ls(self):
        dstr = self._fmt.format(**self._fmtdict)
        substr = "\n\t".join([blk._subfmt.format(**blk._fmtdict) for blk in self._nodes])
        return dstr + '\n\t' + substr if substr else dstr

    def __repr__(self):
        if self.parent is None:
            return super(BlockNode, self).__repr__()
        return "<{:s} '{:s}' in {:s} '{:s}'>".format(self.__class__.__name__,
                                                     self.mnemonic,
                                                     self.parent.__class__.__name__,
                                                     self.parent.mnemonic)


class Peripheral(BlockNode):
    _fmt="{name:s} ({mnemonic:s}, 0x{addr:08X})"
    _subfmt="0x{addr:08X} {mnemonic:s}"

    def __init__(self, mnemonic, addr, fullname='', descr=''):
        super(Peripheral, self).__init__(mnemonic, fullname=fullname, descr=descr)

        self.addr = addr
        self._fields += ['addr']

    def __repr__(self):
        return "<{:s} '{:s}' in {:s} '{:s}' at 0x{:08x}>".format(self.__class__.__name__, self.mnemonic, self.parent.__class__.__name__, self.parent.mnemonic, self.addr)


class RegisterValue(object):
    def __get__(self, inst, cls):
        return inst.root.read(inst.addr)
    def __set__(self, inst, value):
        inst.root.write(inst.addr, value)

class Register(Peripheral):
    value = RegisterValue()


class RootBlockNode(BlockNode):

    def __init__(self, mnemonic, link=None, fullname='', descr=''):
        super(RootBlockNode, self).__init__(mnemonic, fullname=fullname, descr=descr)
        self._link = Link()
        self._map = {}

    def find(self, key):
        return self._map.get(key.lower())

    def write(self, addr, value):
        self._link.write(addr, value)

    def read(self, addr):
        return self._link.read(addr)
