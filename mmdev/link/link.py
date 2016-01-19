class Link(object):
    """
    An interface for a cortex-m DAP
    """
    def __init__(self, interface, transport):
        self.transport = transport
        self.interface = interface

    def connect(self):
        return

    def disconnect(self):
        return

    def reset(self):
        return

    def write(self, value):
        return

    def read(self):
        return -1

    def writeMem(self, addr, value, accessSize=32):
        return

    def readMem(self, addr, accessSize=32):
        return -1


class MockLink(Link):
    """
    A mock I/O interface
    """
    def __init__(self, **kwargs):
        self.value = 0

    def writeMem(self, addr, value, accessSize=32):
        self.value = value
        print "0x%08x <= 0x%08x" % (addr, value)

    def readMem(self, addr, accessSize=32):
        print "0x%08x => 0x%08x" % (addr, self.value)
        return self.value

    def reset(self):
        self.value = 0
        return

    def write(self, value):
        print "Link <= 0x%x" % self.value
        return

    def read(self):
        return self.value
