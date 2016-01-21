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
