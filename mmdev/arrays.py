from mmdev import components
from mmdev import utils
import collections
import itertools


_array_attrs = 'index', 'elementSize', 'suffix'


class BlockArray(object):

    def __init__(self, index, elementTemplate, elementSize, suffix):
        if isinstance(index, int): # allow for index just being the dimension of the array
            index = range(index)

        if elementTemplate is None:
            self._template = self
        else:
            self._template = elementTemplate
            self._template.parent = self.parent
            self._template.root = self.root

        self._elementSize = elementSize
        self._suffix = suffix
        self._index = collections.OrderedDict.fromkeys(index)
        self._intindex = dict(zip(index, range(len(self._index))))

    @property
    def index(self):
        return self._index.keys()

    def __len__(self):
        return len(self._index)

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


class PeripheralArray(BlockArray, components.Peripheral):
    _attrs = _array_attrs

    def __init__(self, mnemonic, registers, address, size, index, elementTemplate=None,
                 elementSize=None, suffix='[%s]', bind=True, displayName='', description='',
                 kwattrs={}):
        components.Peripheral.__init__(self, mnemonic, registers, address, size,
                                       bind=bind, displayName=displayName,
                                       description=description, kwattrs=kwattrs)
        BlockArray.__init__(self, index, elementTemplate, elementSize, suffix)

    def _getsingleitem(self, i):
        if self._index[i] is None:
            template = self._template
            self._index[i] = components.Peripheral((template.mnemonic + self._suffix) % i, 
                                                   template._nodes,
                                                   template.address + self._intindex[i]*self._elementSize, 
                                                   template.size, 
                                                   bind=True, 
                                                   displayName=(template.displayName + self._suffix) % i,
                                                   description=template.description, kwattrs=template._kwattrs)
            self._index[i].parent = self.parent
            self._index[i].root = self.root

        return self._index[i]


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


class RegisterArray(BlockArray, components.Register):
    _attrs = _array_attrs

    def __init__(self, mnemonic, fields, address, size, index,
                 elementTemplate=None, elementSize=None, suffix='[%s]',
                 access='read-write', resetMask=0, resetValue=None, bind=True,
                 displayName='', description='', kwattrs={}):
        components.Register.__init__(self, mnemonic, fields, address, size,
                                     access=access, bind=bind,
                                     displayName=displayName,
                                     description=description, kwattrs=kwattrs)
        BlockArray.__init__(self, index, elementTemplate, elementSize or size, suffix)
        self.vi = ValueIndex(self)

    def to_dict(self, recursive=False):
        arraydict = {}
        if self != self._template: 
            arraydict['master'] = components.Register.to_dict(self, recursive=recursive)
            arraydict.update(self._template.to_dict(recursive=recursive))
            for a in _array_attrs: arraydict[a] = arraydict['master'].pop(a)
        else:
            arraydict = components.Register.to_dict(self, recursive=recursive)

        return arraydict

    def __setitem__(self, i, x):
        reglst = self[i]
        
        reglen = len(reglst) if isinstance(reglst, list) else 1
        try:
            xlen = len(x)
        except TypeError:
            # allow setting multiple elements with a single number
            xlen = reglen
            if reglen > 1: x = [x]*reglen
        else:
            if reglen != xlen:
                raise ValueError("Cannot write sequence of size %d to array of size %d" % (xlen, reglen))

        if reglen == 1: 
            reglst._write(x)
        else:
            for reg, v in itertools.izip(reglst, x): reg._write(v)

    def _getsingleitem(self, i):
        if self._index[i] is None:
            template = self._template
            self._index[i] = components.Register((template.mnemonic + self._suffix) % i, 
                                                 template._nodes,
                                                 template.address + self._intindex[i]*self._elementSize, 
                                                 template.size, 
                                                 access=template.access,
                                                 bind=True, 
                                                 displayName=(template.displayName + self._suffix) % i,
                                                 description=template.description, kwattrs=template._kwattrs)
            self._index[i].parent = self.parent
            self._index[i].root = self.root

        return self._index[i]
