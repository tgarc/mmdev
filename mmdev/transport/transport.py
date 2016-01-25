class Transport(object):
    class TransportError(Exception):
        pass

    class TransferError(Exception):
        pass

    def __init__(self, interface):
        self.interface = interface

    def sendPacket(self, *args, **kwargs):
        self.interface.write(*args, **kwargs)

    def readPacket(self, *args, **kwargs):
        return self.interface.read(*args, **kwargs)

    def sendRequest(self, *args, **kwargs):
        return 1
