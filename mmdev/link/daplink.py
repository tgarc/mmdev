from mmdev import blocks
import mmdev.device as devblks
from mmdev.transport import Transport
from mmdev.interface import Interface
import mmdev.utils as utils
import logging


reverse_bits = lambda b,w: ("{0:0%db}" % w).format(b)[::-1]

IDCODE = 0 << 2
DP_ACC = 0 << 0
READ = 1 << 1
WRITE = 0 << 1
VALUE_MATCH = 1 << 4
MATCH_MASK = 1 << 5

ORUNERRCLR = 0b100
WDERRCLR   = 0b011
STKERRCLR  = 0b010
STKCMPCLRa = 0b001
DAPABORT   = 0b000

APBANKSEL = 0x000000f0

# AP Control and Status Word definitions
CSW_SIZE     =  0x00000007
CSW_SIZE8    =  0x00000000
CSW_SIZE16   =  0x00000001
CSW_SIZE32   =  0x00000002
CSW_ADDRINC  =  0x00000030
CSW_NADDRINC =  0x00000000
CSW_SADDRINC =  0x00000010
CSW_PADDRINC =  0x00000020
CSW_DBGSTAT  =  0x00000040
CSW_TINPROG  =  0x00000080
CSW_HPROT    =  0x02000000
CSW_MSTRTYPE =  0x20000000
CSW_MSTRCORE =  0x00000000
CSW_MSTRDBG  =  0x20000000
CSW_RESERVED =  0x01000000

CSW_VALUE = (CSW_RESERVED | CSW_MSTRDBG | CSW_HPROT | CSW_DBGSTAT | CSW_SADDRINC)


class DAPRegister(devblks.Register):
    _dynamicBinding = False

    def _read(self):
        return self.root.read(self.parent._port, self._address)

    def _write(self, value):
        return self.root.write(self.parent._port, self._address, value)


class AccessPort(blocks.Block):
    _port = 1

    CSW = DAPRegister('CSW', 32, 0x00, [], 
                      fullname='Control Status Word',
                      descr="""The CSW holds control and status information for
                      the MEM-AP.""")

    DRW = DAPRegister('DRW', 32, 0x00, [], 
                      fullname='Data Read/Write',
                      descr="""The DRW is used for memory accesses:
                      + Writing to the DRW initiates a write to the address
                      specified by the TAR.
                      + Reading from the DRW initiates a read from the address
                      specified by the TAR. When the read access completes, the
                      value is returned from the DRW.""")

    TAR = DAPRegister('TAR', 32, 0x04, [], 
                      fullname='Transfer Address Register',
                      descr="""The TAR holds the address for the next access to
                      the memory system, or set of debug resources,
                      connected to the MEM-AP. The MEM-AP can be configured
                      so that the TAR is incremented automatically after
                      each memory access. Reading or writing to the TAR does
                      not cause a memory access.""")

    IDR = DAPRegister('IDR', 32, 0xFC, [], 
                      fullname='Identification Register',
                      descr="""The Identification Register identifies the Access
                      Port. It is a read-only register, implemented in the last
                      word of the AP register space, at offset 0xFC.  An IDR of
                      zero indicates that no AP is present.""")

    def __new__(cls):
        return super(AccessPort, cls).__new__(cls, 'AP', [cls.CSW, cls.TAR, cls.DRW, cls.IDR], fullname='Access Port', bind=False)

    def __init__(self):
        super(AccessPort, self).__init__('AP', [AccessPort.CSW, AccessPort.TAR, AccessPort.DRW, AccessPort.IDR], fullname='Access Port', bind=False)


