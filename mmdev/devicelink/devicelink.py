class DeviceLink(object):
    """
    Provides an interface through which user can send/receive data, as well as
    start, end, and otherwise manage sessions. This interface also takes care of
    fragmenting data into multiple packets as needed.

    """
    class DeviceLinkException(Exception):
        pass

    def __init__(self, *args, **kwargs):
        super(DeviceLink, self).__init__(self)
        self.transport = None

    def connect(self, transport=None):
        """
        Establish a session with the target.

        Parameters
        ----------
        transport : mmdev.transport.Transport
            Specifies a transport protocol to use.
        """
        try:
            assert transport is not None or getattr(self, 'transport', None) is not None
        except AssertionError:
            raise self.DeviceLinkException("No transport protocol has yet been specified.")

        if transport is not None:
            self.transport = transport
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
        raise NotImplementedError

    def memRead(self, address, size):
        """
        Read sequential bits data to device memory. Accepts either a single int or a
        sequence of integer types.
        """
        raise NotImplementedError
