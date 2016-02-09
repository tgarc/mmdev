class DumpException(Exception):
    pass

class RequiredValueError(DumpException):
    pass

class DeviceDumper(object):
    def __new__(cls, deviceblock):
        return cls.dump_device(deviceblock)

    @classmethod
    def dump_device(cls, deviceblock, **kwargs):
        raise NotImplemented

    @classmethod
    def dump_peripheral(cls, pph_node):
        return None

    @classmethod
    def dump_register(cls, reg_node):
        return None

    @classmethod
    def dump_bitfield(cls, bit_node):
        return None
