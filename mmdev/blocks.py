from utils import HexValue


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

        if not hasattr(self, '_subfmt'):
            self._subfmt = self._fmt

        if descr:
            self.description = ' '.join(l.strip() for l in descr.split('\n'))
            self.__doc__ = self.description

    @property
    def attrs(self):
        return { fn: getattr(self, fn) for fn in self._fields }

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


class DescriptorMixin(object):
    def _read(self):
        return

    def _write(self, value):
        return 

    @property
    def value(self):
        return HexValue(self._read(), self.root._width)

    @value.setter
    def value(self, value):
        self._write(value)

    def __set__(self, obj, value):
        self.value = value

    def __invert__(self):
        return ~self.value
    def __ilshift__(self, other):
        return self.value << other
    def __irshift__(self, other):
        return self.value >> other
    def __iand__(self, other):
        return self.value & other
    def __ixor__(self, other):
        return self.value ^ other
    def __ior__(self, other):
        return self.value | other
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
    _dynamic = False

    def __new__(cls, mnemonic, subblocks, fullname='', descr='', **kwargs):
        newblk = super(Block, cls).__new__(cls, mnemonic, fullname=fullname, descr=descr)

        mblk = cls if cls._dynamic else newblk
        for blk in subblocks:
            try:
                getattr(mblk, blk.mnemonic.lower())
            except AttributeError:
                setattr(mblk, blk.mnemonic.lower(), blk)
            else:
                raise ValueError("Block '%s' would overwrite existing attribute "   \
                                 "or subblock by the same name in %s '%s'"          \
                                 % (blk.mnemonic, cls.__name__, mnemonic))

        return newblk

    def __init__(self, mnemonic, subblocks, fullname='', descr='', **kwargs):
        super(Block, self).__init__(mnemonic, fullname=fullname, descr=descr)

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

    def __new__(cls, mnemonic, address, subblocks, fullname='', descr=''):
        return super(MemoryMappedBlock, cls).__new__(cls, mnemonic, subblocks, fullname=fullname, descr=descr)

    def __init__(self, mnemonic, address, subblocks, fullname='', descr=''):
        super(MemoryMappedBlock, self).__init__(mnemonic, subblocks, fullname=fullname, descr=descr)

        self.address = HexValue(address)
        self._fields += ['address']

    def __repr__(self):
        return "<{:s} '{:s}' in {:s} '{:s}' at 0x{:08x}>".format(self.typename, 
                                                                 self.mnemonic, 
                                                                 self.parent.typename, 
                                                                 self.parent.mnemonic, 
                                                                 self.address)
