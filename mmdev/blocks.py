from mmdev import utils
import logging
import re
from operator import attrgetter
import textwrap
import json


_bracketregex = re.compile('[\[\]]')
_textwrap = textwrap.TextWrapper(width=70)


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
    """
    A generic node object that can have ancestors but no descendant nodes.

    Parameters
    ----------
    mnemonic : str
        Shorthand or abbreviated name of block.
    fullname : str
        Expanded name or display name of block.
    descr : str
        A string describing functionality, usage, and other relevant notes about
        the block.

    Attributes
    ----------
    parent : LeafBlock
        Block node that owns this block.
    root : LeafBlock
        Block node that is at the root of the device tree.        
    attrs : dict
        A dict of all metadata available for this block.
    """
    __metaclass__ = MetaBlock

    _macrokey = 'mnemonic'
    _fmt="{name} ({mnemonic})"
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
    def _macrovalue(self):
        return getattr(self, '_'+self._macrokey)

    @_macrovalue.setter
    def _macrovalue(self, value):
        setattr(self, '_'+self._macrokey, value)

    @property
    def _typename(self):
        return self.__class__.__name__

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
        return textwrap.fill(self._fmt.format(**self.attrs), subsequent_indent=pfx, width=80)

    def summary(self):
        descr = textwrap.fill(self._description, initial_indent=' '*4, subsequent_indent=' '*4, width=80)
        print '<' + self._typename + '>' + ' ' + self._fmt.format(**self.attrs) + '\n' + descr

    def __repr__(self):
        return "<{:s} '{:s}'>".format(self._typename, self._mnemonic)


class Block(LeafBlock):
    """
    A generic container node object in a device tree. Has list and dict like
    functionality for accessing direct children blocks.

    Parameters
    ----------
    mnemonic : str
        Shorthand or abbreviated name of block.
    subblocks : list-like
        All the children of this block.
    bind : bool
        Tells the constructor whether or not to bind the subblocks as attributes
        of the Block instance.
    fullname : str
        Expanded name or display name of block.
    descr : str
        A string describing functionality, usage, and other relevant notes about
        the block.
    """
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

        self._nodes = list(subblocks)
        for blk in self:
            blk.parent = self

        self._nodes.sort(key=lambda x: x._macrovalue, reverse=True)

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
        print '<' + self._typename + '>' + ' ' + self._tree(d=depth, pfx=' '*(len(self._typename)+3))

    def ls(self):
        headerstr = self._fmt.format(**self.attrs)
        substr = "\n\t".join([("{%s} {mnemonic}" % blk._macrokey).format(**blk.attrs) for blk in self._nodes])
        print headerstr + '\n\t' + substr if substr else headerstr

    def summary(self):
        super(Block, self).summary()
        for blk in self._nodes:
            descr = textwrap.fill(blk._description, initial_indent=' '*10, subsequent_indent=' '*10, width=80)
            print ' '*4 + '* ' + blk._fmt.format(**blk.attrs) + '\n' + descr

    def __repr__(self):
        if self.parent is None:
            return super(Block, self).__repr__()
        return "<{:s} '{:s}' in {:s} '{:s}'>".format(self._typename,
                                                     self._mnemonic,
                                                     self.parent._typename,
                                                     self.parent._mnemonic)


class MemoryMappedBlock(Block):
    """
    Models a generic hardware block that is mapped into a memory
    space. Instances of this class serve mostly as an abstraction that
    encapsulate groups of lower level, typically read/writable hardware blocks.

    *Note*
    A MemoryMappedBlock 'address' only implies that the block is embedded in an
    address space. It us up to the parent block to define the address space.
    See ``DeviceBlock`` for an example.

    Parameters
    ----------
    mnemonic : str
        Shorthand or abbreviated name of block.
    subblocks : list-like
        All the children of this block.
    address : int
        The absolute address of this block.
    size : int
        Specifies the size of the address region being covered by this block in
        some arbitrary units (typically bytes). The end address of an address
        block results from the sum of address and (size - 1).
    bind : bool
        Tells the constructor whether or not to bind subblocks as attributes of
        the Block instance.
    fullname : str
        Expanded name or display name of block.
    descr : str
        A string describing functionality, usage, and other relevant notes about
        the block.
    """
    _fmt="{name} ({mnemonic}, {address})"
    _attrs = 'address', 'size'
    _macrokey = 'address'

    def __init__(self, mnemonic, subblocks, address, size, bind=True, fullname=None, descr='-', kwattrs={}):
        super(MemoryMappedBlock, self).__init__(mnemonic, subblocks, bind=bind, fullname=fullname, descr=descr, kwattrs=kwattrs)
        self._address = utils.HexValue(address)
        self._size = size

    def __repr__(self):
        return "<{:s} '{:s}' in {:s} '{:s}' at {}>".format(self._typename, 
                                                             self._mnemonic, 
                                                             self.parent._typename, 
                                                             self.parent._mnemonic, 
                                                             self._address)

