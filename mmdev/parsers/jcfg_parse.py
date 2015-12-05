import json
from itertools import imap
from mmdev.parsers.deviceparser import DeviceParser
from mmdev.device import Device, Peripheral, Register, BitField


def _readint(x):
    try:
        return int(x)
    except ValueError:
        return int(x, 16)


class JCFGParser(DeviceParser):
    @classmethod
    def parse_peripheral(cls, pphname, pphnode, devfile):
        regs = []
        for regnode in imap(devfile['registers'].get, pphnode['registers']):
            regs.append(cls.parse_register(regnode, devfile))

        return Peripheral(pphname, 
                          _readint(pphnode['addr']),
                          regs,
                          fullname=pphnode.get('name','Peripheral'),
                          descr=pphnode.get('descr',''))

    @classmethod
    def parse_register(cls, regnode, devfile):
        bits = []
        for bfnode in imap(devfile['bitfields'].get, regnode['bitfields']):
            bits.append(cls.parse_bitfield(bfnode))

        return Register(regnode['mnemonic'],
                        _readint(regnode['addr']),
                        bits,
                        fullname=regnode.get('name','Register'),
                        descr=regnode.get('descr',''))


    @classmethod
    def parse_bitfield(cls, bfnode):
        return BitField(bfnode['mnemonic'], 
                        _readint(bfnode['mask']),
                        fullname=bfnode.get('name','BitField'),
                        descr=bfnode.get('descr',''))

    @classmethod
    def parse_device(cls, devfile):
        if isinstance(devfile, basestring):
            import re
            fname = re.sub('\..*', '', devfile)
            with open(devfile) as fh:
                devfile = json.load(fh)
        else:
            fname = fh.name
            devfile = json.load(fh, **kwargs)

        name = devfile.get('name', 'Device')
        mnem = devfile['mnemonic'] if devfile.get('mnemonic', '') else fname
        descr = devfile.get('descr', '')
        width = devfile.get('width',32)
        vendor = devfile.get('vendor', '')

        pphs = []
        for pphname, pphnode in devfile['blocks'].iteritems():
            pphs.append(cls.parse_peripheral(pphname, pphnode, devfile))

        return Device(mnem, pphs,
                      fullname=name, descr=descr, width=width, vendor=vendor)
