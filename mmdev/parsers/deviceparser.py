import json
import re


class ParseException(Exception):
    pass

class RequiredValueError(ParseException):
    pass

class DeviceParser(object):
    def __new__(cls, devfile, raiseErr=True, **kwargs):
        return cls.parse_device(devfile, raiseErr=raiseErr, **kwargs)

    @classmethod
    def parse_device(cls, devfile, **kwargs):
        raise NotImplementedError

    @classmethod
    def parse_peripheral(cls, pph_node):
        raise NotImplementedError

    @classmethod
    def parse_register(cls, reg_node):
        raise NotImplementedError

    @classmethod
    def parse_bitfield(cls, bit_node):
        raise NotImplementedError
