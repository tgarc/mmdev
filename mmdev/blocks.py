from mmdev import utils
import logging
import re
import textwrap
import json
import collections
import copy
import itertools

logger = logging.getLogger(__name__)


__allblocks__ = [] # Register of all Block types


class MetaBlock(type):
    def __new__(cls, name, bases, attrs):
        clsattrs = attrs.get('_attrs', ())
        if isinstance(clsattrs, basestring):
            clsattrs = [clsattrs,]

        # inherit all _attrs from base classes
        clsattrs = list(clsattrs)
        macrokey = attrs.get('_macrokey', None)
        for b in bases:
            if type(b) is not MetaBlock:
                continue
            if macrokey is None and hasattr(b, '_macrokey'):
                macrokey = b._macrokey
                attrs['_macrokey'] = macrokey
            newattrs = getattr(b, '_attrs', ())
            if isinstance(newattrs, basestring):
                newattrs = [newattrs,]
            clsattrs.extend(list(newattrs))
        clsattrs = tuple(set(clsattrs))

        attrs['_attrs'] = clsattrs
        if '_typename' not in attrs:
            attrs['_typename'] = name

        # __allblocks__.append(newcls.__module__ + '.' + name)

        return super(MetaBlock, cls).__new__(cls, name, bases, attrs)


class LeafBlock(object):
    """\
    A generic node object that can have ancestors but no descendant nodes.

    Parameters
    ----------
    mnemonic : str
        Shorthand or abbreviated name of block.
    description : str
        A string describing functionality, usage, and other relevant notes about
        the block.

    Attributes
    ----------
    parent : LeafBlock instance
        Block node that owns this block.
    root : LeafBlock instance
        Block node that is at the root of the device tree.        
    attrs : dict
        A dict of all metadata available for this block.
    """
    __metaclass__ = MetaBlock

    _fmt = "{mnemonic}"
    _attrs = 'mnemonic', 'description'
    
    def __init__(self, mnemonic, description='', kwattrs={}):
        self.mnemonic = mnemonic
        self.description = description
        self.parent = None # parent is None until attached to another block
        self.root = self

        self._kwattrs = kwattrs
        self.__doc__ = textwrap.fill(self.description, width=70)

    @property
    def _macrovalue(self):
        return getattr(self, self._macrokey)

    # @_macrovalue.setter
    # def _macrovalue(self, value):
    #     setattr(self, self._macrokey, value)

    @property
    def metadata(self):
        return dict(self._kwattrs)

    @property
    def attrs(self):
        attrs = { k : getattr(self, k) if hasattr(self, k) else getattr(self, '_'+k) 
                  for k in self._attrs }
        # attrs.update(self._kwattrs)
        return attrs

    def to_json(self, recursive=False, key=None, **kwargs):
        if key is None: 
            key = self._typename
            key = key[0].lower() + key[1:]
        return json.dumps(collections.OrderedDict([(key, self.to_dict(recursive=recursive))]), **kwargs)

    def _scrubattrs(self):
        attrs = self.attrs
        for k, v in attrs.items():
            if v == '' or v is None:
                del attrs[k]
            elif isinstance(v, utils._IntValue):
                attrs[k] = str(v)
        return attrs

    def __int__(self):
        try:
            if isinstance(self._macrovalue, int):
                return self._macrovalue
        except AttributeError:
            pass

        raise TypeError

    def to_dict(self, **kwargs):
        return self._scrubattrs()

    def summary(self):
        descr = textwrap.fill(self.description, initial_indent=' '*4, subsequent_indent=' '*4, width=80)
        print '<' + self._typename + '>' + ' ' + self._fmt.format(**self.attrs) + '\n' + descr

    def _ls(self):
        return self._fmt.format(**self.attrs)

    def _repr_pretty_(self, p, cycle):
        if cycle:
            p.text(str(self))
        else:
            p.text(self._ls())

    def __copy__(self):
        cls = self.__class__
        blk = cls.__new__(cls)
        blk.__dict__.update(self.__dict__)
        blk.parent = None
        blk.root = blk

        return blk

    def __repr__(self):
        return "<{:s} '{:s}'>".format(self._typename, self.mnemonic)

    def __str__(self):
        return self._fmt.format(**self.attrs)


