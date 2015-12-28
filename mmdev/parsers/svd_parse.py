import xml.etree.ElementTree as ET
from mmdev.parsers.deviceparser import DeviceParser, ParseException
from mmdev.device import CPU, Device, Peripheral, Register, BitField
import re


def _readtxt(node, attr, default=None, required=False):
    x = node.findtext(attr, default)

    if required and x is None:
        raise ParseException("Missing required value '%s' in node '%s':\n%s" % 
                             (attr, node.tag, { n.tag: n.text for n in node.getchildren() }))

    return x

def _readint(node, attr, default=None, required=False):
    x = node.findtext(attr)

    if x is None:
        if required and default is None:
            raise ParseException("Missing required value '%s' in node '%s':\n%s" % 
                                 (attr, node.tag, { n.tag: n.text for n in node.getchildren() }))
        return default

    if isinstance(x, basestring):
        if x.lower().startswith('0x'):
            return int(x, 16)
        if x.startswith('#'):
            raise Exception("Binary format not support")
    return int(x)


class SVDParser(DeviceParser):
    @classmethod
    def parse_device(cls, devfile):

        svd = ET.parse(devfile).getroot()

        name = 'Device'
        mnem = _readtxt(svd, 'name')
        descr = _readtxt(svd, 'description')
        addressUnitBits = _readint(svd, 'addressUnitBits', required=True)
        width = _readint(svd, 'width', required=True)
        vendor = _readtxt(svd, 'vendor', '')

        regopts = { 'size'      :   _readint(svd, 'size'),
                    'resetValue':   _readint(svd, 'resetValue'),
                    'resetMask' :   _readint(svd, 'resetMask') }

        cpu_node = svd.find('./cpu')
        cpu = CPU(_readtxt(cpu_node, 'name'),
                  _readtxt(cpu_node, 'revision'),
                  _readtxt(cpu_node, 'endian'),
                  _readint(cpu_node, 'mpuPresent'),
                  _readint(cpu_node, 'fpuPresent'),
                  _readint(cpu_node, 'nvicPrioBits'),
                  _readint(cpu_node, 'vtorPresent'))

        pphs = []
        for pphnode in svd.iter('peripheral'):
            pphs.append(cls.parse_peripheral(pphnode, **regopts))

        return Device(mnem, pphs, cpu=cpu, fullname=name, descr=descr, width=width,
                      addressbits=addressUnitBits, vendor=vendor)

    @classmethod
    def parse_peripheral(cls, pphnode, size=None, resetValue=None, resetMask=None):
        pphaddr = _readint(pphnode, 'baseAddress')

        regopts = { 'size': _readint(pphnode, 'size', size),
                    'resetValue': _readint(pphnode, 'resetValue', resetValue),
                    'resetMask': _readint(pphnode, 'resetMask', resetMask)}

        regs = []
        for regnode in pphnode.findall('./registers/register'):
            regs.extend(cls.parse_register(regnode, pphaddr, **regopts))

        return Peripheral(_readtxt(pphnode, 'name'), 
                          pphaddr,
                          regs,
                          fullname=_readtxt(pphnode, 'displayName', 'Peripheral'),
                          descr=_readtxt(pphnode, 'description', ''))

    @classmethod
    def parse_register(cls, regnode, baseaddr, size=None, resetValue=None, resetMask=None):
        bits = []
        for bitnode in regnode.findall('.//field'):
            field = cls.parse_bitfield(bitnode)
            if field is not None:
                bits.append(field)

        name       = _readtxt(regnode, 'name')
        addr       = _readint(regnode, 'addressOffset', required=True) + baseaddr
        size       = _readint(regnode, 'size', size, required=True)
        resetmask  = _readint(regnode, 'resetMask', resetMask, required=True)
        resetvalue = _readint(regnode, 'resetValue', resetValue)
        dispname   = _readtxt(regnode, 'displayName', 'Register')
        descr      = _readtxt(regnode, 'description')

        # assume all bit reset values are '0's if resetvalue is not specified
        if resetvalue is None:
            resetvalue = 0

        dim = _readint(regnode, 'dim')
        if dim is None:
            return [Register(name, addr, bits, resetvalue, resetmask,
                             fullname=dispname, descr=descr)]

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
                                   descr=descr))
        return regblk


    @classmethod
    def parse_bitfield(cls, bitnode):
        # enumerated_values = []
        # for enumerated_value_node in bitnode.findall("./enumeratedValues/enumeratedValue"):
        #     enumerated_values.append(cls._parse_enumerated_value(enumerated_value_node))
			
        if _readtxt(bitnode, 'name', required=True).lower() == 'reserved':
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
        return BitField(_readtxt(bitnode, 'name'),
                        bit_width << bit_offset,
                        fullname=_readtxt(bitnode, 'displayName','BitField'),
                        descr=_readtxt(bitnode, 'description',''))

