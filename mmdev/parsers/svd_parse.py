from xml.etree import ElementTree
from mmdev.parsers.deviceparser import DeviceParser, ParseException, RequiredValueError
from mmdev.components import CPU, Device, Peripheral, Register, BitField, EnumeratedValue
from mmdev.arrays import RegisterArray
from mmdev.utils import HexValue, BinValue

import re
import logging
from collections import OrderedDict
from itertools import imap, chain
import sys

logger = logging.getLogger(__name__)

array_suffex = re.compile(r'\[%s\]|_?%s')

def get_suffix(name, exp=array_suffex): 
    m = exp.search(name)
    return m.group() if m else m

get_basename = lambda name, exp=array_suffex: re.sub(exp, '', name)


def _readtxt(node, tag, default=None, parent={}, required=False, pop=True):
    if pop:
        x = node.pop(tag, parent.get(tag, default))
    else:
        x = node.get(tag, parent.get(tag, default))

    if required and x is None:
        raise RequiredValueError("'%s'" % tag)

    return x.text if isinstance(x, ElementTree.Element) else x

def _readint(node, tag, default=None, parent={}, required=False, pop=True):
    if pop:
        x = node.pop(tag, None)
    else:
        x = node.get(tag, None)

    if x is None:
        if required and default is None:
            raise RequiredValueError("'%s'" % tag)
                
        return parent.get(tag, default)
    else:
        x = x.text

    x = x.lower()
    if x.startswith('0x'):
        return HexValue(x, bitwidth=len(x[2:])*4, base=16)
    elif x.startswith('#'):
        return BinValue(x[1:].replace('x','0'), base=2) # replace DCs with 0's for now
    elif x == 'false':
        return False
    elif x == 'true':
        return True
    else:
        return int(x)


class SVDNode(dict):
    def __init__(self, node, *args, **kwargs):
        super(SVDNode, self).__init__()
        if isinstance(node, list):
            if node == []:
                return
            node = node.pop(0)

        for e in node:
            if e.tag not in self:
                self[e.tag] = e
                continue

            if not isinstance(self[e.tag], list):
                self[e.tag] = [self[e.tag]]
            self[e.tag].append(e)

        self.update(node.attrib)


