import itertools
import ctypes as _ctypes

_bruijn32lookup = [0, 1, 28, 2, 29, 14, 24, 3, 30, 22, 20, 15, 25, 17, 4, 8, 
                   31, 27, 13, 23, 21, 19, 16, 7, 26, 12, 18, 6, 11, 5, 10, 9]


def _attach_subblocks(block, subblocks):
    for blk in subblocks:
        try:
            getattr(block, blk.mnemonic.lower())
        except AttributeError:
            setattr(block, blk.mnemonic.lower(), blk)
        else:
            raise ValueError("Block '%s' would overwrite existing attribute \
                              or subblock by the same name" % blk.mnemonic)


class LeafBlock(object):
    _fmt="{name:s} ({mnemonic:s})"
    _subfmt="{typename:s} {mnemonic:s}"
    
    def __init__(self, mnemonic, fullname='', descr=''):
        self.mnemonic = mnemonic
        self.name = fullname
        self.description = descr
        self.typename = self.__class__.__name__
        self.parent = None # parent is None until attached to another block
        self.root = self
        self._fields = ['mnemonic', 'name', 'description', 'typename']

        if descr:
            self.__doc__ = descr

    @property
    def attrs(self):
        return {fn: getattr(self, fn) for fn in self._fields}

    def _tree(self, *args, **kwargs):
        return self._fmt.format(**self.attrs)

    @property
    def tree(self, l=2):
        print self._tree(l)

    def _ls(self):
        return self._fmt.format(**self.attrs)

    @property
    def ls(self):
        print self._ls()

    def __repr__(self):
        return "<{:s} '{:s}'>".format(self.typename, self.mnemonic)


class DescriptorBlock(LeafBlock):
    def _read(self):
        return

    def _write(self, value):
        return 

    @property
    def value(self):
        return self._read()

    @value.setter
    def value(self, value):
        self._write(value)

    def __set__(self, obj, value):
        self.value = value

    def __invert__(self):
        return ~self.value
    def __ilshift__(self, other):
        val = self.value << other
        return val
    def __irshift__(self, other):
        val = self.value >> other
        return val
    def __iand__(self, other):
        val = self.value & other
        return val
    def __ixor__(self, other):
        val = self.value ^ other
        return val
    def __ior__(self, other):
        val = self.value | other
        return val
    def __lshift__(self, other):
        return self.value << other
    def __rshift__(self, other):
        return self.value >> other
    def __and__(self, other):
        return self.value & other
    def __xor__(self, other):
        return self.value ^ other
    def __or__(self, other):
        return self.value | other


class Block(LeafBlock):

    def __init__(self, mnemonic, subblocks, fullname='', descr='', dynamic=False):
        super(Block, self).__init__(mnemonic, fullname=fullname, descr=descr)

        if not dynamic:
            _attach_subblocks(self, subblocks)

        self._nodes = subblocks
        for blk in self._nodes:
            blk.root = blk.parent = self
            if hasattr(blk, 'walk'):
                for subblk in blk.walk():
                    subblk.root = self

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

    def _sort(self, key=None, reverse=True):
        self._nodes.sort(key=key, reverse=reverse)

    def walk(self, l=-1, root=False):
        blocks = [self] if root else list(self._nodes)
        d = len(blocks)
        while blocks and l != 0:
            blk = blocks.pop(0)
            d -= 1

            yield blk

            blocks.extend(getattr(blk, '_nodes', []))
            if d == 0:
                d = len(blocks)
                l -= 1

    def _tree(self, l=-1, pfx=''):
        treestr = self._fmt.format(**self.attrs)

        if l == 0: 
            return treestr

        for i, blk in enumerate(self._nodes):
            treestr += '\n'
            if (i+1) == len(self._nodes):
                treestr += pfx + '`-- ' + blk._tree(l=l-1, pfx=pfx + '    ')
                continue
            
            treestr += pfx + '|-- ' + blk._tree(l=l-1, pfx=pfx + '|   ')

        return treestr

    def _ls(self):
        headerstr = self._fmt.format(**self.attrs)
        substr = "\n\t".join([blk._subfmt.format(**blk.attrs) for blk in self._nodes])
        return headerstr + '\n\t' + substr if substr else headerstr

    def __repr__(self):
        if self.parent is None:
            return super(Block, self).__repr__()
        return "<{:s} '{:s}' in {:s} '{:s}'>".format(self.typename,
                                                     self.mnemonic,
                                                     self.parent.typename,
                                                     self.parent.mnemonic)


class MemoryMappedBlock(Block):
    _fmt="{name:s} ({mnemonic:s}, 0x{address:08X})"
    _subfmt="0x{address:08X} {mnemonic:s}"

    def __init__(self, mnemonic, address, subblocks, fullname='', descr='', dynamic=False):
        super(MemoryMappedBlock, self).__init__(mnemonic, subblocks, fullname=fullname, descr=descr, dynamic=dynamic)

        self.address = address
        self._fields += ['address']

    def __repr__(self):
        return "<{:s} '{:s}' in {:s} '{:s}' at 0x{:08x}>".format(self.typename, 
                                                                 self.mnemonic, 
                                                                 self.parent.typename, 
                                                                 self.parent.mnemonic, 
                                                                 self.address)


def Peripheral(mnemonic, address, subblocks, fullname='', descr=''):
    class Peripheral(MemoryMappedBlock):
        pass
    _attach_subblocks(Peripheral, subblocks)
    return Peripheral(mnemonic, address, subblocks, fullname=fullname, descr=descr, dynamic=True)


def Register(mnemonic, address, subblocks, fullname='', descr=''):
    class Register(MemoryMappedBlock, DescriptorBlock):
        def _read(self):
            return self.root.read(self.address)
        def _write(self, value):
            return self.root.write(self.address, value)
    _attach_subblocks(Register, subblocks)
    return Register(mnemonic, address, subblocks, fullname=fullname, descr=descr, dynamic=True)


class BitField(DescriptorBlock):
    _fmt="{name:s} ({mnemonic:s}, 0x{mask:08X})"
    _subfmt="0x{mask:08X} {mnemonic:s}"

    def __init__(self, mnemonic, mask, fullname='', descr=''):
        # calculate the bit offset from the mask using a debruijn hash function
        # use ctypes to truncate the result to a uint32
        # TODO: change to a 64 bit version of the lookup
        super(BitField, self).__init__(mnemonic, fullname=fullname, descr=descr)
        self.mask = mask
        self.address = _bruijn32lookup[_ctypes.c_uint32((mask & -mask) * 0x077cb531).value >> 27]
        self._fields += ['mask', 'address']

    def _read(self):
        return (self.parent.value & self.mask) >> self.address

    def _write(self, value):
        regvalue = (self.parent.value & ~self.mask) | (value << self.address)
        self.parent.value = regvalue

    def __repr__(self):
        return "<{:s} '{:s}' in Register '{:s}' & 0x{:08x}>".format(self.typename, 
                                                                    self.mnemonic, 
                                                                    self.parent.mnemonic, 
                                                                    self.mask)
