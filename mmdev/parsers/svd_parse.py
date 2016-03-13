from xml.etree import ElementTree
from mmdev.parsers.deviceparser import DeviceParser, ParseException, RequiredValueError
from mmdev.components import CPU, Device, Peripheral, Register, BitField, EnumeratedValue
from mmdev.arrays import RegisterArray

import re
import logging
from collections import OrderedDict

logger = logging.getLogger(__name__)

array_suffex = r'\[%s\]|_?%s'

get_suffix = lambda name, exp=array_suffex: re.search(exp, name)
get_basename = lambda name, exp=array_suffex: re.sub(exp, '', name)


def _readtxt(node, tag, default=None, parent={}, required=False, pop=True):
    if pop:
        x = node.pop(tag, parent.get(tag, default))
    else:
        x = node.get(tag, parent.get(tag, default))

    if required and x is None:
        raise RequiredValueError("Missing required value '%s' in node '%s'" % (tag, node.name))

    return x.text if isinstance(x, ElementTree.Element) else x

def _readint(node, tag, default=None, parent={}, required=False, pop=True):
    if pop:
        x = node.pop(tag, None)
    else:
        x = node.get(tag, None)

    if x is None:
        if required and default is None:
            raise RequiredValueError("Missing required value '%s' in node '%s'" % (tag, node.name))
                
        return parent.get(tag, default)
    else:
        x = x.text

    if x.lower().startswith('0x'):
        return int(x, 16)
    if x.startswith('#'):
        raise ParseException("Binary format not supported")

    return int(x)

class SVDNode(dict):
    def __init__(self, node, *args, **kwargs):
        super(SVDNode, self).__init__()

        for e in node:
            if e.tag not in self:
                self[e.tag] = e
                continue

            if not isinstance(self[e.tag], list):
                self[e.tag] = [self[e.tag]]
            self[e.tag].append(e)

        self.name = node.findtext('name')
        self.update(node.attrib)


