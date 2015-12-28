class ParseException(Exception):
    pass

class DeviceParser(object):
    def __new__(cls, devfile):
        return cls.parse_device(devfile)

    @classmethod
    def parse_device(cls, devfile):
        raise NotImplemented

    @classmethod
    def parse_peripheral(cls, pph_node):
        return None

    @classmethod
    def parse_register(cls, reg_node):
        return None

    @classmethod
    def parse_bitfield(cls, bit_node):
        return None