class DebugPort(blocks.Block):
    _port = 0

    IDCODE = DAPRegister('IDCODE', 32, 0x00, [], 
                         fullname='Identification Code',
                         descr="""The Identification Code Register is always
                         present on all DP implementations. It provides
                         identification information about the ARM Debug
                         Interface.""")

    ABORT = DAPRegister('ABORT', 32, 0x00, 
                        [devblks.BitField('ORUNERRCLR', 1, 4, fullname='Overrun Error Clear', descr="Write 1 to this bit to clear the STICKYORUN overrun error flag to 0."),
                         devblks.BitField('WDERRCLR', 1, 3, fullname='Write Data Error Clear', descr="Write 1 to this bit to clear the WDATAERR write data error flag to 0"),
                         devblks.BitField('STKERRCLR', 1, 2, fullname='Sticky Error Clear', descr="Write 1 to this bit to clear the STICKYERR sticky error flag to 0."),
                         devblks.BitField('STKCMPCLRa', 1, 1, fullname='Sticky Compare Error Clear', descr="Write 1 to this bit to clear the STICKYCMP sticky compare flag to 0."),
                         devblks.BitField('DAPABORT', 1, 0, fullname='DAP Abort', descr="Write 1 to this bit to generate a DAP abort. This aborts the current AP transaction. Do this only if the debugger has received WAIT responses over an extended period.")],
                        fullname='AP Abort',
                        descr='The AP Abort Register')

    CTRL_STAT = DAPRegister('CTRL_STAT', 32, 0x04, [], 
                            fullname='DP Control/Status',
                            descr="""The Control/Status Register is always present
                            on all DP implementations. Its provides control of the
                            DP, and status information about the DP.""")

    SELECT = DAPRegister('SELECT', 32, 0x08, [], 
                         fullname='Select',
                         descr="""The AP Select Register is always present on
                         all DP implementations. Its main purpose is to select
                         the current Access Port (AP) and the active four-word
                         register bank within that AP.""")


    def __new__(cls):
        return super(DebugPort, cls).__new__(cls, 'DP', [cls.IDCODE, cls.ABORT, cls.CTRL_STAT, cls.SELECT], fullname='Debug Port', bind=False)

    def __init__(self):
        super(DebugPort, self).__init__('DP', [DebugPort.IDCODE, DebugPort.ABORT, DebugPort.CTRL_STAT, DebugPort.SELECT], fullname='Debug Port', bind=False)


class DAPLink(blocks.Block):
    AP = AccessPort()
    DP = DebugPort()

    def __new__(cls, *args, **kwargs):
        dap = super(DAPLink, cls).__new__(cls, 'DAP', [cls.AP, cls.DP], fullname='Debug Access Port', bind=False)
        return dap

    def __init__(self, transport=Transport, interface=None):
        super(DAPLink, self).__init__('DAP', [DAPLink.AP, DAPLink.DP], fullname='Debug Access Port', bind=False)
        if interface is None:
            interface = Interface()
        self._interface = interface
        self._transport = transport(interface)

        for blk in self.walk(d=3):
            blk._sort(key=lambda blk: blk._address)

    def connect(self, frequency=1000000):
        self._interface.connect()

        # set clock frequency
        # self.setSWJClock(frequency)

        # configure transfer
        # self.transferConfigure()

        # configure swd protocol
        # self.swdConfigure()

        self.reset()

    def _line_reset(self):
        self._interface.write('1'*56)

    def reset(self):
        self._line_reset()
        # switch from jtag to swd
        self._JTAG2SWD()
        # clear errors
        self.DP.ABORT = 0x1F

    def _JTAG2SWD(self):
        # send the 16bit JTAG-to-SWD sequence
        self._interface.write(reverse_bits(0x9EE7,w=16))

        self._line_reset()

        self._interface.write('0'*8)

        # read ID code to confirm synchronization
        logging.info('IDCODE: 0x%X', self.DP.IDCODE.value)

    def read(self, port, address):
        self._transport.sendRequest(port, 1, address)
        return self._transport.readPacket()

    def write(self, port, address, data):
        self._transport.sendRequest(port, 0, address)
        self._transport.sendPacket(data)

    def writeMem(self, addr, data, accessSize=32):
        self.AP.CSW = CSW_VALUE | accessSize >> 4

        if accessSize == 8:
            data = data << ((addr & 0x03) << 3)
        elif accessSize == 16:
            data = data << ((addr & 0x02) << 3)

        self.AP.TAR = addr
        self.AP.DRW = data

    def readMem(self, addr, accessSize=32):
        self.AP.CSW = CSW_VALUE | accessSize >> 4
        self.AP.TAR = addr
        resp = self.AP.DRW.value

        if accessSize == 8:
            resp = (resp >> ((addr & 0x03) << 3) & 0xff)
        elif accessSize == 16:
            resp = (resp >> ((addr & 0x02) << 3) & 0xffff)

        return resp

    def disconnect(self):
        try:
            self._line_reset()
        finally:
            self._interface.disconnect()
