from mmdev import utils
import logging
import re
import textwrap
import json


logger = logging.getLogger(__name__)


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
        clsattrs = list(set(clsattrs))

        attrs['_attrs'] = clsattrs
        if '_typename' not in attrs:
            attrs['_typename'] = name
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
    parent : LeafBlock
        Block node that owns this block.
    root : LeafBlock
        Block node that is at the root of the device tree.        
    attrs : dict
        A dict of all metadata available for this block.
    """
    __metaclass__ = MetaBlock

    _fmt = "{mnemonic}"
    _attrs = 'mnemonic', 'description', 'typename'
    
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

    @_macrovalue.setter
    def _macrovalue(self, value):
        setattr(self, self._macrokey, value)

    @property
    def metadata(self):
        return dict(self._kwattrs)

    @property
    def attrs(self):
        attrs = { k : getattr(self, k) if hasattr(self, k) else getattr(self, '_'+k) 
                  for k in self._attrs }
        attrs.update(self._kwattrs)
        return attrs

    def to_json(self, recursive=False, **kwargs):
        key = self._typename.replace('Array', '')
        key = key[0].lower() + key[1:]
        return json.dumps({key : self.to_dict(recursive=recursive)}, **kwargs)

    @property
    def _scrubbed_attrs(self):
        attrs = self.attrs
        for k, v in attrs.items():
            if v == '' or v is None or k == 'typename':
                del attrs[k]
            elif isinstance(v, utils.HexValue):
                attrs[k] = str(v)
        return attrs

    def to_dict(self, **kwargs):
        return self._scrubbed_attrs

    def _tree(self, d=-1, pfx=''):
        return textwrap.fill(self._fmt.format(**self.attrs), subsequent_indent=pfx, width=80)

    def summary(self):
        descr = textwrap.fill(self.description, initial_indent=' '*4, subsequent_indent=' '*4, width=80)
        print '<' + self._typename + '>' + ' ' + self._fmt.format(**self.attrs) + '\n' + descr

    def __repr__(self):
        return "<{:s} '{:s}'>".format(self._typename, self.mnemonic)

    def __str__(self):
        return self._fmt.format(**self.attrs)


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

            try:
                if cls._dynamicBinding:
                    mblk[blk.mnemonic]
                else:
                    getattr(mblk, blk.mnemonic)
            except (AttributeError, KeyError):
                if cls._dynamicBinding:
                    mblk[blk.mnemonic] = blk
                else:
                    setattr(mblk, blk.mnemonic, blk)
            else:
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

        self.displayName = displayName or mnemonic

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
        blkdict = self._scrubbed_attrs
        for blk in self:
            key = blk._typename.replace('Array', '')
            key = key[0].lower() + key[1:] + 's'
            if key not in blkdict:
                blkdict[key] = {}
            if recursive:
                v = blk.to_dict(recursive=recursive)
            else:
                v = blk._scrubbed_attrs
            blkdict[key].update({v.pop('mnemonic') : v})
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
        pfx = '<' + self._typename + '>' + ' '
        print pfx + self._tree(d=depth, pfx=' '*len(pfx))

    def _ls(self):
        headerstr = self._fmt.format(**self.attrs)
        for blk in self._nodes:
            headerstr += '\n\t'
            try:
                int(blk._macrovalue)
            except:
                pass
            else:
                headerstr += str(blk._macrovalue) + ' '
            headerstr += blk.mnemonic
        return headerstr

    def ls(self):
        print self._ls()

    def summary(self):
        super(Block, self).summary()
        for blk in self._nodes:
            descr = textwrap.fill(blk.description, initial_indent=' '*10, subsequent_indent=' '*10, width=80)
            print ' '*4 + '* ' + blk._fmt.format(**blk.attrs) + '\n' + descr

    def __str__(self):
        return self._ls()


READ, WRITE, READWRITE = range(1,4)
Access = dict(zip(('read-only', 'write-only', 'read-write'), (READ, WRITE, READWRITE)))
    
class IOBlock(Block):
    """\
    Models a generic memory mapped hardware block that can be read and/or
    written to through a root Block's interface. This block just defines the
    address and size of a read/write - the IO implementation details are decided
    by the root block.
    """

    ###
    # IOBlock is like the DeviceLink, just one level lower. It requires a
    # _read/_write instead of a memRead/memWrite in order to be more generic
    ###
    _attrs = 'access', 'size'

    def __init__(self, mnemonic, subblocks, size, access='read-write',
                 bind=True, displayName='', description='', kwattrs={}):
        super(IOBlock, self).__init__(mnemonic, subblocks, bind=bind,
                                      displayName=displayName,
                                      description=description, kwattrs=kwattrs)
        self.size = size
        self.access = access
        if Access[self.access] & WRITE:
            self.__write = self._write
        if Access[self.access] & READ:
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

    def _read(self, *args, **kwargs):
        raise IOError("No I/O interface has been bound to this block")

    def _write(self, *args, **kwargs):
        raise IOError("No I/O interface has been bound to this block")
