from xml.etree import ElementTree
from mmdev.parsers.deviceparser import DeviceParser, ParseException
from mmdev.device import CPU, Device, Peripheral, Register, BitField, EnumeratedValue
import re
import collections


def _readtxt(node, tag, default=None, required=False, pop=True):
    if pop:
        x = node.pop(tag, default)
    else:
        x = node.get(tag, default)

    if required and x is None:
        raise ParseException("Missing required value '%s' in node:\n%s" % 
                             (tag, node))

    return x.text if isinstance(x, ElementTree.Element) else x

def _readint(node, tag, default=None, required=False, pop=True):
    if pop:
        x = node.pop(tag, None)
    else:
        x = node.get(tag, None)

    if x is None:
        if required and default is None:
            raise ParseException("Missing required value '%s' in node:\n%s" % 
                                 (tag, node))
        return default
    else:
        x = x.text

    if x.lower().startswith('0x'):
        return int(x, 16)
    if x.startswith('#'):
        raise Exception("Binary format not support")

    return int(x)

def _node2dict(node):
    elements = { e.tag: e for e in node }
    elements.update(node.attrib)
    return elements


class SVDParser(DeviceParser):

    @classmethod
    def parse_device(cls, devfile):
        devnode = _node2dict(ElementTree.parse(devfile).getroot())

        name = 'Device'
        mnem = _readtxt(devnode, 'name', required=True)
        version = _readtxt(devnode, 'version', required=True)
        descr = _readtxt(devnode, 'description', required=True)
        addressUnitBits = _readint(devnode, 'addressUnitBits', required=True)
        width = _readint(devnode, 'width', required=True)
        vendor = _readtxt(devnode, 'vendor', '')

        regopts = { 'size'      :   _readint(devnode, 'size'),
                    'access'    :   _readtxt(devnode, 'access'),
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
                      _readint(cpu_node, 'nvicPrioBits'),
                      _readint(cpu_node, 'vtorPresent'),
                      kwattrs=cpu_node)
        else:
            cpu = None

        pphs = []
        for pphnode in devnode.pop('peripherals'):
            pphs.append(cls.parse_peripheral(pphnode, **regopts))

        return Device(mnem, pphs, cpu=cpu, fullname=name, descr=descr, width=width,
                      addressbits=addressUnitBits, vendor=vendor, kwattrs=devnode)

    @classmethod
    def parse_peripheral(cls, pphnode, size=None, access=None, resetValue=None, resetMask=None):
        pphnode = _node2dict(pphnode)

        pphaddr = _readint(pphnode, 'baseAddress')

        regopts = { 'size': _readint(pphnode, 'size', size),
                    'access': _readtxt(pphnode, 'access', size),
                    'resetValue': _readint(pphnode, 'resetValue', resetValue),
                    'resetMask': _readint(pphnode, 'resetMask', resetMask)}

        regs = []
        for regnode in pphnode.pop('registers', []):
            regs.extend(cls.parse_register(regnode, pphaddr, **regopts))

        return Peripheral(_readtxt(pphnode, 'name'), 
                          pphaddr,
                          regs,
                          fullname=_readtxt(pphnode, 'displayName', 'Peripheral'),
                          descr=_readtxt(pphnode, 'description', ''))

    @classmethod
    def parse_register(cls, regnode, baseaddr, size=None, access=None, resetValue=None, resetMask=None):
        regnode = _node2dict(regnode)

        bits = []
        for bitnode in regnode.pop('fields', []):
            field = cls.parse_bitfield(bitnode)
            if field is not None:
                bits.append(field)

        name       = _readtxt(regnode, 'name')
        addr       = _readint(regnode, 'addressOffset', required=True) + baseaddr

        size       = _readint(regnode, 'size', size, required=True)
        access     = _readtxt(regnode, 'access', access)
        resetvalue = _readint(regnode, 'resetValue', resetValue)
        resetmask  = _readint(regnode, 'resetMask', resetMask, required=True)

        dispname   = _readtxt(regnode, 'displayName', 'Register')
        descr      = _readtxt(regnode, 'description')

        # assume all bit reset values are '0's if resetvalue is not specified
        if resetvalue is None:
            resetvalue = 0

        dim = _readint(regnode, 'dim')
        if dim is None:
            return [Register(name, addr, bits, resetvalue, resetmask,
                             fullname=dispname, descr=descr, kwattrs=regnode)]

        diminc = _readint(regnode, 'dimIncrement', required=True)
        dimidx = _readtxt(regnode, 'dimIndex')
        
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
    def parse_bitfield(cls, bitnode):
        bitnode = _node2dict(bitnode)

        if _readtxt(bitnode, 'name', required=True, pop=False).lower() == 'reserved':
            return None

        bit_range=_readtxt(bitnode, 'bitRange')
        bit_offset=_readint(bitnode, 'bitOffset')
        bit_width=_readint(bitnode, 'bitWidth')
        msb=_readint(bitnode, 'msb')
        lsb=_readint(bitnode, 'lsb')
        if bit_range is not None:
            m=re.search('\[([0-9]+):([0-9]+)\]', bit_range)
            bit_offset=int(m.group(2))
            bit_width=1+(int(m.group(1))-int(m.group(2)))     
        elif msb is not None:
            bit_offset=lsb
            bit_width=1+(msb-lsb)

        enumvals = cls.parse_enumerated_values(bitnode.pop('enumeratedValues', []))

        return BitField(_readtxt(bitnode, 'name'),
                        bit_width << bit_offset,
                        list(enumvals),
                        fullname=_readtxt(bitnode, 'displayName','BitField'),
                        descr=_readtxt(bitnode, 'description',''),
                        kwattrs=bitnode)

    @classmethod
    def parse_enumerated_values(cls, enumnode):
        # ignore group attributes for now
        # name = _readtxt(enumnode, 'name')
        # usage = _readtxt(enumnode, 'usage')

        for e in enumnode:
            e = _node2dict(e)
            name =_readtxt(e, 'name', required=True)
            descr = _readtxt(e, 'description', '')
            if _readtxt(e, 'isdefault') != 'true':
                value = _readint(e, 'value', required=True)
            else:
                value = name
            yield EnumeratedValue(name, value, descr=descr, kwattrs=e)