class BlockArray(LeafBlock):
    _attrs = 'index', 'elementSize', 'suffix'

    def __init__(self, index, elementTemplate, elementSize=None, suffix='[%s]', master=None):
        super(BlockArray, self).__init__(elementTemplate.mnemonic,
                                         description=elementTemplate.description,
                                         kwattrs=elementTemplate._kwattrs)
        for attrk in elementTemplate._attrs:
            attrv = getattr(elementTemplate, attrk)
            # self._attrs = self._attrs + (attrk,)
            setattr(self, attrk, attrv)
        self._fmt = elementTemplate._fmt

        if isinstance(index, int): # allow for index just being the dimension of the array
            index = range(index)
                         
        self._template = elementTemplate
        self.master = master

        self._elementSize = utils.HexValue(elementTemplate.size if elementSize is None else elementSize)
        self._suffix = suffix
        self._index = collections.OrderedDict.fromkeys(index)
        self._intindex = dict(zip(index, range(len(self._index))))

    @property
    def attrs(self):
        attrs = self._template.attrs
        attrs.update(super(BlockArray, self).attrs)
        return attrs

    @property
    def _macrovalue(self):
        return getattr(self._template, self._template._macrokey)

    def to_json(self, recursive=False, key=None, **kwargs):
        if key is None:
            key = self._typename.replace('Array', '')
            key = key[0].lower() + key[1:]
        return super(BlockArray, self).to_json(recursive=recursive, key=key, **kwargs)

    def to_dict(self, recursive=False):
        arraydict = self._template.to_dict(recursive=recursive)
        if self.master:
            arraydict['master'] = self.master.to_dict(recursive=recursive)
        arraydict.update(super(BlockArray, self).to_dict(recursive=recursive))

        return arraydict

    def _ls(self):
        headerstr = ''
        if self.master:
            headerstr = self.master._ls() + '\n'
        return headerstr + self._template._ls()

    @property
    def index(self):
        return self._index.keys()

    def __len__(self):
        return len(self._index)

    def __iter__(self):
        return (self._getsingleitem(i) for i in self._index)

    def __sanitizeslice(self, dslice):
        if isinstance(dslice.start, basestring):
            yield self._intindex[dslice.start]
        else:
            yield dslice.start

        if isinstance(dslice.stop, basestring):
            yield self._intindex[dslice.stop] + 1
        else:
            yield dslice.stop

        yield dslice.step

    def __getitem__(self, i):
        if not isinstance(i, slice): # if not a slice, assume a single element
            return self._getsingleitem(i)

        return [self._getsingleitem(i) for i in self.index[slice(*self.__sanitizeslice(i))]]

    def _getsingleitem(self, i):
        raise NotImplementedError


class ValueIndex(object):
    """\
    Indexer for that allows for writing/reading values from a block array using
    indexing and slicing notation.
    """
    def __init__(self, owner):
        self._owner = owner

    def __getitem__(self, i):
        if not isinstance(i, slice): # if not a slice, assume a single element
            return self._owner[i]._read()
        else:
            return [blk._read() for blk in self._owner[i]]

    def __setitem__(self, i, x):
        self._owner.__setitem__(i, x)


class IOBlockArray(BlockArray):

    def __init__(self, index, elementTemplate, elementSize=None, suffix='[%s]', master=None):
        super(IOBlockArray, self).__init__(index, elementTemplate,
                                           elementSize=elementSize,
                                           suffix=suffix, master=master)

        self.vi = ValueIndex(self)

    def __setitem__(self, i, x):
        blklst = self[i]
        
        blklen = len(blklst) if isinstance(blklst, list) else 1
        try:
            xlen = len(x)
        except TypeError:
            # allow setting multiple elements with a single number
            xlen = blklen
            if blklen > 1: x = [x]*blklen
        else:
            if blklen != xlen:
                raise ValueError("Cannot write sequence of size %d to array of size %d" % (xlen, blklen))

        if blklen == 1: 
            blklst._write(x)
        else:
            for blk, v in itertools.izip(blklst, x): blk._write(v)


