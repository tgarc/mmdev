from mmdev import utils
import logging
import re
from operator import attrgetter
import textwrap
import json


_bracketregex = re.compile('[\[\]]')
_textwrap = textwrap.TextWrapper(drop_whitespace=True)


class MetaBlock(type):
    def __init__(self, name, bases, attrs):
        for b in bases:
            if type(b) is not MetaBlock:
                continue
            newattrs = attrs.get('_attrs', ())
            if isinstance(newattrs, basestring):
                newattrs = (newattrs,)
            self._attrs = tuple(getattr(b, '_attrs', ())) + tuple(newattrs)


class LeafBlock(object):
    __metaclass__ = MetaBlock

    _fmt="{name} ({mnemonic})"
    _subfmt="{typename} {mnemonic}"
    _attrs = 'mnemonic', 'name', 'description', 'typename'
    
    def __init__(self, mnemonic, fullname=None, descr='-', kwattrs={}):
        self._mnemonic = mnemonic
        self._name = fullname or mnemonic
        self._description = descr
        self.parent = None # parent is None until attached to another block
        self.root = self
        
        self._kwattrs = kwattrs
        self.__doc__ = _textwrap.fill(self._description)

    @property
    def _typename(self):
        return self.__class__.__name__

    @property
    def _key(self):
        return self._mnemonic

    @property
    def attrs(self):
        attrs= { fn: getattr(self, '_'+fn) for fn in self._attrs }
        attrs['extra'] = self._kwattrs
        return attrs

    def to_json(self, recursive=False, **kwargs):
        return json.dumps(self.to_dict(recursive=recursive), **kwargs)

    def to_dict(self, **kwargs):
        return { self._mnemonic: self.attrs }

    def _tree(self, d=-1, pfx=''):
        return textwrap.fill(self._fmt.format(**self.attrs), subsequent_indent=pfx)

    def summary(self):
        descr = textwrap.fill(self._description, initial_indent=' '*4, subsequent_indent=' '*4)
        print self._typename + ' ' + self._fmt.format(**self.attrs) + '\n' + descr

    def __repr__(self):
        return "<{:s} '{:s}'>".format(self._typename, self._mnemonic)


class Block(LeafBlock):
    _dynamicBinding = False

    def __new__(cls, mnemonic, subblocks, *args, **kwargs):
        bind = kwargs.get('bind', True)
        if cls._dynamicBinding and bind:
            mblk = dict(cls.__dict__)
        else:
            mblk = super(Block, cls).__new__(cls, mnemonic, **kwargs)

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
            return super(Block, newcls).__new__(newcls, mnemonic, **kwargs)
        else:
            return mblk

    def __init__(self, mnemonic, subblocks, bind=True, fullname=None, descr='-', kwattrs={}):
        super(Block, self).__init__(mnemonic, fullname=fullname, descr=descr, kwattrs=kwattrs)

        self._nodes = subblocks
        for blk in self._nodes:
            blk.root = blk.parent = self
        
        for blk in self.walk(l=2):
            blk.root = self

        self._nodes.sort(key=lambda x: x._key, reverse=True)

    def __len__(self):
        return len(self._nodes)

    def __iter__(self):
        return iter(self._nodes)

    def export(self, namespace):
        namespace.update(dict(self.iteritems()))

    def to_dict(self, recursive=False):
        blkdict = self.attrs
        for blk in self.itervalues():
            key = blk._typename.lower()+'s'
            if key not in blkdict:
                blkdict[key] = {}
            if recursive:
                v = blk.to_dict()
            else:
                v = blk.attrs
            blkdict[key].update(v)
        return { self._mnemonic: blkdict }

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
        treestr = super(Block, self)._tree(d=d, pfx=pfx)

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
        print self._typename + ' ' + self._tree(d=depth)

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
    _attrs = 'address'

    def __init__(self, mnemonic, subblocks, address, bind=True, fullname=None, descr='-', kwattrs={}):
        super(MemoryMappedBlock, self).__init__(mnemonic, subblocks, bind=bind, fullname=fullname, descr=descr, kwattrs=kwattrs)
        self._address = utils.HexValue(address)

    @property
    def _key(self):
        return self._address

    def __int__(self):
        return int(self._key)

    def _set_width(self, width):
        self._address = utils.HexValue(self._address, width)

    def __repr__(self):
        return "<{:s} '{:s}' in {:s} '{:s}' at {}>".format(self._typename, 
                                                             self._mnemonic, 
                                                             self.parent._typename, 
                                                             self.parent._mnemonic, 
                                                             self._address)


class IOBlock(MemoryMappedBlock):
    """
    access
    ------
    'read-only': read access is permitted. Write operations have an undefined
    result.
    'write-only': write access is permitted. Read operations have an undefined
    result.
    'read-write': both read and write accesses are permitted. Writes affect
    the state of the register and reads return a value related to the
    register.
    """
    _attrs = 'access'
    _fmt="{name} ({mnemonic}, {access}, {address})"


    def __init__(self, mnemonic, subblocks, address, access='read-write', bind=True, fullname=None, descr='-', kwattrs={}):
        super(IOBlock, self).__init__(mnemonic, subblocks, address, bind=bind,
                                      fullname=fullname, descr=descr,
                                      kwattrs=kwattrs)
        self._access = access
        if self._access == 'write-only':
            self._read = lambda slf: 0
        elif self._access == 'read-only':
            self._write = lambda slf, x: None

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
        self.value = value


class RootBlock(Block):
    _attrs = 'width', 'addressBits'

    def __init__(self, mnemonic, subblocks, addressBits, width, bind=True, fullname=None, descr='-', kwattrs={}):
        super(RootBlock, self).__init__(mnemonic, subblocks, bind=bind, fullname=fullname, descr=descr, kwattrs=kwattrs)

        self._width = width
        self._addressBits = addressBits
        
        for blk in self.walk():
            if hasattr(blk, '_set_width'):
                blk._set_width(self._width)