class SVDParser(DeviceParser):
    _raiseErr = True
    _supcls = None

    @classmethod
    def parse_subblocks(cls, subblksnode, parser, *args, **kwargs):
        # Collect blocks first, grouping blocks by their base name (i.e. name
        # without an array suffix)
        blkmap = OrderedDict()
        for blknode in subblksnode:
            name = get_basename(blknode.findtext('name'))
            if name in blkmap:
                blkmap[name].append(blknode)
            else:
                blkmap[name] = [blknode]

        subblocks = []
        for name, blknodelst in blkmap.iteritems():
            nodes = []
            parents = []

            # Convert nodes to SVDNodes and grab the appropriate parent nodes
            for bnode in blknodelst:
                # Since a parent may actually be an array block, iterate through
                # the parent list and find the first one that has the same
                # suffix (or lack of one)
                parent = {}
                if 'derivedFrom' in bnode.attrib:
                    childsfx = get_suffix(bnode.findtext('name'))
                    for pblk in blkmap[get_basename(bnode.attrib['derivedFrom'])]:
                        if get_suffix(pblk.findtext('name')) == childsfx:
                            parent = SVDNode(pblk)
                            break
                parents.append(parent)
                nodes.append(SVDNode(bnode))

            if len(nodes) == 1 or parser != cls.parse_register:
                nodes = nodes.pop()
                parents = parents.pop()
                
            # Parse this collection of sub-blocks
            try:
                blk = parser(nodes, *args, parent=parents, **kwargs)
            except ParseException as e:
                if cls._raiseErr:
                    raise e
                print >> sys.stderr, "Parse error for node(s) '%s': %s: %s" \
                                     % (name, e.__class__.__name__, e.message)
                continue

            # add parsed node(s) to the list
            if isinstance(blk, list):
                subblocks.extend(blk)
            elif blk is not None:
                subblocks.append(blk)

        return subblocks

    @classmethod
    def parse_device(cls, devfile, raiseErr=True, supcls=None):
        cls._raiseErr = raiseErr
        cls._supcls = supcls
        devnode = SVDNode(ElementTree.parse(devfile).getroot())

        try:
            mnem = _readtxt(devnode, 'name', required=True)
            # version = _readtxt(devnode, 'version', required=True)
            description = _readtxt(devnode, 'description', required=True)
            addressUnitBits = _readint(devnode, 'addressUnitBits', required=True)
            width = _readint(devnode, 'width', required=True)
            vendor = _readtxt(devnode, 'vendor', '')

            regopts = { 'size'      :   _readint(devnode, 'size'),
                        'access'    :   _readtxt(devnode, 'access'),
                        # 'protection':   _readtxt(devnode, 'protection'),
                        'resetValue':   _readint(devnode, 'resetValue'),
                        'resetMask' :   _readint(devnode, 'resetMask') }

            for k, t in {'vendorID': _readtxt, 'version': _readtxt, 'series':
                         _readtxt, 'licenseText': _readtxt}.items():
                if k in devnode: devnode[k] = t(devnode, k)

            cpu_node = devnode.pop('cpu', None)
            if cpu_node is not None:
                cpu_node = SVDNode(cpu_node)
                
                for k, t in {'nvicPrioBits':_readint, 'vtorPresent':_readint,
                             'vendorSysTickConfig':_readtxt}.items():
                    if k in cpu_node: cpu_node[k] = t(cpu_node, k)

                cpu = CPU(_readtxt(cpu_node, 'name'),
                          _readtxt(cpu_node, 'revision'),
                          _readtxt(cpu_node, 'endian'),
                          _readint(cpu_node, 'mpuPresent'),
                          _readint(cpu_node, 'fpuPresent'),
                          kwattrs=cpu_node)
            else:
                cpu = None
        except ParseException as e:
            if cls._raiseErr:
                raise e
            logger.critical(e.message)
            return None

        pphs = cls.parse_subblocks(devnode.pop('peripherals'), cls.parse_peripheral, **regopts)

        args = mnem, pphs, addressUnitBits, width, cpu
        kwargs = dict(description=description, vendor=vendor,
                      kwattrs=devnode)

        # don't ask...
        if cls._supcls is None:
            return Device(*args, **kwargs)

        newdev = Device.__new__(cls._supcls, *args, **kwargs)
        Device.__init__(newdev, *args, **kwargs)
        return newdev

    @classmethod
    def parse_peripheral(cls, pphnode, parent={}, size=None, access=None,
                         protection=None, resetValue=None, resetMask=0):
        name = _readtxt(pphnode, 'name', parent=parent, required=True)
        pphaddr = _readint(pphnode, 'baseAddress', parent=parent, required=True)
        description = _readtxt(pphnode,'description', '', parent=parent) 

        regopts = { 'size': _readint(pphnode, 'size', parent.get('size', size)),
                    'access': _readtxt(pphnode, 'access', parent.get('access', access)),
                    # 'protection': _readtxt(pphnode, 'protection', parent.get('protection', protection)),
                    'resetValue': _readint(pphnode, 'resetValue', resetValue, parent=parent),
                    'resetMask': _readint(pphnode, 'resetMask', resetMask, parent=parent),
                    'prependToName': _readtxt(pphnode, 'prependToName', '', parent=parent),
                    'appendToName': _readtxt(pphnode, 'appendToName', '', parent=parent)}

        regs = cls.parse_subblocks(pphnode.pop('registers', parent.get('registers', [])), 
                                   cls.parse_register, pphaddr, **regopts)

        if 'groupName' in pphnode or 'groupName' in parent:
            pphnode['groupName'] = _readtxt(pphnode, 'groupName', parent=parent)

        if 'interrupt' in pphnode:
            intrpt = SVDNode(pphnode['interrupt'])
            intrpt['name'] = _readtxt(intrpt, 'name', required=True)
            intrpt['value'] = _readint(intrpt, 'value', required=True)
            intrpt['description'] = _readtxt(intrpt, 'description', '')
            pphnode['interrupt'] = intrpt

        # addressBlocks can be either a list or a single instance
        # here we force it into a list
        addrblocks = pphnode.pop('addressBlock', parent.get('addressBlock'))
        if not isinstance(addrblocks, list):
            addrblocks = [addrblocks]

        pphblk = []
        for addrblk in imap(SVDNode, addrblocks):
            offset = _readint(addrblk, 'offset', required=True)
            size = _readint(addrblk, 'size', required=True)
            # usage = _readint(pphnode, 'usage')

            pphblk.append(Peripheral(name,
                                     regs,
                                     pphaddr + offset,
                                     size,
                                     description=description,
                                     kwattrs=pphnode))
        return pphblk


    @classmethod
    def parse_register(cls, regnode, baseaddr, parent=None, size=None,
                       access=None, protection=None, resetValue=None,
                       resetMask=0, prependToName='', appendToName=''):
        if not isinstance(regnode, list):
            regnodelst = [regnode]
            parentlst = [parent or {}]
        else:
            regnodelst = regnode
            parentlst = [{}]*len(regnodelst) if parent is None else parent

        masterCnt = 0
        for i in range(len(regnodelst)):
            dim = _readint(regnodelst[i], 'dim', parent=parentlst[i], pop=False)

            # Ah, if one of the elements has no 'dim' element then this must be
            # the master element. 
            if dim is None:
                masterCnt += 1
                masterIdx = i
            # Otherwise, we just assume this is a collection of register arrays
            # and use the first reg array as a template for the rest

        if masterCnt > 1:
            raise ParseException("Non-unique identifier for register %s" % name)
        elif masterCnt == 1:
            templatereg, parent = regnodelst.pop(masterIdx), parentlst.pop(masterIdx)
            hasmaster = True
        else: # masterCnt == 0:
            templatereg, parent = regnodelst[0], parentlst[0]
            hasmaster = False

        (name, bits, addr, size), kwargs = cls._parse_register(templatereg, baseaddr,
                                                               parent=parent, size=size,
                                                               access=access,
                                                               protection=protection,
                                                               resetValue=resetValue,
                                                               resetMask=resetMask)

        # This is just a regular register
        if masterCnt == 1 and len(regnodelst) == 0:
            return Register(name, bits, addr, size, **kwargs)

        regs = []
        if hasmaster:
            # Grab the first array and use it as the template
            templatereg, parent = regnodelst[0], parentlst[0]
            (tname, tbits, taddr, tsize), tkwargs = cls._parse_register(templatereg, baseaddr,
                                                                        parent=parent, size=size,
                                                                        access=access,
                                                                        protection=protection,
                                                                        resetValue=resetValue,
                                                                        resetMask=resetMask)
            # Strip the suffix off the names
            suffix      = get_suffix(tname)
            tkwargs['displayName'] = get_basename(tkwargs['displayName'])
            tname = prependToName + get_basename(tname) + appendToName
            master = Register(tname, tbits, taddr, tsize, **tkwargs)
        else:
            # No template needed, just use the properties of the array itself
            templatereg, parent = regnodelst[0], parentlst[0]
            suffix = get_suffix(name)
            kwargs['displayName'] = get_basename(kwargs['displayName'])
            name = get_basename(name)
            master = None

        name = prependToName + name + appendToName

        # dimIncrement has to be the same across a register array, so just take
        # it from the first one
        dimInc = _readint(templatereg, 'dimIncrement', default=size, parent=parent, required=True)

        # Concatenate the index from all found register arrays
        dimIndex = cls._parse_arrays(regnodelst)

        template = Register(name, bits, addr, size, **kwargs)

        return RegisterArray(dimIndex, template, elementSize=dimInc, suffix=suffix, master=master)

    @classmethod
    def _parse_register(cls, regnode, baseaddr, parent={}, size=None,
                        access=None, protection=None, resetValue=None,
                        resetMask=0):
        kwargs = {\
                  'description': _readtxt(regnode, 'description', required=True),
                  'access' : _readtxt(regnode, 'access', access, required=True),
                  # protection = _readtxt(regnode, 'protection', protection),
                  'resetMask' : _readint(regnode, 'resetMask', resetMask, parent=parent),
                  'displayName': _readtxt(regnode, 'displayName', '', parent=parent)
                  }
        kwargs['resetValue'] = _readint(regnode, 'resetValue', resetValue, 
                                        parent=parent, required=kwargs['resetMask'] != 0)

        args = [\
                # These are required even when inheriting from another register
                _readtxt(regnode, 'name', required=True),
                cls.parse_subblocks(regnode.pop('fields', parent.get('fields', [])), cls.parse_bitfield, access=kwargs['access']),
                _readint(regnode, 'addressOffset', required=True) + baseaddr,
                _readint(regnode, 'size', size, required=True),
                ]
        return args, kwargs

    @classmethod
    def _parse_arrays(cls, regnodelst):
        dimIndex = []
        for reg in regnodelst:
            dimidx = _readtxt(reg, 'dimIndex')
            if dimidx is None:
                dim = _readint(reg, 'dim', required=True)
                dimdx = range(dim)
            elif ',' in dimidx:
                dimidx = dimidx.split(',')
                try:
                    dimidx = map(int, dimidx)
                except ValueError:
                    pass
            elif '-' in dimidx:
                m=re.search('([0-9]+)-([0-9]+)', dimidx)
                dimidx = range( int(m.group(1)), int(m.group(2))+1 )
            dimIndex.extend(dimidx)
        return dimIndex
        
    @classmethod
    def parse_bitfield(cls, bitnode, parent={}, access=None):
        name = _readtxt(bitnode, 'name', parent=parent, required=True)
        if name.lower() == 'reserved':
            return None

        description = _readtxt(bitnode, 'description', '', parent=parent)
        bit_range=_readtxt(bitnode, 'bitRange', parent=parent)
        bit_offset=_readint(bitnode, 'bitOffset', parent=parent)
        bit_width=_readint(bitnode, 'bitWidth', parent=parent)
        msb=_readint(bitnode, 'msb', parent=parent)
        lsb=_readint(bitnode, 'lsb', parent=parent)
        if bit_range is not None:
            m=re.search('\[([0-9]+):([0-9]+)\]', bit_range)
            bit_offset=int(m.group(2))
            bit_width=1+(int(m.group(1))-int(m.group(2)))     
        elif msb is not None:
            bit_offset=lsb
            bit_width=1+(msb-lsb)

        access = _readtxt(bitnode, 'access', access, required=True)
        # modifiedWriteValues = _readtxt(bitnode, 'writeValueType')
        # writeConstraint = _readtxt(bitnode, 'writeConstraintType')
        # readAction = _readtxt(bitnode, 'readActionType')
        
        enumvals = bitnode.get('enumeratedValues', parent.get('enumeratedValues', []))
        if len(enumvals):
            # discard 'enumeratedValues' level attributes
            enumvals = enumvals.findall('enumeratedValue')

        enumvals = cls.parse_subblocks(enumvals, cls.parse_enumerated_value)

        return BitField(name, bit_offset, bit_width, values=enumvals, access=access, description=description, kwattrs=bitnode)

    @classmethod
    def parse_enumerated_value(cls, enumnode, parent={}):
        name =_readtxt(enumnode, 'name', parent=parent, required=True)
        description = _readtxt(enumnode, 'description', '', parent=parent)

        # isdefault values are simply ignored and assumed as reserved
        if _readtxt(enumnode, 'isDefault', False, parent=parent) == 'true':
            return None
        
        value = _readint(enumnode, 'value', parent=parent, required=True)
        return EnumeratedValue(name, value, description=description, kwattrs=enumnode)
