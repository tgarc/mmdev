class Transport(object):
    class TransportException(Exception):
        pass

    class TransferInvalid(TransportException):
        pass

    class TransferNoACK(TransportException):
        pass

    class TransferFault(TransportException):
        pass

    class TransferBusy(TransportException):
        pass

    def __init__(self, interface):
        self.interface = interface

    def sendPacket(self, *args, **kwargs):
        self.interface.write(*args, **kwargs)

    def readPacket(self, *args, **kwargs):
        return self.interface.read(*args, **kwargs)

    def sendRequest(self, *args, **kwargs):
        return 1
