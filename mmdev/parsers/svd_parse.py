from deviceparser import *
import xml.etree.ElementTree as ET


def _readint(x):
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
        addressUnitBits = _readint(svd.findtext('addressUnitBits'))
        width = _readint(svd.findtext('width'))
        vendor = svd.findtext('vendor', '')

        # defwidth = _readint(svd.findtext('size'))
        # defaccess = _readint(svd.findtext('access'))
        # defrval = _readint(svd.findtext('resetValue'))
        # defrmsk = _readint(svd.findtext('resetMask'))

        pphs = []
        for pphnode in svd.iter('peripheral'):
            pphs.append(cls.parse_peripheral(pphnode))

        return Device(mnem, pphs, fullname=name, descr=descr, width=width, vendor=vendor)

    @classmethod
    def parse_bitfield(cls, bitnode):
        mask = _readint(bitnode.findtext('bitWidth')) \
               << _readint(bitnode.findtext('bitOffset'))
        return BitField(bitnode.findtext('name'),
                        mask,
                        fullname=bitnode.findtext('displayName','BitField'),
                        descr=bitnode.findtext('description',''))

    @classmethod
    def parse_register(cls, regnode, baseaddr):
        bits = []
        for bitnode in regnode.findall('.//field'):
            bits.append(cls.parse_bitfield(bitnode))

        return Register(regnode.findtext('name'),
                        _readint(regnode.findtext('addressOffset')) + baseaddr,
                        bits,
                        fullname=regnode.findtext('displayName','Register'),
                        descr=regnode.findtext('description'),)

    @classmethod
    def parse_peripheral(cls, pphnode):
        pphaddr = _readint(pphnode.findtext('baseAddress'))
        regs = []
        for regnode in pphnode.findall('./registers/register'):
            regs.append(cls.parse_register(regnode, pphaddr))

        return Peripheral(pphnode.findtext('name'), 
                          pphaddr,
                          regs,
                          fullname=pphnode.findtext('displayName', 'Peripheral'),
                          descr=pphnode.findtext('description', ''))

