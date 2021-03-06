import logging
logger = logging.getLogger(__name__)


class DataLink(object):
    """
    Provides an interface to the physical link over which a host communicates to
    a target debug port. This is most commonly used as an interface to a USB
    driver.
    """
    class DeviceLinkException(Exception):
        pass

    def connect(self):
        raise NotImplementedError

    def disconnect(self):
        raise NotImplementedError

    def write(self, data, **kwargs):
        raise NotImplementedError

    def read(self, *args, **kwargs):
        raise NotImplementedError
