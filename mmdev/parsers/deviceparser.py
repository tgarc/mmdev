from mmdev.blocks import BlockNode, Peripheral, Register, BitField
from mmdev.device import Device

class DeviceParser(Device):
    @classmethod
    def parse_device(cls, devfile):
        raise NotImplemented

    @classmethod
    def parse_peripheral(cls, devfile):
        raise NotImplemented

    @classmethod
    def parse_register(cls, devfile):
        raise NotImplemented

    @classmethod
    def parse_bitfield(cls, devfile):
        raise NotImplemented


class BlockNodeBuilder(BlockNode):
    @classmethod
    def attach_subblock(cls, subblock):
        """
        Attach a sub-block to this parent block
        """
        setattr(cls, subblock.mnemonic.lower(), subblock)
        cls._nodes.append(subblock)

        subblock.parent = cls
        p = cls
        while p.parent is not None: p = p.parent
        subblock.root = p

        # Ugly hack so root can find all nodes
        if isinstance(cls.root, RootBlockNode):
            cls.root._map[subblock.mnemonic.lower()] = subblock

    @classmethod
    def create_subblock(cls, mnemonic, fullname='', descr=''):
        """
        Create and attach a (non-addressable) sub-block to this parent block
        """
        subblock = BlockNode(mnemonic, fullname=fullname, descr=descr)
        cls._attach_subblock(subblock)
        return subblock


class PeripheralBuilder(BlockNodeBuilder):
    @classmethod
    def create_peripheral(cls, mnemonic, addr, fullname='', descr=''):
        """
        Create and attach a peripheral to this parent block
        """
        pph = Peripheral(mnemonic, addr, fullname=fullname, descr=descr)
        cls._attach_subblock(pph)
        return pph

    @classmethod
    def parse_peripheral(cls, pph):
        raise NotImplemented


class RegisterBuilder(BlockNodeBuilder):
    @classmethod
    def create_register(cls, mnemonic, addr, fullname='', descr='', fmt=None):
        """
        Create and attach a register to this peripheral
        """
        reg = Register(mnemonic, addr, fullname=fullname, descr=descr)
        cls.attach_subblock(reg)
        return reg

    @classmethod
    def parse_register(cls, reg):
        raise NotImplemented


class BitFieldBuilder(BitField):
    @classmethod
    def create_bitfield(cls, mnemonic, mask, fullname='', descr=''):
        """
        Create and attach a bitfield to this register
        """
        bits = BitField(mnemonic, mask, fullname=fullname, descr=descr)
        cls.attach_subblock(bits)
        return bits

    @classmethod
    def parse_bitfield(cls, bits):
        raise NotImplemented

