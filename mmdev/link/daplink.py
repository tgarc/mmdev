from mmdev import blocks
import mmdev.device as devblks
from mmdev.transport import Transport
from mmdev.interface import Interface
import mmdev.utils as utils
import logging
from operator import attrgetter
import time

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


class DPRegister(devblks.Register):
    def _read(self):
        return self.root.read(self.parent._port, self._address)

    def _write(self, value):
        return self.root.write(self.parent._port, self._address, value)

class APRegister(devblks.Register):
    _attrs = devblks.Register._attrs + ['bank']

    def __new__(cls, mnemonic, width, address, bank, subblocks, resetMask=0, resetValue=None,
                fullname=None, descr='-', kwattrs={}):
        return super(APRegister, cls).__new__(cls, mnemonic, width, address, subblocks,
                                              fullname=fullname, descr=descr, kwattrs=kwattrs)

    def __init__(self, mnemonic, width, address, bank, subblocks, resetMask=0, resetValue=None,
                fullname=None, descr='-', kwattrs={}):
        super(APRegister, self).__init__(mnemonic, width, address, subblocks, 
                                         fullname=fullname, descr=descr, kwattrs=kwattrs)
        self._bank = bank

    def _read(self):
        return self.root.read(self.parent._port, self._address, bank=self._bank)

    def _write(self, value):
        return self.root.write(self.parent._port, self._address, value, bank=self._bank)


class MemoryAccessPort(blocks.Block):
    _port = 1

    CSW = APRegister('CSW', 32, 0x00, 0, 
                     [devblks.BitField('PROT', 7, 24, fullname='Bus Access Protection Control', descr="This field enables the debugger to specify protection flags for a debug access."),
                      devblks.BitField('ADDRINC', 2, 4, fullname='Address Increment', descr="""\
Address auto-increment and packing mode. This field controls whether the access
address increments automatically on read and write data accesses through the
Data Read/Write Register."""),
                      devblks.BitField('SIZE', 3, 0, descr="Byte size of the access to perform")], 
                      fullname='Control Status Word',
                      descr="""The CSW holds control and status information for the MEM-AP.""")

    DRW = APRegister('DRW', 32, 0x00, 0, [], 
                      fullname='Data Read/Write',
                      descr="""\
The DRW is used for memory accesses: 
1) Writing to the DRW initiates a write to the address specified by the TAR.  
2) Reading from the DRW initiates a read from the address specified by the
TAR. When the read access completes, the value is returned from the DRW.""")

    TAR = APRegister('TAR', 32, 0x04, 0, [], 
                      fullname='Transfer Address Register',
                      descr="""\
The TAR holds the address for the next access to the memory system, or set
of debug resources, connected to the MEM-AP. The MEM-AP can be configured so
that the TAR is incremented automatically after each memory access. Reading or
writing to the TAR does not cause a memory access.""")

    IDR = APRegister('IDR', 32, 0xFC, 0x0F, [], 
                     fullname='Identification Register',
                     descr="""\
The Identification Register identifies the Access Port. It is a read-only
register, implemented in the last word of the AP register space, at offset 0xFC.
An IDR of zero indicates that no AP is present.""")

    def __new__(cls):
        return super(MemoryAccessPort, cls).__new__(cls, 'MEMAP', [cls.CSW, cls.TAR, cls.DRW, cls.IDR], fullname='Access Port', bind=False)

    def __init__(self):
        super(MemoryAccessPort, self).__init__('MEMAP', [MemoryAccessPort.CSW,
                                                          MemoryAccessPort.TAR,
                                                          MemoryAccessPort.DRW,
                                                          MemoryAccessPort.IDR],
                                               fullname='Memory Access Port',
                                               bind=False, descr="""\
A MEM-AP provides a DAP with access to a memory subsystem. Another way of
describing the operation of a MEM-AP is that:

1) A debug component implements a memory-mapped abstraction of a set of resources.
2) The MEM-AP provides AP access to those resources.

However, an access to a MEM-AP might only access a register within the MEM-AP,
                                               without generating a memory access.""", allow_formatting=False)