class Block(LeafBlock):
    """\
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
    displayName : str
        Expanded name or display name of block.
    description : str
        A string describing functionality, usage, and other relevant notes about
        the block.
    """
    _dynamicBinding = False
    _attrs = 'displayName'

    def __new__(cls, mnemonic, subblocks, *args, **kwargs):
        bind = kwargs.get('bind', True)

        if cls._dynamicBinding and bind:
            mblk = dict(cls.__dict__)
        else:
            mblk = super(Block, cls).__new__(cls, mnemonic, **kwargs)

        if not bind:
            return mblk

        for blk in subblocks:
            if re.search('[\[\]]', blk.mnemonic):
                logger.warning("%s '%s' in %s '%s' is not a legal attribute "
                                "name. Will not be added to attributes."  %
                                (blk.__class__.__name__, blk.mnemonic,
                                 cls.__name__, mnemonic))
                continue

            uniq = False
            if cls._dynamicBinding:
                try:
                    mblk[blk.mnemonic]
                except KeyError:
                    mblk[blk.mnemonic] = blk
                    uniq = True
            else:
                try:
                    getattr(mblk, blk.mnemonic)
                except AttributeError:
                    setattr(mblk, blk.mnemonic, blk)
                    uniq = True

            if not uniq:
                logger.warning("%s '%s' would overwrite existing attribute by "
                               "the same name in %s '%s'. Will not be added "
                               "to attributes."  % (blk.__class__.__name__,
                                                    blk.mnemonic, cls.__name__, mnemonic))

        if cls._dynamicBinding:
            newcls = type(cls.__name__, (cls,) + cls.__bases__, mblk)
            return super(Block, newcls).__new__(newcls, mnemonic, **kwargs)
        else:
            return mblk

    def __init__(self, mnemonic, subblocks, bind=True, displayName='', description='', kwattrs={}):
        super(Block, self).__init__(mnemonic, description=description, kwattrs=kwattrs)
        self._bound = bind
        
        self.displayName = displayName or self._typename

        self._nodes = list(subblocks)
        for blk in self._nodes:
            blk.parent = self

        self._nodes.sort(key=lambda x: x._macrovalue, reverse=True)
        self._nodes = tuple(self._nodes)

    def _scrubattrs(self):
        attrs = super(Block, self)._scrubattrs()
        if attrs['displayName'] == self._typename: attrs.pop('displayName')
        return attrs

    # wonky feature to allow lower-case aliasing of nodes
    # def __getattr__(self, attr):
    #     if attr.islower() and attr.upper() in self.keys():
    #         return getattr(self, attr.upper())
    #     else:
    #         raise AttributeError("'%s' object has no attribute '%s'" % (self._typename, attr))

    # def __setattr__(self, attr, value):
    #     if attr.islower() and attr.upper() in self.keys():
    #         setattr(self, attr.upper(), value)
    #     else:
    #         super(Block, self).__setattr__(attr, value)

    def __copy__(self):
        cls = self.__class__.__base__ if self._dynamicBinding else self.__class__
        blk = cls.__new__(cls, self.mnemonic, self._nodes, bind=self._bound)
        blk.__dict__.update(self.__dict__)
        blk.parent = None
        blk.root = blk

        return blk

    # def __deepcopy__(self, memo):
    #     blk = self.__copy__()
    #     memo[id(self)] = blk
    #     print blk
    #     for k, v in self.__dict__.iteritems():
    #         print k, v
    #         setattr(blk, k, copy.deepcopy(v, memo))
    #     print
    #     return blk

    @property
    def nodes(self):
        return self._nodes

    def export(self, namespace):
        namespace.update(dict(self.iteritems()))

    def to_dict(self, recursive=False):
        blkdict = collections.OrderedDict(self._scrubattrs())
        for blk in reversed(self._nodes):
            key = blk._typename
            key = key[0].lower() + key[1:] + 's'
            if isinstance(blk, BlockArray):
                key = key.replace('Array', '')

            if recursive:
                v = blk.to_dict(recursive=recursive)
            else:
                v = collections.OrderedDict(blk._scrubattrs())

            if key not in blkdict:
                blkdict[key] = collections.OrderedDict()
            blkdict[key][v.pop('mnemonic')] = v
        return blkdict

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

    def walk(self, d=-1, l=1):
        n = 1
        blocks = [self]

        while blocks and d != 0:
            blk = blocks.pop(0)
            n -= 1

            if l == 0:
                yield blk

            if isinstance(blk, BlockArray):
                blocks.extend(list(blk))
            else:
                blocks.extend(getattr(blk, '_nodes', []))
            if n == 0:
                n = len(blocks)
                if l == 0:
                    d -= 1
                else:
                    l -= 1
            
    def _ls(self):
        headerstr = self._fmt.format(**self.attrs)
        rowstr = '\n    {}{}{}  {} {}'
        for blk in self._nodes:
            if isinstance(blk, BlockArray) and blk.master:
                mblk = blk.master
                headerstr += rowstr.format('a' if isinstance(mblk, BlockArray) else '-',
                                           'r' if hasattr(mblk, 'access') and Access[mblk.access] & RDACC else '-',
                                           'w' if hasattr(mblk, 'access') and Access[mblk.access] & WRACC else '-',
                                           mblk._macrovalue,
                                           mblk.mnemonic)

            headerstr += rowstr.format('a' if isinstance(blk, BlockArray) else '-',
                                       'r' if hasattr(blk, 'access') and Access[blk.access] & RDACC else '-',
                                       'w' if hasattr(blk, 'access') and Access[blk.access] & WRACC else '-',
                                       blk._macrovalue,
                                       blk.mnemonic)
        return headerstr

    def summary(self):
        super(Block, self).summary()
        for blk in self._nodes:
            descr = textwrap.fill(blk.description, initial_indent=' '*10, subsequent_indent=' '*10, width=80)
            print ' '*4 + '* ' + blk._fmt.format(**blk.attrs) + '\n' + descr


