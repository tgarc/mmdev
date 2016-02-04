class DataLink(object):
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
        print "DataLink <= %s %s" % (data, kwargs)

    def read(self, *args, **kwargs):
        print "DataLink => 0"
        return 0