class DebugPort(blocks.Block):
    _port = 0

    WCR = DPRegister('WCR', 32, 0x04, [], 
                      fullname='Wire Control Register',
                      descr="""\
The Wire Control Register is always present on any SW-DP implementation. Its
purpose is to select the operating mode of the physical serial port connection
to the SW-DP. On a SW-DP, the WCR is a read/write register at address 0x4 on
read and write operations when the CTRLSEL bit in the Select Register is set to
1.""")

    RDBUFF = DPRegister('RDBUFF', 32, 0x0C, [], 
                         fullname='Read Buffer',
                         descr="""\
On a SW-DP, performing a read of the Read Buffer captures data from the AP,
presented as the result of a previous read, without initiating a new AP
transaction. This means that reading the Read Buffer returns the result of the
last AP read access, without generating a new AP access. After you have read
the Read Buffer, its contents are no longer valid. The result of a second read
of the Read Buffer is UNPREDICTABLE.""")

    IDCODE = DPRegister('IDCODE', 32, 0x00, [], 
                         fullname='Identification Code',
                         descr="""\
The Identification Code Register is always present on all DP implementations. It
provides identification information about the ARM Debug Interface.""")

    ABORT = DPRegister('ABORT', 32, 0x00, 
                        [devblks.BitField('ORUNERRCLR', 1, 4, fullname='Overrun Error Clear', descr="Write 1 to this bit to clear the STICKYORUN overrun error flag to 0."),
                         devblks.BitField('WDERRCLR', 1, 3, fullname='Write Data Error Clear', descr="Write 1 to this bit to clear the WDATAERR write data error flag to 0"),
                         devblks.BitField('STKERRCLR', 1, 2, fullname='Sticky Error Clear', descr="""\
Write 1 to this bit to clear the STICKYERR sticky error flag to 0."""),
                         devblks.BitField('STKCMPCLRa', 1, 1, fullname='Sticky Compare Error Clear', descr="Write 1 to this bit to clear the STICKYCMP sticky compare flag to 0."),
                         devblks.BitField('DAPABORT', 1, 0, fullname='DAP Abort', descr="""\
Write 1 to this bit to generate a DAP abort. This aborts the current AP
transaction. Do this only if the debugger has received WAIT responses over an
extended period.""")],
                        fullname='AP Abort',
                        descr='The AP Abort Register')

    CTRLSTAT = DPRegister('CTRLSTAT', 32, 0x04,
                           [devblks.BitField('CSYSPWRUPACK', 1, 31, fullname='System Power Up Acknowledge'),
                            devblks.BitField('CSYSPWRUPREQ', 1, 30, fullname='System Power Up Request'),
                            devblks.BitField('CDBGPWRUPACK', 1, 29, fullname='Debug Power Up Acknowledge'),
                            devblks.BitField('CDBGPWRUPREQ', 1, 28, fullname='Debug Power Up Request'),
                            devblks.BitField('CDBGRSTACK', 1, 27, fullname='Debug Reset Acknowledge'),
                            devblks.BitField('CDBGRSTREQ', 1, 26, fullname='Debug Reset Request'),
                            devblks.BitField('TRNCNT', 12, 12, fullname='Transaction Counter'),
                            devblks.BitField('MASKLANE', 4, 8, descr="""\
Indicates the bytes to be masked in pushed compare and pushed verify
operations."""), 
                            devblks.BitField('WDATAERR', 1, 7, fullname='Write Data Error', 
                                             descr="""\
This bit is set to 1 if a Write Data Error occurs. This happens if:

1) There is a a parity or framing error on the data phase of a write.
2) A write that has been accepted by the DP is then discarded without being
submitted to the AP.

This bit can only be cleared to 0 by writing 1 to the WDERRCLR field of the AP
Abort Register, see The AP Abort Register, ABORT on page 6-6.  After a power-on
reset this bit is 0."""),
                            devblks.BitField('READOK', 1, 6, descr="""\
This bit is set to 1 if the response to the previous AP or RDBUFF read was
OK. It is cleared to 0 if the response was not OK."""),
                            devblks.BitField('STICKYERR', 1, 5, descr="This bit is set to 1 if an error is returned by an AP transaction."),
devblks.BitField('STICKYCMP', 1, 4, descr="""This bit is set to 1 when a match occurs on a pushed compare or a pushed verify operation."""),
                            devblks.BitField('TRNMODE', 2, 2, fullname='Transfer Mode', descr="""This field sets the transfer mode for AP operations."""),
                            devblks.BitField('STICKYORUN', 1, 1, descr="""If overrun detection is enabled, this bit is set to 1 when an overrun occurs."""),
                            devblks.BitField('ORUNDETECT', 1, 0, fullname='Overrun Detect', descr="""This bit is set to 1 to enable overrun detection.""")],
                            fullname='DP Control/Status',
                            descr="""\
The Control/Status Register is always present on all DP
implementations. Its provides control of the DP, and status information about
the DP.""")

    SELECT = DPRegister('SELECT', 32, 0x08,
                         [devblks.BitField('APSEL', 8, 24, fullname='AP Select', descr="Selects the current AP."),
                          devblks.BitField('APBANKSEL', 4, 4, fullname='AP Bank Select', descr="Selects the active four-word register bank on the current AP")], 
                         fullname='Select',
                         descr="""\
The AP Select Register is always present on all DP implementations. Its
main purpose is to select the current Access Port (AP) and the active four-word
register bank within that AP.""")

    RESEND = DPRegister('RESEND', 32, 0x08,
                        [devblks.BitField('RESEND', 32, 0, descr="The value that was returned by the last AP read or DP RDBUFF read.")],
                        fullname='Read Resend',
                        descr="""\
The Read Resend Register is always present on any SW-DP implementation. Its
purpose is to enable the read data to be recovered from a corrupted debugger
transfer, without repeating the original AP transfer.""")

    def __new__(cls):
        return super(DebugPort, cls).__new__(cls, 'DP', [cls.IDCODE, cls.ABORT,
                                                         cls.CTRLSTAT,
                                                         cls.SELECT],
                                             fullname='Debug Port',
                                             bind=False)

    def __init__(self):
        super(DebugPort, self).__init__('DP', [DebugPort.IDCODE,
                                               DebugPort.ABORT,
                                               DebugPort.CTRLSTAT,
                                               DebugPort.SELECT], 
                                        fullname='Debug Port', bind=False,
                                        descr="""\
An ARM Debug Interface implementation includes a single Debug Port (DP), that provides the external
physical connection to the interface. The ARM Debug Interface v5 specification supports two DP
implementations:

1) The JTAG Debug Port (JTAG-DP).
2) The Serial Wire Debug Port (SW-DP).

These alternative DP implementations provide different mechanisms for making
Access Port and Debug Port accesses. However, they have a number of common
features. In particular, each implementation provides:

1) A means of identifying the DAP, using an identification code scheme.
2) A means of making DP and AP accesses.
3) A means of aborting a register access that appears to have faulted.""")


