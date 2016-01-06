from xml.etree import ElementTree
from mmdev.parsers.deviceparser import DeviceParser, ParseException, RequiredValueError
from mmdev.device import CPU, Device, Peripheral, Register, BitField, EnumeratedValue
import re
import collections
import logging


def _readtxt(node, tag, default=None, parent={}, required=False, pop=True):
    if pop:
        x = node.pop(tag, parent.get(tag, default))
    else:
        x = node.get(tag, parent.get(tag, default))

    if required and x is None:
        raise RequiredValueError("Missing required value '%s' in node '%s'" % (tag, node['node'].findtext('name')))

    return x.text if isinstance(x, ElementTree.Element) else x

def _readint(node, tag, default=None, parent={}, required=False, pop=True):
    if pop:
        x = node.pop(tag, None)
    else:
        x = node.get(tag, None)

    if x is None:
        if required and default is None:
            raise RequiredValueError("Missing required value '%s' in node '%s'" % (tag, node['node'].findtext('name')))
                
        return parent.get(tag, default)
    else:
        x = x.text

    if x.lower().startswith('0x'):
        return int(x, 16)
    if x.startswith('#'):
        raise ParseException("Binary format not supported")

    return int(x)

def _node2dict(node):
    elements = { e.tag: e for e in node }
    elements.update(node.attrib)
    elements['node'] = node
    return elements


