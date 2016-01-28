class Interface(object):

    def connect(self):
        return

    def disconnect(self):
        return

    def write(self, data, **kwargs):
        print "Interface <= 0x%x" % data

    def read(self, *args, **kwargs):
        return 0