class DAPLink(blocks.RootBlock):
    MEMAP = MemoryAccessPort()
    DP = DebugPort()

    def __new__(cls, *args, **kwargs):
        dap = super(DAPLink, cls).__new__(cls, 'DAP', 32, 32, [cls.MEMAP, cls.DP], fullname='Debug Access Port', bind=False)
        return dap

    def __init__(self, transport=Transport, interface=None):
        super(DAPLink, self).__init__('DAP', 32, 32, [DAPLink.MEMAP, DAPLink.DP], fullname='Debug Access Port', bind=False)
        if interface is None:
            interface = Interface()
        self._interface = interface
        self._transport = transport(interface)

    def connect(self, frequency=1000000):
        self._interface.connect()

        # set clock frequency
        # self.setSWJClock(frequency)

        # configure transfer
        # self.transferConfigure()

        # configure swd protocol
        # self.swdConfigure()

        self.reset()
        self.init()

    def init(self):
        self.DP.SELECT.APBANKSEL = 0
        self.DP.CTRLSTAT.CSYSPWRUPREQ = 1 
        self.DP.CTRLSTAT.CDBGPWRUPREQ = 1
        
        mask = self.DP.CTRLSTAT.CSYSPWRUPACK._mask | self.DP.CTRLSTAT.CDBGPWRUPACK._mask
        while self.DP.CTRLSTAT&mask != mask: None

    def _sort(self, key=attrgetter('_port'), reverse=False):
        self._nodes.sort(key=key, reverse=reverse)
    
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

    def read(self, port, address, bank=None):
        if bank is not None:
            self.DP.SELECT.APBANKSEL = bank
        if self._transport.sendRequest(port, 1, address) == 2: 
            time.sleep(0.1)
        return self._transport.readPacket()

    def write(self, port, address, data, bank=None):
        if bank is not None:
            self.DP.SELECT.APBANKSEL = bank
        if self._transport.sendRequest(port, 0, address) == 2: 
            time.sleep(0.1)
        self._transport.sendPacket(data)

    def writeMem(self, addr, data, accessSize=32):
        self.DP.SELECT.APBANKSEL = 0
        self.MEMAP.CSW = CSW_VALUE | accessSize >> 4

        if accessSize == 8:
            data = data << ((addr & 0x03) << 3)
        elif accessSize == 16:
            data = data << ((addr & 0x02) << 3)

        self.MEMAP.TAR = addr
        self.MEMAP.DRW = data

    def readMem(self, addr, accessSize=32):
        self.DP.SELECT.APBANKSEL = 0
        self.MEMAP.CSW = CSW_VALUE | accessSize >> 4
        self.MEMAP.TAR = addr
        resp = self.MEMAP.DRW.value

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
