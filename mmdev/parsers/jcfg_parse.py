from mmdev.parsers.deviceparser import DeviceParser, ParseException, RequiredValueError
from mmdev.device import Device
from mmdev.components import Peripheral, Register, BitField, EnumeratedValue
import json


def _readtxt(node, tag, default=None, parent={}, required=False, pop=False):
    if pop:
        x = node.pop(tag, parent.get(tag, default))
    else:
        x = node.get(tag, parent.get(tag, default))

    if required and x is None:
        raise RequiredValueError("Missing required value '%s' in node '%s'" % (tag, node))

    return x


def _readint(node, tag, default=None, parent={}, required=False, pop=False):
    if pop:
        x = node.pop(tag, None)
    else:
        x = node.get(tag, None)

    if x is None:
        if required and default is None:
            raise RequiredValueError("Missing required value '%s' in node '%s'" % (tag, node))
                
        return parent.get(tag, default)

    try:
        return int(x)
    except ValueError:
        return int(x, 16)        


class JCFGParser(DeviceParser):

    @classmethod
    def parse_peripheral(cls, pphname, pphnode):
        regs = []
        for regname, regnode in pphnode.get('registers', {}).iteritems():
            regs.append(cls.parse_register(regname, regnode))

        return Peripheral(pphname, 
                          regs,
                          _readint(pphnode, 'address', required=True),
                          _readint(pphnode, 'size', required=True),
                          displayName=_readtxt(pphnode, 'displayName', ''),
                          descr=_readtxt(pphnode, 'description',''))

    @classmethod
    def parse_register(cls, regname, regnode):
        bits = []
        for bfname, bfnode in regnode.get('bitfields', {}).iteritems():
            bits.append(cls.parse_bitfield(bfname, bfnode))

        return Register(regname,
                        bits,
                        _readint(regnode, 'address', required=True),
                        _readint(regnode, 'size', required=True),
                        access=_readtxt(regnode, 'access', 'read-write'),
                        displayName=_readtxt(regnode, 'displayName',''),
                        descr=_readtxt(regnode, 'description',''))


    @classmethod
    def parse_bitfield(cls, bfname, bfnode):
        evals = []
        for evname, evnode in bfnode.get('enumeratedValues', {}).iteritems():
            evals.append(cls.parse_enumerated_value(evname, evnode))

        return BitField(bfname,
                        _readint(bfnode, 'offset', required=True),
                        _readint(bfnode, 'width', required=True),
                        evals,
                        access=_readtxt(bfnode, 'access', 'read-write'),
                        displayName=_readtxt(bfnode, 'displayName',''),
                        descr=_readtxt(bfnode, 'description',''))

    @classmethod
    def parse_enumerated_value(cls, evname, evnode):
        return EnumeratedValue(evname,
                               _readint(evnode, 'value', required=True),
                               displayName=_readtxt(evnode, 'displayName',''),
                               descr=_readtxt(evnode, 'description',''))

    @classmethod
    def parse_device(cls, devfile, raiseErr=True):
        cls._raiseErr = raiseErr

        if isinstance(devfile, basestring):
            import os
            fname = devfile
            with open(devfile) as fh:
                devfile = json.load(fh)
        else:
            fname = fh.name
            devfile = json.load(fh, **kwargs)

        path, fname = os.path.split(fname)
        fname = os.path.splitext(fname)[0]

        devfile = devfile['device'] # 'device' is the only node that exists at
                                    # the top level

        pphs = []
        for pphname, pphnode in devfile['peripherals'].iteritems():
            pphs.append(cls.parse_peripheral(pphname, pphnode))

        return Device(_readtxt(devfile, 'mnemonic', required=True),
                      pphs, 
                      _readint(devfile, 'lane_width', required=True), 
                      _readint(devfile, 'bus_width', required=True), 
                      displayName=_readtxt(devfile, 'displayName', fname), 
                      descr=_readtxt(devfile, 'description', ''), 
                      vendor=_readtxt(devfile, 'vendor', ''))
