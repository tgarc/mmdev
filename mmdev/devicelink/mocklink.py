import logging
from mmdev.devicelink import DeviceLink
from mmdev.transport import MockTransport

logger = logging.getLogger(__name__)


class MockLink(DeviceLink):
    """
    A mock device link interface
    """
    def __init__(self, transport, descriptorfile, **kwparse):
        super(MockLink, self).__init__(transport, descriptorfile, **kwparse)
        self.values = {}

    def memWrite(self, addr, value, accessSize=32):
        self.values[addr] = value
        self.transport.sendPacket(addr, value)
        logger.debug(("{:#x} <= {:#%dx}" % (accessSize>>2)).format(addr, value))

    def memRead(self, addr, accessSize=32):
        value = self.values.get(addr, 0)
        self.transport.readPacket(addr)
        logger.debug(("{:#x} => {:#%dx}" % (accessSize>>2)).format(addr, value))
        return value

    def reset(self):
        self.values.clear()
