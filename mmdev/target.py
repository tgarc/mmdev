from mmdev import utils
from mmdev.components import Device
from mmdev.devicelink import DeviceLink


class Target(Device):
    """
    Models an SVD-like device that defines a single memory address space and its
    data bus.
    """
    def __new__(cls, link, descriptor, **kwparse):
        # This is a sneaky way for init'ing the deviceblock but it's much easier
        # to let from_devfile handle the parsing and initialization
        return utils.from_devfile(descriptor, supcls=cls, **kwparse)

    def __init__(self, link, descriptorfile, **kwparse):
        assert isinstance(link, DeviceLink)
        self.link = link

        for blk in self.walk():
            blk.root = self

    def connect(self):
        self.link.connect()

    def disconnect(self):
        self.link.disconnect()

    def reset(self):
        self.link.disconnect()
        self.link.connect()

    # defer to a DeviceLink to read/write memory
    def _write(self, address, value, accessSize=None):
        if accessSize is None:
            accessSize = self.busWidth
        self.link.memWrite(address, value, accessSize)
    write = _write
    
    def _read(self, address, accessSize=None):
        if accessSize is None:
            accessSize = self.busWidth
        return utils.HexValue(self.link.memRead(address, accessSize), accessSize)
    read = _read

    # def read(self, address, bitlen):
    #     data = []

    #     # First align the address
    #     modbits = address % self.laneWidth
    #     address -= modbits
    #     bitlen -= modbits
    #     xferlen = align*bool(modbits)
    #     data += self.link.memRead(address, xferlen)
    #     address += xferlen

    #     # Read the rest of the data in the largest aligned transfers possible
    #     xferwidth = self.busWidth
    #     while bitlen:
    #         xferlen = xferwidth * (bitlen // xferwidth)
    #         data += self.link.memRead(address, xferlen)
    #         bitlen -= xferlen
    #         address += xferlen
    #         xferwidth >>= 1

    #     return data

    # def write(self, address, data, bitlen):
    #     # First align the address
    #     modbits = address % self.laneWidth
    #     address -= modbits
    #     bitlen -= modbits
    #     xferlen = align*bool(modbits)
    #     self.link.memWrite(address, data.pop(), xferlen)
    #     address += xferlen

    #     # Read the rest of the data in the largest aligned transfers possible
    #     xferwidth = self.busWidth
    #     while bitlen:
    #         xferlen = xferwidth * (bitlen // xferwidth)
    #         self.link.memWrite(address, data.pop(), xferlen)
    #         bitlen -= xferlen
    #         address += xferlen
    #         xferwidth >>= 1

    #     return data
