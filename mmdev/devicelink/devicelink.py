from mmdev import utils
from mmdev.transport import Transport
from mmdev.components import Device


class DeviceLink(Device):
    """
    Provides an interface through which user can send/receive data, as well as
    start, end, and otherwise manage sessions. This interface also takes care of
    fragmenting data into multiple packets as needed.

    """
    class DeviceLinkException(Exception):
        pass

    def __new__(cls, transport, descriptorfile, **kwparse):
        # This is a sneaky way for init'ing the deviceblock but it's much easier
        # to let from_devfile handle the parsing and initialization
        return utils.from_devfile(descriptorfile, supcls=cls, **kwparse)

    def __init__(self, transport, descriptorfile, **kwparse):
        assert isinstance(transport, Transport)
        self.transport = transport

    def connect(self):
        """
        Establish a session with the target.

        Parameters
        ----------
        transport : mmdev.transport.Transport
            Specifies a transport protocol to use.
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
        raise NotImplementedError

    def memRead(self, address, size):
        """
        Read sequential bits data to device memory. Accepts either a single int or a
        sequence of integer types.
        """
        raise NotImplementedError
