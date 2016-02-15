class DeviceLinkException(Exception):
    pass


class DeviceLink(object):
    """
    Provides an interface through which user can send/receive data, as well as
    start, end, and otherwise manage sessions. This interface also takes care of
    fragmenting data into multiple packets as needed.

    Parameters
    ----------
    transport : mmdev.transport.Transport
        Specifies a transport protocol to use.
    """
    def __init__(self, transport):
        self.transport = transport

    def connect(self):
        """
        Establish a session with the target.
        """
        self.transport.connect()

    def disconnect(self):
        """
        Terminate session with the target.
        """
        self.transport.disconnect()

    def reset(self):
        self.disconnect()
        self.connect()

    def memWrite(self, address, data, size):
        """
        Write data bits to device memory. Accepts either a single int or a
        sequence of integer types.
        """
        return

    def memRead(self, address, size):
        """
        Read sequential bits data to device memory. Accepts either a single int or a
        sequence of integer types.
        """
        return 0
