from mmdev import utils
import logging
import re
from operator import attrgetter
import textwrap

_bracketregex = re.compile('[\[\]]')
_textwrap = textwrap.TextWrapper(drop_whitespace=True)

class LeafBlock(object):
    _fmt="{name} ({mnemonic})"
    _subfmt="{typename} {mnemonic}"
    _attrs = ['mnemonic', 'name', 'description', 'typename']
    
    def __init__(self, mnemonic, fullname=None, descr='-', kwattrs={}):
        self._mnemonic = mnemonic
        self._name = fullname or mnemonic
        self._description = descr
        self.parent = None # parent is None until attached to another block
        self.root = self
        
        self._kwattrs = kwattrs

        if descr != '-':
            self._description = _textwrap.fill(self._description)
        self.__doc__ = self._description

    @property
    def _typename(self):
        return self.__class__.__name__

    def __lt__(self, other):
        return self._key < other._key

    @property
    def _key(self):
        return self._mnemonic

    @property
    def attrs(self):
        attrs= { fn: getattr(self, '_'+fn) for fn in self._attrs }
        attrs['extra'] = self._kwattrs
        return attrs

    def to_dict(self):
        return { self._mnemonic: self.attrs }

    def _tree(self, *args, **kwargs):
        return self._fmt.format(**self.attrs)

    def summary(self):
        descr = textwrap.fill(self._description, initial_indent=' '*4, subsequent_indent=' '*4)
        print self._typename + ' ' + self._fmt.format(**self.attrs) + '\n' + descr

    def __repr__(self):
        return "<{:s} '{:s}'>".format(self._typename, self._mnemonic)


class Block(LeafBlock):
    _dynamicBinding = False

    def __new__(cls, mnemonic, subblocks, fullname=None, descr='-', kwattrs={},
                bind=True, **kwargs):
        if cls._dynamicBinding and bind:
            mblk = dict(cls.__dict__)
        else:
            mblk = super(Block, cls).__new__(cls, mnemonic, fullname=fullname,
                                             descr=descr, kwattrs=kwattrs)

        if not bind:
            return mblk

        for blk in subblocks:
            if _bracketregex.search(blk._mnemonic):
                logging.warning("%s '%s' in %s '%s' is not a legal attribute "
                                "name. Will not be added to attributes."  %
                                (blk.__class__.__name__, blk._mnemonic,
                                 cls.__name__, mnemonic))
                continue

            try:
                if cls._dynamicBinding:
                    mblk[blk._mnemonic]
                else:
                    getattr(mblk, blk._mnemonic)
            except (AttributeError, KeyError):
                if cls._dynamicBinding:
                    mblk[blk._mnemonic] = blk
                else:
                    setattr(mblk, blk._mnemonic, blk)
            else:
                logging.warning("%s '%s' would overwrite existing attribute by "
                                "the same name in %s '%s'. Will not be added "
                                "to attributes." % (blk.__class__.__name__,
                                                    blk._mnemonic, cls.__name__,
                                                    mnemonic))

        if cls._dynamicBinding:
            newcls = type(cls.__name__, (cls,) + cls.__bases__, mblk)
            return super(Block, newcls).__new__(newcls, mnemonic, fullname=fullname,
                                                descr=descr, kwattrs=kwattrs)
        else:
            return mblk

    def __init__(self, mnemonic, subblocks, fullname=None, descr='-', kwattrs={}, **kwargs):
        super(Block, self).__init__(mnemonic, fullname=fullname, descr=descr, kwattrs=kwattrs)

        self._nodes = subblocks
        for blk in self._nodes:
            blk.root = blk.parent = self
        
        for blk in self.walk(l=2):
            blk.root = self

        self._nodes.sort(reverse=True)

    def __len__(self):
        return len(self._nodes)

    def __iter__(self):
        return iter(self._nodes)

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

    def to_dict(self):
        blkdict = self.attrs
        del blkdict['extra']
        for blk in self.itervalues():
            key = blk._typename.lower()+'s'
            if key not in blkdict:
                blkdict[key] = {}
            blkdict[key].update(blk.to_dict())
        return { self._mnemonic: blkdict }

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

    def summary(self):
        super(Block, self).summary()
        for blk in self._nodes:
            descr = textwrap.fill(blk._description, initial_indent=' '*10, subsequent_indent=' '*10)
            print ' '*4 + '* ' + blk._fmt.format(**blk.attrs) + '\n' + descr

    def __repr__(self):
        if self.parent is None:
            return super(Block, self).__repr__()
        return "<{:s} '{:s}' in {:s} '{:s}'>".format(self._typename,
                                                     self._mnemonic,
                                                     self.parent._typename,
                                                     self.parent._mnemonic)


class MemoryMappedBlock(Block):
    _fmt="{name} ({mnemonic}, {address})"
    _subfmt="{address} {mnemonic}"
    _attrs = Block._attrs + ['address']

    def __new__(cls, mnemonic, address, subblocks, fullname=None, descr='-', kwattrs={}, bind=True):
        return super(MemoryMappedBlock, cls).__new__(cls, mnemonic, subblocks, fullname=fullname, descr=descr, kwattrs=kwattrs, bind=bind)

    def __init__(self, mnemonic, address, subblocks, fullname='', descr='-', kwattrs={}, bind=True):
        super(MemoryMappedBlock, self).__init__(mnemonic, subblocks, fullname=fullname, descr=descr, kwattrs=kwattrs, bind=bind)
        self._address = utils.HexValue(address)

    @property
    def _key(self):
        return self._address

    def _set_width(self, width):
        self._address = utils.HexValue(self._address, width)

    def __repr__(self):
        return "<{:s} '{:s}' in {:s} '{:s}' at {}>".format(self._typename, 
                                                             self._mnemonic, 
                                                             self.parent._typename, 
                                                             self.parent._mnemonic, 
                                                             self._address)


class IOBlock(MemoryMappedBlock):
    def _read(self):
        return

    def _write(self, value):
        return 

    @property
    def value(self):
        return utils.HexValue(self._read(), self._width)

    @value.setter
    def value(self, value):
        self._write(value)

    def __set__(self, obj, value):
        if value is not None:
            self.value = value

    def __invert__(self):
        return ~self.value
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


class RootBlock(Block):
    _attrs = Block._attrs + ['width', 'addressBits']

    def __new__(cls, mnemonic, width, addressBits, blocks, fullname=None, descr='', kwattrs={}, bind=True):
        return super(RootBlock, cls).__new__(cls, mnemonic, blocks, fullname=fullname, descr=descr, kwattrs=kwattrs, bind=bind)

    def __init__(self, mnemonic, width, addressBits, blocks, fullname=None, descr='', kwattrs={}, bind=True):
        super(RootBlock, self).__init__(mnemonic, blocks, fullname=fullname, descr=descr, kwattrs=kwattrs, bind=bind)

        self._width = width
        self._addressBits = addressBits
        
        for blk in self.walk():
            blk._set_width(self._width)
