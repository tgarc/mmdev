from mmdev.datalink import MockDataLink
from mmdev.transport import Transport
import logging 

logger = logging.getLogger(__name__)


class MockTransport(Transport):

    def __init__(self, datalink=None):
        self.datalink = MockDataLink()

    def sendPacket(self, *args, **kwargs):
        logger.debug("Transport <= %s %s" % (args, kwargs))
        self.datalink.write(*args, **kwargs)

    def readPacket(self, *args, **kwargs):
        logger.debug("Transport => %s %s" % (args, kwargs))
        return self.datalink.read(*args, **kwargs)

    def sendRequest(self, *args, **kwargs):
        return 1
