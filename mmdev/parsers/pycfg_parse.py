from deviceparser import *


class PYCFGParser(DeviceParser):
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

    @classmethod
    def parse_peripheral(cls, pphname, pphaddr, devfile):
        pph = Peripheral(pphname, pphaddr,
                         fullname=devfile.BLK_NAME.get(pphname,'Peripheral'),
                         descr=devfile.BLK_DESCR.get(pphname,''))

        for regname, regaddr in devfile.REG_MAP.get(pphname,{}).iteritems():
            reg = cls.parse_register(regname, regaddr, devfile)
            pph._attach_subblock(reg)

        return pph

    @classmethod
    def parse_register(cls, regname, regaddr, devfile):
        reg = Register(regname, regaddr,
                       fullname=devfile.REG_NAME.get(regname,'Register'),
                       descr=devfile.REG_DESCR.get(regname,''))

        for bitname, bitmask in devfile.BIT_MAP.get(regname,{}).iteritems():
            bits = cls.parse_bitfield(bitname, bitmask, devfile)
            reg._attach_subblock(bits)

        return reg

    @classmethod
    def parse_bitfield(cls, bitname, bitmask, devfile):
        return BitField(bitname, bitmask,
                        fullname=devfile.BIT_NAME.get(bitname,'BitField'),
                        descr=devfile.BIT_DESCR.get(bitname,''))

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

        for pphname, pphaddr in devfile.BLK_MAP.iteritems():
            pph = cls.parse_peripheral(pphname, pphaddr, devfile)
            dev._attach_subblock(pph)

        return dev