RDACC, WRACC, RWACC = range(1,4)
Access = dict(zip(('read-only', 'write-only', 'read-write'), (RDACC, WRACC, RWACC)))

    
class IOBlock(Block):
    """\
    Models a generic memory mapped hardware block that can be read and/or
    written to through a root Block's interface. This block just defines the
    address and size of a read/write - the IO implementation details are decided
    by the root block.
    """
    _attrs = 'access', 'size'

    def __init__(self, mnemonic, subblocks, size, access='read-write',
                 bind=True, displayName='', description='', kwattrs={}):
        super(IOBlock, self).__init__(mnemonic, subblocks, bind=bind,
                                      displayName=displayName,
                                      description=description, kwattrs=kwattrs)
        self.size = size
        self.access = access
        if Access[self.access] & WRACC:
            self.__write = self._write
        if Access[self.access] & RDACC:
            self.__read = self._read

    def __read(self):
        return 0

    def __write(self, value):
        return

    def _read(self):
        raise NotImplementedError('_read')

    def _write(self, value):
        raise NotImplementedError('_write')

    @property
    def value(self):
        return utils.HexValue(self.__read(), self.size)

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
    """\
    Models a generic hardware block that defines a single memory address space
    and its data bus.

    A few notes about the usage of this block:

    1) This block does not impose any structure on the device tree;
       e.g., this parent need not be the root node.
    2) This block has no idea about the phyical `link` through which it is
       connected, or the transport by which data it is sent.

    Parameters
    ----------
    mnemonic : str
        Shorthand or abbreviated name of block.
    subblocks : list-like
        All the children of this block.
    laneWidth : int
        Defines the number of data bits uniquely selected by each address. For
        example, a value of 8 denotes that the device is byte-addressable.
    busWidth : int
        Defines the bit-width of the maximum single data transfer supported by
        the bus infrastructure. For example, a value of 32 denotes that the
        device bus can transfer a maximum of 32 bits in a single transfer.
    bind : bool
        Tells the constructor whether or not to bind the subblocks as attributes
        of the Block instance.
    displayName : str
        Expanded name or display name of block.
    description : str
        A string describing functionality, usage, and other relevant notes about
        the block.
    """
    _attrs = 'laneWidth', 'busWidth'


    def __init__(self, mnemonic, subblocks, laneWidth, busWidth, 
                 bind=True, displayName='', description='', kwattrs={}):
        super(DeviceBlock, self).__init__(mnemonic, subblocks, 
                                     bind=bind, displayName=displayName,
                                     description=description, kwattrs=kwattrs)
        self.laneWidth = laneWidth
        self.busWidth = busWidth

        for blk in self.walk():
            if isinstance(blk, DeviceBlock):
                # We'll assume that if there is a device block on this level that
                # all other nodes on this level are also device block types
                break
            blk.root = self

    def _read(self, *args, **kwargs):
        raise IOError("No I/O interface has been bound to this block")

    def _write(self, *args, **kwargs):
        raise IOError("No I/O interface has been bound to this block")

    def find(self, key):
        try:
            return (blk for blk in self.walk() if key == blk.mnemonic).next()
        except StopIteration:
            raise ValueError("%s was not found" % key)

    def findall(self, key):
        return tuple(blk for blk in self.walk() if key == blk.mnemonic)