class SVDParser(DeviceParser):
    _raiseErr = True
    _supcls = None

    @classmethod
    def parse_subblocks(cls, subblksnode, parser, *args, **kwargs):
        blkmap = OrderedDict()
        for blknode in subblksnode:
            # We'll put blocks and block arrays that have the same base name
            # in the same index
            name = get_basename(blknode.findtext('name'))
            if name in blkmap:
                blkmap[name].append(blknode)
            else:
                blkmap[name] = [blknode]

        subblocks = []
        for name, blknodelst in blkmap.iteritems():
            svdnodes = []
            parents = []

            # We iterate through the list, inheriting from any parents, and
            for blknode in blknodelst:
                # Since a parent may actually be an array block, iterate through
                # the parent list and find the first one that has the same
                # suffix (or lack of one)
                parent = {}
                if 'derivedFrom' in blknode.attrib:
                    bsfx = get_suffix(blknode.findtext('name'))
                    if bsfx: 
                        bsfx = bsfx.group()

                    pname = get_basename(blknode.attrib['derivedFrom'])
                    for pblk in blkmap[pname]:
                        psfx = get_suffix(pblk.findtext('name'))
                        if psfx: 
                            psfx = psfx.group()
                        if psfx == bsfx:
                            parent = SVDNode(pblk)
                            break
                parents.append(parent)
                svdnodes.append( SVDNode(blknode) )

            if len(svdnodes) == 1 or parser != cls.parse_register:
                svdnodes = svdnodes.pop()
                parents = parents.pop()

            try:
                blk = parser(svdnodes, *args, parent=parents, **kwargs)
            except ParseException as e:
                if cls._raiseErr:
                    raise e
                logger.critical(e.message)
                continue

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
            name = 'Device'
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

            # cpu_node = devnode.pop('cpu', None)
            # if cpu_node is not None:
            #     cpu_node = SVDNode(cpu_node)
            #     cpu = CPU(_readtxt(cpu_node, 'name'),
            #               _readtxt(cpu_node, 'revision'),
            #               _readtxt(cpu_node, 'endian'),
            #               _readint(cpu_node, 'mpuPresent'),
            #               _readint(cpu_node, 'fpuPresent'),
            #               # _readint(cpu_node, 'nvicPrioBits'),
            #               # _readint(cpu_node, 'vtorPresent'),
            #               kwattrs=cpu_node)
            # else:
            #     cpu = None
        except ParseException as e:
            if cls._raiseErr:
                raise e
            logger.critical(e.message)
            return None

        pphs = cls.parse_subblocks(devnode.pop('peripherals'), cls.parse_peripheral, **regopts)

        args = mnem, pphs, addressUnitBits, width, #cpu=cpu,
        kwargs = dict(displayName=name, description=description, vendor=vendor,
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
                    'resetMask': _readint(pphnode, 'resetMask', resetMask, parent=parent) }

        regs = cls.parse_subblocks(pphnode.pop('registers', parent.get('registers', [])), 
                                   cls.parse_register, pphaddr, **regopts)

        # addressBlocks can be either a list or a single instance
        # here we force it into a list
        addrblocks = pphnode.pop('addressBlock', parent.get('addressBlock'))
        if not isinstance(addrblocks, list):
            addrblocks = [addrblocks]

        pphblk = []
        for addrblk in map(SVDNode, addrblocks):
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
                       resetMask=0):
        if not isinstance(regnode, list):
            parent = parent or {}
            (name, bits, addr, size), kwargs = cls._parse_register(regnode, baseaddr, parent=parent,
                                                                   size=size, access=access,
                                                                   protection=protection,
                                                                   resetValue=resetValue,
                                                                   resetMask=resetMask)
            dim = _readint(regnode, 'dim', parent=parent, pop=False)
            if dim is None:
                return Register(name, bits, addr, size, **kwargs)

            kwargs['suffix'] = get_suffix(name).group()
            kwargs['displayName'] = get_basename(kwargs['displayName'])
            name = get_basename(name)

            dimInc = _readint(regnode, 'dimIncrement', default=size, parent=parent, required=True)
            dimIndex = cls._parse_arrays([regnode])

            return RegisterArray(name, bits, addr, size, dimIndex, elementSize=dimInc, **kwargs)

        regnodelst = regnode
        parentlst = [{}]*len(regnodelst) if parent is None else parent
        masterCnt = 0
        for i in range(len(regnodelst)):
            dim = _readint(regnodelst[i], 'dim', parent=parentlst[i], pop=False)

            # Ah, if one of the elements has no 'dim' element then this must be the
            # master element.
            # Otherwise, we just assume this is a collection of register arrays
            # and use the first reg as a template for the rest
            if dim is None:
                masterCnt += 1
                masterIdx = i
                hasmaster = True

        if masterCnt > 1:
            raise ParseException("Non-unique identifier for register %s" % name)
        elif masterCnt == 0:
            templatereg, parent = regnodelst[0], parentlst[0]
            hasmaster = False
        else:
            templatereg, parent = regnodelst.pop(masterIdx), parentlst.pop(masterIdx)

        (name, bits, addr, size), kwargs = cls._parse_register(templatereg, baseaddr,
                                                               parent=parent, size=size,
                                                               access=access,
                                                               protection=protection,
                                                               resetValue=resetValue,
                                                               resetMask=resetMask)

        if hasmaster:
            # Grab the first array and use it as the template
            (tname, tbits, taddr, tsize), tkwargs = cls._parse_register(regnodelst[0], baseaddr,
                                                                        parent=parentlst[0], size=size,
                                                                        access=access,
                                                                        protection=protection,
                                                                        resetValue=resetValue,
                                                                        resetMask=resetMask)
            # Strip the suffix off the names
            kwargs['suffix']      = get_suffix(tname).group()
            tkwargs['displayName'] = get_basename(tkwargs['displayName'])
            tname = get_basename(tname)
            templatereg = Register(tname, tbits, taddr, tsize, **tkwargs)
        else:
            # No template needed, just use the properties of the array itself
            templatereg = None
            kwargs['suffix'] = get_suffix(name).group()
            kwargs['displayName'] = get_basename(kwargs['displayName'])
            name = get_basename(name)

        # dimIncrement has to be the same across a register array, so just take
        # it from the first one
        dimInc = _readint(regnodelst[0], 'dimIncrement', default=size, parent=parentlst[0], required=True)

        # Concatenate the index from all found register arrays
        dimIndex = cls._parse_arrays(regnodelst)

        return RegisterArray(name, bits, addr, size, dimIndex,
                             elementTemplate=templatereg, elementSize=dimInc, **kwargs)

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
