class ParseException(Exception):
    pass

class RequiredValueError(ParseException):
    pass

class DeviceParser(object):
    def __new__(cls, devfile, raiseErr=True):
        return cls.parse_device(devfile, raiseErr=raiseErr)

    @classmethod
    def parse_device(cls, devfile, **kwargs):
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
