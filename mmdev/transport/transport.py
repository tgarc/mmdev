class Transport(object):
    class TransportError(Exception):
        pass

    class TransferError(Exception):
        pass

    def __init__(self, interface):
        self.interface = interface

    def sendPacket(self, *args, **kwargs):
        return

    def readPacket(self, *args, **kwargs):
        return -1

    def sendRequest(self, *args, **kwargs):
        return
