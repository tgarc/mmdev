import logging 

logger = logging.getLogger(__name__)


class MockTransport(object):
    def sendPacket(self, *args, **kwargs):
        logger.debug("Transport <= %s %s" % (args, kwargs))
        self.datalink.write(*args, **kwargs)

    def readPacket(self, *args, **kwargs):
        logger.debug("Transport => %s %s" % (args, kwargs))
        return self.datalink.read(*args, **kwargs)

    def sendRequest(self, *args, **kwargs):
        return 1
