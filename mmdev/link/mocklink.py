from link import Link

class MockLink(Link):
    """
    A mock I/O interface
    """
    def __init__(self, **kwargs):
        self.value = 0

    def memWrite(self, addr, value, accessSize=32):
        self.value = value
        print "0x%08x <= 0x%08x" % (addr, value)

    def memRead(self, addr, accessSize=32):
        value = self.value
        print "0x%08x => 0x%08x" % (addr, value)
        return value

    def reset(self):
        self.value = 0
        return

    def write(self, value):
        print "Link <= 0x%x" % self.value

    def read(self):
        return self.value
