class Link:
    """
    A mock I/O interface
    """
    def write(self, addr, value):
        print "0x%08x <= 0x%08x" % (addr, value)

    def read(self, addr):
        value = 0xdeadbeef
        print "0x%08x => 0x%08x" % (addr, value)
        return value
