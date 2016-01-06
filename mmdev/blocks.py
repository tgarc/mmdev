import mmdev.utils as utils
import logging
import re

_bracketregex = re.compile('[\[\]]')

class LeafBlock(object):
    _fmt="{name:s} ({mnemonic:s})"
    _subfmt="{typename:s} {mnemonic:s}"
    _attrs = ['mnemonic', 'name', 'description', 'typename']
    
    def __init__(self, mnemonic, fullname=None, descr='', kwattrs={}):
        self._mnemonic = mnemonic
        self._name = fullname or mnemonic
        self._description = descr
        self.parent = None # parent is None until attached to another block
        self.root = self
        
        self._kwattrs = kwattrs

        if self.__class__._subfmt == LeafBlock._subfmt:
            self.__class__._subfmt = self.__class__._fmt            

        if descr:
            self._description = ' '.join(l.strip() for l in descr.split('\n'))
            self.__doc__ = self._description

    @property
    def _typename(self):
        return self.__class__.__name__

    @property
    def attrs(self):
        attrs= { fn: getattr(self, '_'+fn) for fn in self._attrs }
        attrs.update(self._kwattrs)
        return attrs

    def _tree(self, *args, **kwargs):
        return self._fmt.format(**self.attrs)

    def __repr__(self):
        return "<{:s} '{:s}'>".format(self._typename, self._mnemonic)


class DescriptorMixin(object):
    def _read(self):
        return

    def _write(self, value):
        return 

    @property
    def value(self):
        return utils.HexValue(self._read(), self.root._width)

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

    def __new__(cls, mnemonic, subblocks, fullname=None, descr='', kwattrs={}, **kwargs):
        newblk = super(Block, cls).__new__(cls, mnemonic, fullname=fullname, descr=descr, kwattrs=kwattrs)

        mblk = cls if cls._dynamic else newblk
        for blk in subblocks:
            if _bracketregex.search(blk._mnemonic):
                logging.warning("%s '%s' in %s '%s' is not a legal attribute name. Will not be added to attributes."
                                % (blk.__class__.__name__, blk._mnemonic, cls.__name__, mnemonic))
                continue

            try:
                getattr(mblk, blk._mnemonic)
            except AttributeError:
                setattr(mblk, blk._mnemonic, blk)
            else:
                logging.warning("%s '%s' would overwrite existing attribute by the same name in "   \
                                "%s '%s'. Will not be added to attributes."                         \
                                % (blk.__class__.__name__, blk._mnemonic, cls.__name__, mnemonic))

        return newblk

    def __init__(self, mnemonic, subblocks, fullname=None, descr='', kwattrs={}, **kwargs):
        super(Block, self).__init__(mnemonic, fullname=fullname, descr=descr, kwattrs=kwattrs)

        self._nodes = subblocks
        for blk in self._nodes:
            blk.root = blk.parent = self
        
        for blk in self.walk(l=2):
            blk.root = self

    def iterkeys(self):
        return iter(blk._mnemonic for blk in self._nodes)

    def keys(self):
        return list(self.iterkeys())

    def iteritems(self):
        return iter((blk._mnemonic, blk) for blk in self._nodes)

    def items(self):
        return list(self.iteritems())

    def values(self):
        return list(self._nodes)

    def itervalues(self):
        return iter(self._nodes)

    def _sort(self, key=None, reverse=True):
        self._nodes.sort(key=key, reverse=reverse)

    def walk(self, d=-1, l=1):
        n = 1
        blocks = [self]

        while blocks and d != 0:
            blk = blocks.pop(0)
            n -= 1

            if l == 0:
                yield blk

            blocks.extend(getattr(blk, '_nodes', []))
            if n == 0:
                n = len(blocks)
                if l == 0:
                    d -= 1
                else:
                    l -= 1
            
    def _tree(self, d=-1, pfx=''):
        treestr = self._fmt.format(**self.attrs)

        if d == 0: 
            return treestr

        for i, blk in enumerate(self._nodes, start=1):
            treestr += '\n'
            if i == len(self._nodes):
                treestr += pfx + '`-- ' + blk._tree(d=d-1, pfx=pfx + '    ')
            else:
                treestr += pfx + '|-- ' + blk._tree(d=d-1, pfx=pfx + '|   ')

        return treestr

    def tree(self, depth=2):
        print self._tree(d=depth)

    def ls(self):
        headerstr = self._fmt.format(**self.attrs)
        substr = "\n\t".join([blk._subfmt.format(**blk.attrs) for blk in self._nodes])
        print headerstr + '\n\t' + substr if substr else headerstr

    def __repr__(self):
        if self.parent is None:
            return super(Block, self).__repr__()
        return "<{:s} '{:s}' in {:s} '{:s}'>".format(self._typename,
                                                     self._mnemonic,
                                                     self.parent._typename,
                                                     self.parent._mnemonic)


class MemoryMappedBlock(Block):
    _fmt="{name:s} ({mnemonic:s}, 0x{address:08X})"
    _subfmt="0x{address:08X} {mnemonic:s}"
    _attrs = Block._attrs + ['address']

    def __new__(cls, mnemonic, address, subblocks, fullname=None, descr='', kwattrs={}):
        return super(MemoryMappedBlock, cls).__new__(cls, mnemonic, subblocks, fullname=fullname, descr=descr, kwattrs={})

    def __init__(self, mnemonic, address, subblocks, fullname='', descr='', kwattrs={}):
        super(MemoryMappedBlock, self).__init__(mnemonic, subblocks, fullname=fullname, descr=descr, kwattrs={})
        self._address = utils.HexValue(address)

    def __repr__(self):
        return "<{:s} '{:s}' in {:s} '{:s}' at 0x{:08x}>".format(self._typename, 
                                                                 self._mnemonic, 
                                                                 self.parent._typename, 
                                                                 self.parent._mnemonic, 
                                                                 self._address)
