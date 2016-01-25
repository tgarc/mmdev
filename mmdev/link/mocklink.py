from link import Link
from mmdev.interface import Interface
from mmdev.transport import Transport

class MockLink(Link):
    """
    A mock I/O interface
    """
    def __init__(self, interface=None, transport=None, **kwargs):
        super(MockLink, self).__init__(Interface, Transport(Interface))
        self.values = {}

    def connect(self, frequency=1000000):
        self._interface.connect()

    def disconnect(self):
        self._interface.disconnect()

    def memWrite(self, addr, value, accessSize=32):
        self.values[addr] = value
        print "0x%08x <= 0x%08x" % (addr, value)

    def memRead(self, addr, accessSize=32):
        value = self.values.get(addr, 0)
        print "0x%08x => 0x%08x" % (addr, value)
        return value

    def reset(self):
        self.values.clear()
        return

    def write(self, value):
        print "Link <= 0x%x" % value

    def read(self):
        return 0