READ, WRITE, READWRITE = range(1,4)
Access = dict(zip(('read-only', 'write-only', 'read-write'), (READ, WRITE, READWRITE)))
    

class IOBlock(MemoryMappedBlock):
    """
    Models a generic memory mapped hardware block that can be read and/or
    written to through a root Block's interface. This block just defines the
    address and size of a read/write - the IO implementation details are decided
    by the root block.

    Parameters
    ----------
    mnemonic : str
        Shorthand or abbreviated name of block.
    subblocks : list-like
        All the children of this block.
    address : int
        The absolute address of this block.
    size : int
        The number of data bits in this block.
    access : access-type (str)
        Describes the read/write permissions for this block.
        'read-only': 
            read access is permitted. Write operations will be ignored.
        'write-only': 
            write access is permitted. Read operations on this block will always return 0.
        'read-write': 
            both read and write accesses are permitted.
    bind : bool
        Tells the constructor whether or not to bind the subblocks as attributes
        of the Block instance.
    fullname : str
        Expanded name or display name of block.
    descr : str
        A string describing functionality, usage, and other relevant notes about
        the block.
    """
    _attrs = 'access'
    _fmt="{name} ({mnemonic}, {access}, {address})"


    def __init__(self, mnemonic, subblocks, address, size, access='read-write',
                 bind=True, fullname=None, descr='-', kwattrs={}):
        super(IOBlock, self).__init__(mnemonic, subblocks, address, size, bind=bind,
                                      fullname=fullname, descr=descr,
                                      kwattrs=kwattrs)
        self._access = access
        if Access[self._access] & WRITE:
            self.__write = self._write
        if Access[self._access] & READ:
            self.__read = self._read

        # purely for readability, set the data width for child blocks
        for blk in self:
            blk._macrovalue = utils.HexValue(blk._macrovalue, self._size)

    def __read(self):
        return 0

    def __write(self, value):
        return

    def _read(self):
        return self.root._read(self._address, self._size)

    def _write(self, value):
        return self.root._write(self._address, value, self._size)

    @property
    def value(self):
        return utils.HexValue(self.__read(), self._size)

    @value.setter
    def value(self, value):
        self.__write(value)

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

    def __rlshift__(self, other):
        return self.value << other
    def __rrshift__(self, other):
        return self.value >> other
    def __rand__(self, other):
        return self.value & other
    def __rxor__(self, other):
        return self.value ^ other
    def __ror__(self, other):
        return self.value | other


class DeviceBlock(Block):
    """
    Models a generic hardware block that defines a single memory address space
    and its data bus.

    A few notes about the usage of this block:

    1) This block does not impose any structure on the device tree;
       it's even possible that this block has a parent. 
    2) This block has no idea about the phyical `link` through which it is
       connected, or the transport by which data it is sent.

    Parameters
    ----------
    mnemonic : str
        Shorthand or abbreviated name of block.
    subblocks : list-like
        All the children of this block.
    lane_width : int
        Defines the number of data bits uniquely selected by each address. For
        example, a value of 8 denotes that the device is byte-addressable.
    bus_width : int
        Defines the bit-width of the maximum single data transfer supported by
        the bus infrastructure. For example, a value of 32 denotes that the
        device bus can transfer a maximum of 32 bits in a single transfer.
    bind : bool
        Tells the constructor whether or not to bind the subblocks as attributes
        of the Block instance.
    fullname : str
        Expanded name or display name of block.
    descr : str
        A string describing functionality, usage, and other relevant notes about
        the block.
    """
    _attrs = 'lane_width', 'bus_width'

    def __init__(self, mnemonic, subblocks, lane_width, bus_width, 
                 bind=True, fullname=None, descr='-', kwattrs={}):
        super(DeviceBlock, self).__init__(mnemonic, subblocks, 
                                          bind=bind, fullname=fullname,
                                          descr=descr, kwattrs=kwattrs)
        self._lane_width = lane_width
        self._bus_width = bus_width

    def _read(self, address, size):
        raise NotImplementedError

    def _write(self, address, value, size):
        raise NotImplementedError
