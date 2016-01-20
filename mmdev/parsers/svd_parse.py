from xml.etree import ElementTree
from mmdev.parsers.deviceparser import DeviceParser, ParseException, RequiredValueError
from mmdev.device import Device, CPU, Peripheral, Register, BitField, EnumeratedValue
import re
import logging


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
        super(SVDNode, self).__init__(**{ e.tag: e for e in node })
        self.name = node.findtext('name')
        self.update(node.attrib)

class SVDParser(DeviceParser):
    _raiseErr = True

    @classmethod
    def parse_subblocks(cls, subblksnode, parser, *args, **kwargs):
        blks = []
        blkmap = { blk.findtext('name'): blk for blk in subblksnode }
        for blknode in subblksnode:
            if 'derivedFrom' in blknode.attrib:
                parent = SVDNode(blkmap[blknode.attrib['derivedFrom']])
            else:
                parent = {}

            try:
                blk = parser(SVDNode(blknode), *args, parent=parent, **kwargs)
            except ParseException as e:
                if cls._raiseErr:
                    raise e
                logging.critical(e.message)
                continue

            if isinstance(blk, list):
                blks.extend(blk)
            elif blk is not None:
                blks.append(blk)

        return blks

    @classmethod
    def parse_device(cls, devfile, raiseErr=True):
        cls._raiseErr = raiseErr
        devnode = SVDNode(ElementTree.parse(devfile).getroot())

        try:
            name = 'Device'
            mnem = _readtxt(devnode, 'name', required=True)
            # version = _readtxt(devnode, 'version', required=True)
            descr = _readtxt(devnode, 'description', required=True)
            addressUnitBits = _readint(devnode, 'addressUnitBits', required=True)
            width = _readint(devnode, 'width', required=True)
            vendor = _readtxt(devnode, 'vendor', '')

            regopts = { 'size'      :   _readint(devnode, 'size'),
                        # 'access'    :   _readtxt(devnode, 'access'),
                        # 'protection':   _readtxt(devnode, 'protection'),
                        'resetValue':   _readint(devnode, 'resetValue'),
                        'resetMask' :   _readint(devnode, 'resetMask') }

            cpu_node = devnode.pop('cpu', None)
            if cpu_node is not None:
                cpu_node = SVDNode(cpu_node)
                cpu = CPU(_readtxt(cpu_node, 'name'),
                          _readtxt(cpu_node, 'revision'),
                          _readtxt(cpu_node, 'endian'),
                          _readint(cpu_node, 'mpuPresent'),
                          _readint(cpu_node, 'fpuPresent'),
                          # _readint(cpu_node, 'nvicPrioBits'),
                          # _readint(cpu_node, 'vtorPresent'),
                          kwattrs=cpu_node)
            else:
                cpu = None
        except ParseException as e:
            if cls._raiseErr:
                raise e
            logging.critical(e.message)
            return None

        pphs = cls.parse_subblocks(devnode.pop('peripherals'), cls.parse_peripheral, **regopts)

        return Device(mnem, width, addressUnitBits, pphs, cpu=cpu,
                      fullname=name, descr=descr, vendor=vendor,
                      kwattrs=devnode)

    @classmethod
    def parse_peripheral(cls, pphnode, parent={}, size=None, access=None,
                         protection=None, resetValue=None, resetMask=0):
        name = _readtxt(pphnode, 'name', parent=parent, required=True)
        pphaddr = _readint(pphnode, 'baseAddress', parent=parent, required=True)
        descr = _readtxt(pphnode,'description', parent=parent) 

        regopts = { 'size': _readint(pphnode, 'size', parent.get('size', size)),
                    # 'access': _readtxt(pphnode, 'access', parent.get('access', access)),
                    # 'protection': _readtxt(pphnode, 'protection', parent.get('protection', protection)),
                    'resetValue': _readint(pphnode, 'resetValue', resetValue, parent=parent),
                    'resetMask': _readint(pphnode, 'resetMask', resetMask, parent=parent) }

        regs = cls.parse_subblocks(pphnode.pop('registers', parent.get('registers', [])), cls.parse_register, pphaddr, **regopts)

        return Peripheral(name, pphaddr, regs, descr=descr, kwattrs=pphnode)

    @classmethod
    def parse_register(cls, regnode, baseaddr, parent={}, size=None,
                       access=None, protection=None, resetValue=None,
                       resetMask=0):
        # These are required even when inheriting from another register
        name       = _readtxt(regnode, 'name', required=True)
        addr       = _readint(regnode, 'addressOffset', required=True) + baseaddr
        descr      = _readtxt(regnode, 'description', required=True)

        size       = _readint(regnode, 'size', size, required=True)
        # access     = _readtxt(regnode, 'access', access)
        # protection = _readtxt(regnode, 'protection', protection)
        resetmask = _readint(regnode, 'resetMask', resetMask, parent=parent)
        resetvalue = _readint(regnode, 'resetValue', resetValue, 
                              parent=parent, required=resetmask != 0)

        dispname   = _readtxt(regnode, 'displayName', name, parent=parent)
        bits = cls.parse_subblocks(regnode.pop('fields', parent.get('fields', [])), cls.parse_bitfield, access=access)

        dim = _readint(regnode, 'dim', parent=parent)
        if dim is None:
            return Register(name, size, addr, bits, resetMask=resetmask,
                            resetValue=resetvalue, fullname=dispname,
                            descr=descr, kwattrs=regnode)

        diminc = _readint(regnode, 'dimIncrement', parent=parent, required=True)
        dimidx = _readtxt(regnode, 'dimIndex', parent=parent)
        if dimidx is None:
            dimdx = map(str, range(dim))
        elif ',' in dimidx:
            dimidx = dimidx.split(',')
        elif '-' in dimidx:
            m=re.search('([0-9]+)-([0-9]+)', dimidx)
            dimidx = map(str, range(int(m.group(1)),int(m.group(2))+1))

        regblk = []
        for i, idx in enumerate(dimidx):
            regblk.append(Register(name % idx,
                                   size,
                                   addr + i*diminc,
                                   bits,
                                   resetMask=resetmask, 
                                   resetValue=resetvalue,
                                   fullname=dispname % idx if '%s' in dispname else dispname,
                                   descr=descr,
                                   kwattrs=regnode))
        return regblk


    @classmethod
    def parse_bitfield(cls, bitnode, parent={}, access=None):
        name = _readtxt(bitnode, 'name', parent=parent, required=True)
        if name.lower() == 'reserved':
            return None

        descr = _readtxt(bitnode, 'description', '', parent=parent)
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

        # access = _readtxt(bitnode, 'access', access)
        # modifiedWriteValues = _readtxt(bitnode, 'writeValueType')
        # writeConstraint = _readtxt(bitnode, 'writeConstraintType')
        # readAction = _readtxt(bitnode, 'readActionType')
        
        enumvals = bitnode.get('enumeratedValues', parent.get('enumeratedValues', []))
        if len(enumvals):
            # discard 'enumeratedValues' level attributes
            nodes = list(enumvals)
            attrs = SVDNode(enumvals)
            attrs.pop('enumeratedValue')
            bitnode['enumeratedValues'] = attrs
            enumvals = enumvals.findall('enumeratedValue')

        enumvals = cls.parse_subblocks(enumvals, cls.parse_enumerated_value)

        return BitField(name, bit_width, bit_offset, values=enumvals, descr=descr, kwattrs=bitnode)

    @classmethod
    def parse_enumerated_value(cls, enumnode, parent={}):
        name =_readtxt(enumnode, 'name', parent=parent, required=True)
        descr = _readtxt(enumnode, 'description', '', parent=parent)
        if _readtxt(enumnode, 'isdefault', parent=parent) != 'true':
            value = _readint(enumnode, 'value', parent=parent, required=True)
        else:
            value = name

        return EnumeratedValue(name, value, descr=descr, kwattrs=enumnode)
