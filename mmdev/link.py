class Link:
    """
    A mock I/O interface
    """
    def __init__(self):
        self.value = 0

    def write(self, addr, value, transfer_size):
        self.value = value
        print "0x%08x <= 0x%08x (%d)" % (addr, value, transfer_size)

    def read(self, addr, transfer_size):
        print "0x%08x => 0x%08x" % (addr, self.value, transfer_size)
        return self.value
