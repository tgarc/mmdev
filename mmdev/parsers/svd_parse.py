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

        dev = Device(mnem, fullname=name, descr=descr, width=width, vendor=vendor)
        for pphnode in svd.iter('peripheral'):
            pph = cls.parse_peripheral(pphnode)
            dev._attach_subblock(pph)

        return dev

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
        reg = Register(regnode.findtext('name'),
                       _readint(regnode.findtext('addressOffset')) + baseaddr,
                       fullname=regnode.findtext('displayName','Register'),
                       descr=regnode.findtext('description'),)
        for bitnode in regnode.findall('.//field'):
            bits = cls.parse_bitfield(bitnode)
            reg._attach_subblock(bits)

        return reg

    @classmethod
    def parse_peripheral(cls, pphnode):
        pphaddr = _readint(pphnode.findtext('baseAddress'))
        pph = Peripheral(pphnode.findtext('name'), 
                         pphaddr,
                         fullname=pphnode.findtext('displayName', 'Peripheral'),
                         descr=pphnode.findtext('description', ''))

        for regnode in pphnode.findall('./registers/register'):
            reg = cls.parse_register(regnode, pphaddr)
            pph._attach_subblock(reg)

        return pph
