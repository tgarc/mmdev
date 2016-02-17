class Transport(object):
    """
    Models the communication protocol that is used for sending and receiving
    data over a data link. Handles encapsulation of data, error checking, and
    automatic resending of data among other things.

    Parameters
    ----------
    datalink : mmdev.datalink.DataLink
        Specifies the underlying data link to use for sending data.
    """
    class TransportException(Exception):
        pass

    class InvalidResponse(TransportException):
        pass

    class NoACKResponse(TransportException):
        pass

    class FaultResponse(TransportException):
        pass

    class BusyResponse(TransportException):
        pass

    def __init__(self, datalink):
        self.datalink = datalink

    def connect(self):
        self.datalink.connect()

    def disconnect(self):
        self.datalink.disconnect()

    def sendPacket(self, *args, **kwargs):
        raise NotImplementedError

    def readPacket(self, *args, **kwargs):
        raise NotImplementedError

    def sendRequest(self, *args, **kwargs):
        raise NotImplementedError
