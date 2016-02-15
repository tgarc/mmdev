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
    def from_devfile(cls, devfile, raiseErr=True):
        cls._raiseErr = raiseErr

        with open(devfile) as fh:
            devfile = json.load(fh)

        for k, v in devfile.iteritems():
            cameltype = re.sub(r'(?!^)([A-Z][a-z0-9]+)', r'_\1', k).lower()

            try:
                parser = getattr(cls, 'parse_' + cameltype)
            except AttributeError:
                raise AttributeError("No '%s' parser found" % k)

            # don't support multiple nodes at the top level
            return parser(v.pop('mnemonic'), v)

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
