class Link:
    """
    A mock I/O interface
    """
    def __init__(self):
        self.value = 0

    def write(self, addr, value):
        self.value = value
        print "0x%08x <= 0x%08x" % (addr, value)

    def read(self, addr):
        print "0x%08x => 0x%08x" % (addr, self.value)
        return self.value
