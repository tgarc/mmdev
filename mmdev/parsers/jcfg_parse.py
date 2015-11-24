from deviceparser import *
import json
from itertools import imap


def _readint(x):
    try:
        return int(x)
    except ValueError:
        return int(x, 16)


class JCFGParser(DeviceParser):
    @classmethod
    def parse_peripheral(cls, pphname, pphnode, devfile):
        pph = Peripheral(pphname, 
                         _readint(pphnode['addr']),
                         fullname=pphnode.get('name','Peripheral'),
                         descr=pphnode.get('descr',''))

        for regnode in imap(devfile['registers'].get, pphnode['registers']):
            reg = cls.parse_register(regnode, devfile)
            pph._attach_subblock(reg)

        return pph

    @classmethod
    def parse_register(cls, regnode, devfile):
        reg = Register(regnode['mnemonic'],
                       _readint(regnode['addr']),
                       fullname=regnode.get('name','Register'),
                       descr=regnode.get('descr',''))

        for bfnode in imap(devfile['bitfields'].get, regnode['bitfields']):
            bits = cls.parse_bitfield(bfnode)
            reg._attach_subblock(bits)

        return reg

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

        dev = Device(mnem, fullname=name, descr=descr, width=width, vendor=vendor)
        for pphname, pphnode in devfile['blocks'].iteritems():
            pph = cls.parse_peripheral(pphname, pphnode, devfile)
            dev._attach_subblock(pph)

        return dev
