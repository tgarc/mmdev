"""
pyconfig Device definition files are required to have three
dict-like objects:

BLK_MAP, REG_MAP
----------------
Maps a block/register mnemonic to its address for all hardware
blocks/registers on device

BIT_MAP
-------
Maps a bitfield mnemonic to a bitmask for all registers on device


These definition files also have some optional fields:

mnemonic
--------
Shorthand name for Device (e.g. armv7m). Defaults to definition file
name.

name
--------
Full name of Device. Defaults to "Device".

BLK_NAME, REG_NAME, BIT_NAME
------------------
Maps a block/register/bitfield mnemonic to its full name (e.g., ITM :
Instrumentation Trace Macrocell).

BLK_DESCR, REG_DESCR, BIT_DESCR
-------------------------------
Maps a block/register/bitfield mnemonic to a description.
"""
from deviceparser import DeviceParser


class pycfgDevice(DeviceParser):
    @classmethod
    def parse_device(cls, devfile):
        if isinstance(devfile, basestring):
            try:
                devfile = __import__('mmdev.'+devfile, fromlist=[''])
            except ImportError:
                import imp, os
                devfile = imp.load_source(os.path.basename(devfile), devfile)

        name = getattr(devfile, 'name', 'Device')
        mnem = getattr(devfile, 'mnemonic', devfile.__name__)
        descr = getattr(devfile, 'descr', '')
        width = getattr(devfile, 'width', 32)
        vendor = getattr(devfile, 'vendor', '')        

        dev = Device(mnem, fullname=name, descr=descr, width=width, vendor=vendor)

        for blkname, blkaddr in devfile.BLK_MAP.iteritems():
            cls.parse_peripheral(dev, blkname, blkaddr, devfile)

        return dev

    @classmethod
    def parse_peripheral(cls, blkname, blkaddr, devfile):
        pph = cls._create_peripheral(blkname, blkaddr,
                                     fullname=devfile.BLK_NAME.get(blkname,'Peripheral'),
                                     descr=devfile.BLK_DESCR.get(blkname,''))

        for regname, regaddr in devfile.REG_MAP.get(blkname,{}).iteritems():
            pph.parse_register(regname, regaddr, devfile)

        return pph

    @classmethod
    def parse_register(cls, regname, regaddr, devfile):
        reg = cls._create_register(regname, regaddr,
                                   fullname=devfile.REG_NAME.get(regname,'Register'),
                                   descr=devfile.REG_DESCR.get(regname,''))
        for bitname, bitmask in devfile.BIT_MAP.get(regname,{}).iteritems():
            reg.parse_bitfield(bitname, bitmask, devfile)
        return reg

    @classmethod
    def parse_bitfield(cls, bitname, bitmask, devfile):
        return cls._create_bitfield(bitname, bitmask,
                                     fullname=devfile.BIT_NAME.get(bitname,'BitField'),
                                     descr=devfile.BIT_DESCR.get(regname,{}).get(bitname,''))