class SVDParser(DeviceParser):
    _raiseErr = True

    @classmethod
    def parse_block(cls, blknode, dtype={}, parent={}, **opts):
        blkattrs = []
        for blkattr in set(dtype).difference(opts):
            read = dtype[blkattr] or _readtxt
            try:
                val = read(blknode, blkattr, parent.get(blkattr), required=True)
            except ParseException as e:
                if cls._raiseErr:
                    raise e
                logging.critical(e.message)
            else:
                blkattrs.append(val)
        
        blkopts = {}
        for blkopt in opts:
            if blkopt in dtype:
                read = dtype[blkopt] or _readtxt
                opt = read(blknode, blkopt, parent.get(blkopt, opts[blkopt]))
            else:
                opt = opts[blkopt]
            blkopts[blkopt] = opt

        return blkattrs, blkopts

    @classmethod
    def parse_subblocks(cls, subblksnode, parser, *args, **kwargs):
        blks = []
        blkmap = {}
        derivedblks = []

        for blknode in subblksnode:
            blkmap[blknode.findtext('name')] = blknode
            if 'derivedFrom' in blknode.attrib:
                derivedblks.append((blknode, blknode.attrib['derivedFrom']))
                continue

            blk = parser(_node2dict(blknode), *args, **kwargs)
            if isinstance(blk, list):
                blks.extend(blk)
            elif blk is not None:
                blks.append(blk)

        for childnode, parent in derivedblks:
            blk = parser(_node2dict(childnode), *args, parent=_node2dict(blkmap[parent]), **kwargs)
            if isinstance(blk, list):
                blks.extend(blk)
            elif blk is not None:
                blks.append(blk)

        return blks


    @classmethod
    def parse_device(cls, devfile, raiseErr=True):
        cls._raiseErr = raiseErr
        devnode = _node2dict(ElementTree.parse(devfile).getroot())

        name = 'Device'
        mnem = _readtxt(devnode, 'name', required=True)
        # version = _readtxt(devnode, 'version', required=True)
        descr = _readtxt(devnode, 'description', required=True)
        addressUnitBits = _readint(devnode, 'addressUnitBits', required=True)
        width = _readint(devnode, 'width', required=True)
        vendor = _readtxt(devnode, 'vendor', '')

        regopts = { # 'size'      :   _readint(devnode, 'size'),
                    # 'access'    :   _readtxt(devnode, 'access'),
                    # 'protection':   _readtxt(devnode, 'protection'),
                    'resetValue':   _readint(devnode, 'resetValue'),
                    'resetMask' :   _readint(devnode, 'resetMask') }

        cpu_node = devnode.pop('cpu', None)
        if cpu_node is not None:
            cpu_node = _node2dict(cpu_node)
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

        pphs = cls.parse_subblocks(devnode.pop('peripherals'), cls.parse_peripheral, **regopts)

        return Device(mnem, pphs, cpu=cpu, fullname=name, descr=descr, width=width,
                      addressbits=addressUnitBits, vendor=vendor, kwattrs=devnode)

    # @classmethod
    # def parse_peripheral(cls, pphnode, parent={}, **regopts):
    #     pphnode = _node2dict(pphnode)

    #     attrs = collections.OrderedDict.fromkeys(['name', 'baseAddress', 'description'])
    #     attrs['baseAddress'] = _readint
    #     attrs.update(regopts)

    #     if 'size' not in regopts: attrs['size'] = _readint
    #     if 'access' not in regopts: attrs['access'] = _readint
    #     if 'protection' not in regopts: attrs['protection'] = _readint
    #     if 'resetValue' not in regopts: attrs['resetValue'] = _readint
    #     if 'resetMask' not in regopts: attrs['resetMask'] = _readint

    #     name, baseAddress, regopts = cls.parse_block(pphnode, attrs, **regopts)

    #     regs = cls.parse_subblocks(pphnode.pop('registers', parent.get('registers', [])), cls.parse_register, **regopts)

    #     return Peripheral(name, baseAddress, regs, descr=description, kwattrs=pphnode)

    @classmethod
    def parse_peripheral(cls, pphnode, parent={}, size=None, access=None,
                         protection=None, resetValue=None, resetMask=None):
        name = _readtxt(pphnode, 'name', parent=parent, required=True)
        pphaddr = _readint(pphnode, 'baseAddress', parent=parent, required=True)
        descr = _readtxt(pphnode,'description', parent=parent) 

        regopts = { # 'size': _readint(pphnode, 'size', parent.get('size', size)),
                    # 'access': _readtxt(pphnode, 'access', parent.get('access', access)),
                    # 'protection': _readtxt(pphnode, 'protection', parent.get('protection', protection)),
                    'resetValue': _readint(pphnode, 'resetValue', resetValue, parent=parent),
                    'resetMask': _readint(pphnode, 'resetMask', resetMask, parent=parent) }

        regs = cls.parse_subblocks(pphnode.pop('registers', parent.get('registers', [])), cls.parse_register, pphaddr, **regopts)

        return Peripheral(name, pphaddr, regs, descr=descr, kwattrs=pphnode)

    @classmethod
    def parse_register(cls, regnode, baseaddr, parent={}, size=None,
                       access=None, protection=None, resetValue=None,
                       resetMask=None):
        # These are required even when inheriting from another register
        try:
            name       = _readtxt(regnode, 'name', required=True)
            addr       = _readint(regnode, 'addressOffset', required=True) + baseaddr
            descr      = _readtxt(regnode, 'description', required=True)

            # size       = _readint(regnode, 'size', size, required=True)
            # access     = _readtxt(regnode, 'access', access)
            # protection = _readtxt(regnode, 'protection', protection)
            resetvalue = _readint(regnode, 'resetValue', resetValue, parent=parent, required=True)
            resetmask  = _readint(regnode, 'resetMask', resetMask, parent=parent, required=True)
        except ParseException as e:
            if cls._raiseErr:
                raise e
            logging.critical(e.message)
            return None

        dispname   = _readtxt(regnode, 'displayName', 'Register', parent=parent)
        bits = cls.parse_subblocks(regnode.pop('fields', parent.get('fields', [])), cls.parse_bitfield, access=access)

        dim = _readint(regnode, 'dim', parent=parent)
        if dim is None:
            return Register(name, addr, bits, resetvalue, resetmask,
                            fullname=dispname, descr=descr, kwattrs=regnode)

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
                                   addr + i*diminc,
                                   bits,
                                   resetvalue,
                                   resetmask, 
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
            attrs = _node2dict(enumvals)
            attrs.pop('enumeratedValue')
            bitnode['enumeratedValues'] = attrs
            enumvals = enumvals.findall('enumeratedValue')

        enumvals = cls.parse_subblocks(enumvals, cls.parse_enumerated_value)

        return BitField(name, bit_width << bit_offset, enumvals, descr=descr, kwattrs=bitnode)

    @classmethod
    def parse_enumerated_value(cls, enumnode, parent={}):
        name =_readtxt(enumnode, 'name', parent=parent, required=True)
        descr = _readtxt(enumnode, 'description', '', parent=parent)
        if _readtxt(enumnode, 'isdefault', parent=parent) != 'true':
            value = _readint(enumnode, 'value', parent=parent, required=True)
        else:
            value = name

        return EnumeratedValue(name, value, descr=descr, kwattrs=enumnode)
