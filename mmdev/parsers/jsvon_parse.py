import json, re
from mmdev.parsers.deviceparser import DeviceParser, ParseException, RequiredValueError
from mmdev.components import Device, Peripheral, Port, Register, BitField, EnumeratedValue, DebugPort, AccessPort
from mmdev.blocks import DeviceBlock
from mmdev import utils


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


class JSVONParser(DeviceParser):
    _raiseErr = True
    _supcls = None

    @classmethod
    def from_devfile(cls, devfile, raiseErr=True, supcls=None):
        cls._raiseErr = raiseErr
        cls._supcls = supcls

        with open(devfile) as fh:
            devfile = json.load(fh)

        for k, v in devfile.iteritems():
            cameltype = re.sub(r'(?!^)([A-Z][a-z0-9]+)', r'_\1', k).lower()

            try:
                parser = getattr(cls, 'parse_' + cameltype)
            except AttributeError:
                raise AttributeError("No '%s' parser found" % k)

            # don't support multiple nodes at the top level
            return parser(v.pop('mnemonic'), v)

    @classmethod
    def parse_port(cls, portname, portnode):
        regs = []
        for regname, regnode in portnode.get('registers', {}).iteritems():
            regs.append(cls.parse_register(regname, regnode))

        return Port(portname, 
                    regs,
                    _readint(portnode, 'port', required=True),
                    _readint(portnode, 'size', required=True),
                    _readint(portnode, 'laneWidth', required=True), 
                    _readint(portnode, 'busWidth', required=True), 
                    displayName=_readtxt(portnode, 'displayName', ''),
                    description=_readtxt(portnode, 'description',''))

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
                          description=_readtxt(pphnode, 'description',''))

    @classmethod
    def parse_register(cls, regname, regnode):
        bits = []
        for bfname, bfnode in regnode.get('bitFields', {}).iteritems():
            bits.append(cls.parse_bitfield(bfname, bfnode))

        return Register(regname,
                        bits,
                        _readint(regnode, 'address', required=True),
                        _readint(regnode, 'size', required=True),
                        access=_readtxt(regnode, 'access', 'read-write'),
                        displayName=_readtxt(regnode, 'displayName',''),
                        description=_readtxt(regnode, 'description',''))


    @classmethod
    def parse_bitfield(cls, bfname, bfnode):
        evals = []
        for evname, evnode in bfnode.get('enumeratedValues', {}).iteritems():
            evals.append(cls.parse_enumerated_value(evname, evnode))

        mask = _readint(bfnode, 'mask', required=True)
        offset = utils.get_mask_offset(mask)
        width = int.bit_length(mask >> offset)

        return BitField(bfname,
                        # _readint(bfnode, 'offset', required=True),
                        # _readint(bfnode, 'width', required=True),
                        offset,
                        width,
                        evals,
                        access=_readtxt(bfnode, 'access', 'read-write'),
                        displayName=_readtxt(bfnode, 'displayName',''),
                        description=_readtxt(bfnode, 'description',''))

    @classmethod
    def parse_enumerated_value(cls, evname, evnode):
        return EnumeratedValue(evname,
                               _readint(evnode, 'value', required=True),
                               description=_readtxt(evnode, 'description',''))

    @classmethod
    def parse_device(cls, devname, devnode):
        pphs = []
        for pphname, pphnode in devnode.get('peripherals', {}).iteritems():
            pphs.append(cls.parse_peripheral(pphname, pphnode))

        args = (devname,
                pphs, 
                _readint(devnode, 'laneWidth', required=True), 
                _readint(devnode, 'busWidth', required=True))

        kwargs = dict(displayName=_readtxt(devnode, 'displayName', ''), 
                      description=_readtxt(devnode, 'description', ''), 
                      vendor=_readtxt(devnode, 'vendor', ''))

        # don't ask...
        if cls._supcls is None:
            return Device(*args, **kwargs)

        newdev = Device.__new__(cls._supcls, *args, **kwargs)
        Device.__init__(newdev, *args, **kwargs)
        return newdev

    @classmethod
    def parse_debug_access_port(cls, dapname, dapnode):
        ports = []
        for portname, portnode in dapnode.get('accessPorts', {}).iteritems():
            ports.append(cls.parse_access_port(portname, portnode))

        dp = dapnode['debugPort']
        ports.append(cls.parse_debug_port(dp.pop('mnemonic'), dp))

        args = (dapname,
                ports, 
                _readint(dapnode, 'laneWidth', required=True), 
                _readint(dapnode, 'busWidth', required=True))

        kwargs = dict(displayName=_readtxt(dapnode, 'displayName', ''), 
                      description=_readtxt(dapnode, 'description', ''))

        # don't ask...
        if cls._supcls is None:
            return DeviceBlock(*args, **kwargs)

        newdev = DeviceBlock.__new__(cls._supcls, *args, **kwargs)
        DeviceBlock.__init__(newdev, *args, **kwargs)
        return newdev

    @classmethod
    def parse_port(cls, portname, portnode):
        regs = []
        for regname, regnode in portnode.get('registers', {}).iteritems():
            regs.append(cls.parse_register(regname, regnode))

        return Port(portname,
                    regs, 
                    _readint(portnode, 'port', required=True), 
                    _readint(portnode, 'size', required=True), 
                    _readint(portnode, 'laneWidth', required=True), 
                    _readint(portnode, 'busWidth', required=True), 
                    displayName=_readtxt(portnode, 'displayName', ''), 
                    description=_readtxt(portnode, 'description', ''))
    @classmethod
    def parse_debug_port(cls, portname, portnode):
        regs = []
        for regname, regnode in portnode.get('registers', {}).iteritems():
            regs.append(cls.parse_register(regname, regnode))

        return DebugPort(portname,
                    regs, 
                    _readint(portnode, 'port', required=True), 
                    _readint(portnode, 'size', required=True), 
                    _readint(portnode, 'laneWidth', required=True), 
                    _readint(portnode, 'busWidth', required=True), 
                    displayName=_readtxt(portnode, 'displayName', ''), 
                    description=_readtxt(portnode, 'description', ''))

    @classmethod
    def parse_access_port(cls, portname, portnode):
        regs = []
        for regname, regnode in portnode.get('registers', {}).iteritems():
            regs.append(cls.parse_register(regname, regnode))

        return AccessPort(portname,
                    regs, 
                    _readint(portnode, 'port', required=True), 
                    _readint(portnode, 'size', required=True), 
                    _readint(portnode, 'laneWidth', required=True), 
                    _readint(portnode, 'busWidth', required=True), 
                    displayName=_readtxt(portnode, 'displayName', ''), 
                    description=_readtxt(portnode, 'description', ''))
