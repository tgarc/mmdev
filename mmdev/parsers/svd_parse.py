import xml.etree.ElementTree as ET
from mmdev.parsers.deviceparser import DeviceParser
from mmdev.device import Device, Peripheral, Register, BitField
import re

def _readint(node, attr, default=None, required=False):
    x = node.findtext(attr)

    if x is None:
        if required and default is None:
            raise Exception("Missing required value '%s'" % attr)
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
        mnem = svd.findtext('name')
        descr = svd.findtext('description')
        addressUnitBits = _readint(svd, 'addressUnitBits', required=True)
        width = _readint(svd, 'width', required=True)
        vendor = svd.findtext('vendor', '')

        regopts = { 'size':_readint(svd, 'size'),
                    'resetValue': _readint(svd, 'resetValue'),
                    'resetMask': _readint(svd, 'resetMask')}

        pphs = []
        for pphnode in svd.iter('peripheral'):
            pphs.append(cls.parse_peripheral(pphnode, **regopts))

        return Device(mnem, pphs, fullname=name, descr=descr, width=width,
                      addressbits=addressUnitBits, vendor=vendor)

    @classmethod
    def parse_peripheral(cls, pphnode, size=None, resetValue=None, resetMask=None):
        pphaddr = _readint(pphnode, 'baseAddress')

        regopts = { 'size': _readint(pphnode, 'size', size),
                    'resetValue': _readint(pphnode, 'resetValue', resetValue),
                    'resetMask': _readint(pphnode, 'resetMask', resetMask)}

        regs = []
        for regnode in pphnode.findall('./registers/register'):
            regs.append(cls.parse_register(regnode, pphaddr, **regopts))

        return Peripheral(pphnode.findtext('name'), 
                          pphaddr,
                          regs,
                          fullname=pphnode.findtext('displayName', 'Peripheral'),
                          descr=pphnode.findtext('description', ''))

    @classmethod
    def parse_register(cls, regnode, baseaddr, size=None, resetValue=None, resetMask=None):
        bits = []
        for bitnode in regnode.findall('.//field'):
            bits.append(cls.parse_bitfield(bitnode))

        return Register(regnode.findtext('name'),
                        _readint(regnode, 'addressOffset', required=True) + baseaddr,
                        bits,
                        _readint(regnode, 'resetValue', resetValue, required=True),
                        _readint(regnode, 'resetMask', resetMask, required=True),
                        fullname=regnode.findtext('displayName','Register'),
                        descr=regnode.findtext('description'))

    @classmethod
    def parse_bitfield(cls, bitnode):
        enumerated_values = []
        for enumerated_value_node in bitnode.findall("./enumeratedValues/enumeratedValue"):
            enumerated_values.append(self._parse_enumerated_value(enumerated_value_node))
			
        bit_range=bitnode.findtext('bitRange')
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
        return BitField(bitnode.findtext('name'),
                        bit_width << bit_offset,
                        fullname=bitnode.findtext('displayName','BitField'),
                        descr=bitnode.findtext('description',''))

