import logging
logger = logging.getLogger(__name__)


class MockDataLink(object):
    """
    Provides an interface to the physical link over which a host communicates to
    a target debug port. This is most commonly used as an interface to a USB
    driver.
    """
    def connect(self):
        return

    def disconnect(self):
        return

    def write(self, data, **kwargs):
        logger.debug("DataLink <= %s %s" % (data, kwargs))

    def read(self, *args, **kwargs):
        logger.debug("DataLink => 0")
        return 0
