import itertools
import ctypes as _ctypes
from link import Link

_bruijn32lookup = [0, 1, 28, 2, 29, 14, 24, 3, 30, 22, 20, 15, 25, 17, 4, 8, 
                   31, 27, 13, 23, 21, 19, 16, 7, 26, 12, 18, 6, 11, 5, 10, 9]


class LeafBlockNode(object):
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

    def _tree(self, pfx='', last=False, l=-1):
        tag='`-- ' if last else '|-- '
        return pfx + tag + self._subfmt.format(**self.attrs)

    def _ls(self):
        return self._fmt.format(**self.attrs)

    @property
    def ls(self):
        print self._ls()

    def __repr__(self):
        return "<{:s} '{:s}'>".format(self.typename, self.mnemonic)


class BitFieldValue(object):
    def __get__(self, inst, cls):
        return (inst.root.read(inst.parent.address+inst.address) & inst.mask) >> inst.address
    def __set__(self, inst, value):
        address = inst.parent.address+inst.address
        value = (inst.root.read(address) & ~inst.mask) | (value << inst.address)
        inst.root.write(address, value)

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
        self.address = _bruijn32lookup[_ctypes.c_uint32((mask & -mask) * 0x077cb531).value >> 27]
        self._fields += ['mask', 'address']

    def __repr__(self):
        return "<{:s} '{:s}' in Register '{:s}' & 0x{:08x}>".format(self.typename, 
                                                                    self.mnemonic, 
                                                                    self.parent.mnemonic, 
                                                                    self.mask)

    
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
            raise ValueError("Block '%s' would overwrite existing attribute or "\
                             "subblock by the same name in '%s'." % (subblock.mnemonic, self.mnemonic))

        self._nodes.append(subblock)

        p = subblock.parent = self
        while p.parent is not None: p = p.parent
        subblock.root = p

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

    def walk(self, l=-1):
        blocks = [self]
        d = 1
        while blocks and l != 0:
            blk = blocks.pop(0)
            d -= 1

            yield blk

            blocks.extend(getattr(blk, '_nodes', []))
            if d == 0:
                d = len(blocks)
                l -= 1

    def _tree(self, pfx='', last=False, l=-1):
        if l == 0: 
            return

        headerstr = super(BlockNode, self)._tree(pfx, last)
        pfx += '    ' if last else '|   '

        treestr = ''
        if l != 1 and len(self._nodes):
            treestr = []
            if len(self._nodes) > 1:
                treestr = [blk._tree(pfx, l=l-1) for blk in self._nodes[:-1]]
            treestr.append(self._nodes[-1]._tree(pfx, last=True, l=l-1))
            treestr = '\n' + '\n'.join(treestr)
        return headerstr + treestr

    @property
    def tree(self, l=2):
        if l == 0: 
            return

        headerstr = self._fmt.format(**self.attrs)

        treestr = ''
        if len(self._nodes):
            treestr = []
            if len(self._nodes) > 1:
                treestr = [blk._tree(l=l) for blk in self._nodes[:-1]]
            treestr.append(self._nodes[-1]._tree(last=True, l=l))
            treestr = '\n' + '\n'.join(treestr)
        print headerstr + treestr

    def _ls(self):
        headerstr = self._fmt.format(**self.attrs)
        substr = "\n\t".join([blk._subfmt.format(**blk.attrs) for blk in self._nodes])
        return headerstr + '\n\t' + substr if substr else headerstr

    def __repr__(self):
        if self.parent is None:
            return super(BlockNode, self).__repr__()
        return "<{:s} '{:s}' in {:s} '{:s}'>".format(self.typename,
                                                     self.mnemonic,
                                                     self.parent.typename,
                                                     self.parent.mnemonic)


class Peripheral(BlockNode):
    _fmt="{name:s} ({mnemonic:s}, 0x{address:08X})"
    _subfmt="0x{address:08X} {mnemonic:s}"

    def __init__(self, mnemonic, address, fullname='', descr=''):
        super(Peripheral, self).__init__(mnemonic, fullname=fullname, descr=descr)

        self.address = address
        self._fields += ['address']

    def __repr__(self):
        return "<{:s} '{:s}' in {:s} '{:s}' at 0x{:08x}>".format(self.typename, 
                                                                 self.mnemonic, 
                                                                 self.parent.typename, 
                                                                 self.parent.mnemonic, 
                                                                 self.address)


class RegisterValue(object):
    def __get__(self, inst, cls):
        return inst.root.read(inst.address)
    def __set__(self, inst, value):
        inst.root.write(inst.address, value)

class Register(Peripheral):
    value = RegisterValue()


class RootBlockNode(BlockNode):

    def __init__(self, mnemonic, link=None, fullname='', descr=''):
        super(RootBlockNode, self).__init__(mnemonic, fullname=fullname, descr=descr)
        self._link = Link()
        self._map = {}

    def find(self, key):
        return self._map.get(key.lower())

    def write(self, address, value):
        self._link.write(address, value)

    def read(self, address):
        return self._link.read(address)
