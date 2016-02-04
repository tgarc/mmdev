from devicelink import DeviceLink


class MockLink(DeviceLink):
    """
    A mock device link interface
    """
    def __init__(self):
        super(MockLink, self).__init__()
        self.values = {}

    def memWrite(self, addr, value, accessSize=32):
        self.values[addr] = value
        print "0x%08x <= 0x%08x" % (addr, value)

    def memRead(self, addr, accessSize=32):
        value = self.values.get(addr, 0)
        print "0x%08x => 0x%08x" % (addr, value)
        return value

    def reset(self):
        self.values.clear()
