from mmdev import blocks, components
from mmdev.transport import Transport
import devicelink
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


CSW = components.Register('CSW', 
                 [components.BitField('PROT', 24, 7, fullname='Bus Access Protection Control', 
                                      descr="""\
This field enables the debugger to specify protection flags for a debug
access."""),
                  components.BitField('ADDRINC', 4, 2, 
                                      [components.EnumeratedValue('ADDRINC', 0, descr="Auto-increment off Always."),
                                       components.EnumeratedValue('ADDRINC', 1, descr="Increment single Always."),
                                       components.EnumeratedValue('ADDRINC', 2, descr="""\
Increment packed If Packed transfers are supported. When Packed transfers are
not supported, value b10 is Reserved.""")],
                                      fullname='Address Increment', 
                                      descr="""\
Address auto-increment and packing mode. This field controls whether the access
address increments automatically on read and write data accesses through the
Data Read/Write components.Register."""),
                  components.BitField('SIZE', 0, 3, 
                                      descr="Byte size of the access to perform")], 
                 0x00, 32,
                 access='read-write',
                 fullname='Control Status Word',
                 descr="The CSW holds control and status information for the MEM-AP.")

DRW = components.Register('DRW', [], 0x0C, 32,
                 access='read-write',
                 fullname='Data Read/Write',
                 descr="""\
The DRW is used for memory accesses: 
1) Writing to the DRW initiates a write to the address specified by the TAR.  
2) Reading from the DRW initiates a read from the address specified by the
TAR. When the read access completes, the value is returned from the DRW.""")

TAR = components.Register('TAR', [], 0x04, 32, 
                 access='read-write',
                 fullname='Transfer Address components.Register',
                 descr="""\
The TAR holds the address for the next access to the memory system, or set
of debug resources, connected to the MEM-AP. The MEM-AP can be configured so
that the TAR is incremented automatically after each memory access. Reading or
writing to the TAR does not cause a memory access.""")

IDR = components.Register('IDR', [], 0xFC, 32, 
                 access='read-only',
                 fullname='Identification components.Register', 
                 descr="""\
The Identification components.Register identifies the Access Port. It is a read-only
register, implemented in the last word of the AP register space, at offset 0xFC.
An IDR of zero indicates that no AP is present.""")

WCR = components.Register('WCR', [], 0x04, 32,
                 access='read-write',
                 fullname='Wire Control components.Register',
                 descr="""\
The Wire Control components.Register is always present on any SW-DP implementation. Its
purpose is to select the operating mode of the physical serial port connection
to the SW-DP. On a SW-DP, the WCR is a read/write register at address 0x4 on
read and write operations when the CTRLSEL bit in the Select components.Register is set to
1.""")

RDBUFF = components.Register('RDBUFF', [], 0x0C, 32,
                    access='read-only',
                    fullname='Read Buffer',
                    descr="""\
On a SW-DP, performing a read of the Read Buffer captures data from the AP,
presented as the result of a previous read, without initiating a new AP
transaction. This means that reading the Read Buffer returns the result of the
last AP read access, without generating a new AP access. After you have read
the Read Buffer, its contents are no longer valid. The result of a second read
of the Read Buffer is UNPREDICTABLE.""")

IDCODE = components.Register('IDCODE', [], 0x00, 32,
                    access='read-only',
                    fullname='Identification Code',
                    descr="""\
The Identification Code components.Register is always present on all DP implementations. It
provides identification information about the ARM Debug Interface.""")

ABORT = components.Register('ABORT', 
                   [components.BitField('ORUNERRCLR', 4, 1, fullname='Overrun Error Clear', 
                                        descr="""\
Write 1 to this bit to clear the STICKYORUN overrun error flag to 0."""),
                    components.BitField('WDERRCLR', 3, 1, fullname='Write Data Error Clear', 
                                        descr="""\
Write 1 to this bit to clear the WDATAERR write data error flag to 0"""),
                    components.BitField('STKERRCLR', 2, 1, fullname='Sticky Error Clear', descr="""\
Write 1 to this bit to clear the STICKYERR sticky error flag to 0."""),
                    components.BitField('STKCMPCLRa', 1, 1, fullname='Sticky Compare Error Clear', descr="""\
Write 1 to this bit to clear the STICKYCMP sticky compare flag to 0."""),
                    components.BitField('DAPABORT', 0, 1, fullname='DAP Abort', descr="""\
Write 1 to this bit to generate a DAP abort. This aborts the current AP
transaction. Do this only if the debugger has received WAIT responses over an
extended period.""")],
                   0x00, 32, 
                   access='write-only',
                   fullname='AP Abort',
                   descr='The AP Abort components.Register')

CTRLSTAT = components.Register('CTRLSTAT',
                      [components.BitField('CSYSPWRUPACK', 31, 1, fullname='System Power Up Acknowledge'),
                       components.BitField('CSYSPWRUPREQ', 30, 1, fullname='System Power Up Request'),
                       components.BitField('CDBGPWRUPACK', 29, 1, fullname='Debug Power Up Acknowledge'),
                       components.BitField('CDBGPWRUPREQ', 28, 1, fullname='Debug Power Up Request'),
                       components.BitField('CDBGRSTACK', 27, 1, fullname='Debug Reset Acknowledge'),
                       components.BitField('CDBGRSTREQ', 26, 1, fullname='Debug Reset Request'),
                       components.BitField('TRNCNT', 12, 12, fullname='Transaction Counter'),
                       components.BitField('MASKLANE', 8, 4, descr="""\
Indicates the bytes to be masked in pushed compare and pushed verify
operations."""), 
                       components.BitField('WDATAERR', 7, 1, fullname='Write Data Error', 
                                           descr="""\
This bit is set to 1 if a Write Data Error occurs. This happens if:

1) There is a a parity or framing error on the data phase of a write.
2) A write that has been accepted by the DP is then discarded without being
submitted to the AP.

This bit can only be cleared to 0 by writing 1 to the WDERRCLR field of the AP
Abort components.Register, see The AP Abort components.Register.  After a power-on
reset this bit is 0."""),
                       components.BitField('READOK', 6, 1, descr="""\
This bit is set to 1 if the response to the previous AP or RDBUFF read was
OK. It is cleared to 0 if the response was not OK."""),
                       components.BitField('STICKYERR', 5, 1, fullname='Sticky Error',
                                           descr="This bit is set to 1 if an error is returned by an AP transaction."),
                       components.BitField('STICKYCMP', 4, 1, fullname='Sticky Compare',
                                           descr="""This bit is set to 1 when a match occurs on a pushed compare or a pushed verify operation."""),
                       components.BitField('TRNMODE', 2, 2, fullname='Transfer Mode', 
                                           descr="""This field sets the transfer mode for AP operations."""),
                       components.BitField('STICKYORUN', 1, 1,  fullname='Sticky Overrun',
                                           descr="""If overrun detection is enabled, this bit is set to 1 when an overrun occurs."""),
                       components.BitField('ORUNDETECT', 0, 1, fullname='Overrun Detect', 
                                           descr="""This bit is set to 1 to enable overrun detection.""")],
                      0x04, 32, 
                      access='read-write',
                      fullname='DP Control/Status',
                      descr="""\
The Control/Status components.Register is always present on all DP
implementations. Its provides control of the DP, and status information about
the DP.""")

SELECT = components.Register('SELECT', 
                    [components.BitField('APSEL', 24, 8, fullname='AP Select', 
                                         descr="Selects the current AP."),
                     components.BitField('APBANKSEL', 4, 4, fullname='AP Bank Select', 
                                         descr="Selects the active four-word register bank on the current AP"),
                     components.BitField('CTRLSEL', 0, 1, 
                                         [components.EnumeratedValue('CTRLSEL', 0, descr='Control Status components.Register'),
                                          components.EnumeratedValue('CTRLSEL', 1, descr='Wire Control components.Register')],
                                         fullname='CTRL Select', 
                                         descr="""\
SW-DP Debug Port address bank select. Controls which DP register is selected at
address b01 on a SW-DP.""")
                    ],
                    0x08, 32,
                    access='write-only',
                    fullname='Select',
                    descr="""\
The AP Select components.Register is always present on all DP implementations. Its
main purpose is to select the current Access Port (AP) and the active four-word
register bank within that AP.""")

RESEND = components.Register('RESEND',
                    [components.BitField('RESEND', 0, 32, 
                                         descr="The value that was returned by the last AP read or DP RDBUFF read.")],
                    0x08, 32, 
                    access='read-only',
                    fullname='Read Resend',
                    descr="""\
Performing a read to the RESEND register does not capture new data from the
AP. It returns the value that was returned by the last AP read or DP RDBUFF
read.  Reading the RESEND register enables the read data to be recovered from a
corrupted SW transfer without having to re-issue the original read request or
generate a new access to the connected debug memory system.  The RESEND register
can be accessed multiple times. It always return the same value until a new
access is made to the DP RDBUFF register or to an AP register.""")


class Port(blocks.DeviceBlock):
    """
    Models a generic hardware block that lives in an address space *and* defines
    it's own independent address space.

    Parameters
    ----------
    mnemonic : str
        Shorthand or abbreviated name of block.
    subblocks : list-like
        All the children of this block.
    port : int
        The 'port' address of this block.
    lane_width : int
        Defines the number of data bits uniquely selected by each address. For
        example, a value of 8 denotes that the device is byte-addressable.
    bus_width : int
        Defines the bit-width of the maximum single data transfer supported by
        the bus infrastructure. For example, a value of 32 denotes that the
        device bus can transfer a maximum of 32 bits in a single transfer.
    bind : bool
        Tells the constructor whether or not to bind the subblocks as attributes
        of the Block instance.
    fullname : str
        Expanded name or display name of block.
    descr : str
        A string describing functionality, usage, and other relevant notes about
        the block.
    """
    _dynamicBinding = True
    _macrokey = _attrs = 'port'
    _fmt="{name} ({mnemonic}, {port})"

    def __init__(self, mnemonic, registers, port, lane_width, bus_width,
                 bind=True, fullname=None, descr='-', kwattrs={}):
        super(Port, self).__init__(mnemonic, registers, lane_width, bus_width,
                                   bind=bind, fullname=fullname, descr=descr,
                                   kwattrs=kwattrs)
        self._port = utils.HexValue(port)

        for blk in self.walk():
            blk.root = self

        for reg in self:
            reg._address = utils.HexValue(reg._address, 8)


class AccessPort(Port):
    # IDR = IDR # all access ports require an IDR

    def _read(self, address, size):
        self.root.select(self._port, (address&0xF0) >> 4)
        return self.root.read(1, address&0xF)

    def _write(self, address, value, size):
        self.root.select(self._port, (address&0xF0) >> 4)
        self.root.write(1, address&0xF, value)


class DebugPort(Port):

    def _read(self, address, size):
        return self.root.read(0, address)

    def _write(self, address, value, size):
        self.root.write(0, address, value)


DP = DebugPort('DP', [IDCODE, ABORT, CTRLSTAT, SELECT, RESEND, WCR, RDBUFF], 0, 32, 32,
                 fullname='Debug Port', descr="""\
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


MEMAP = AccessPort('MEMAP', [CSW, TAR, DRW, IDR], 0, 32, 32,
                   fullname='Memory Access Port', descr="""\
A MEM-AP provides a DAP with access to a memory subsystem. Another way of
describing the operation of a MEM-AP is that:

1) A debug component implements a memory-mapped abstraction of a set of resources.
2) The MEM-AP provides AP access to those resources.

However, an access to a MEM-AP might only access a register within the MEM-AP,
without generating a memory access.""")


class DAPLink(devicelink.DeviceLink, blocks.DeviceBlock):
    MEMAP = MEMAP
    DP = DP

    def __new__(cls, *args, **kwargs):
        return blocks.DeviceBlock.__new__(cls, 'DAP', [cls.MEMAP, cls.DP], 32, 32,
                                          fullname='Debug Access Port', bind=False)

    def __init__(self, transport):
        blocks.DeviceBlock.__init__(self, 'DAP', [self.MEMAP,self.DP], 32, 32,
                                    fullname='Debug Access Port')
        assert isinstance(transport, Transport), "Link must be of Transport type"
        devicelink.DeviceLink.__init__(self, transport)

        for blk in self:
            blk._macrovalue = utils.HexValue(blk._macrovalue, 8)
            blk.root = self

    def connect(self):
        """
        Establish a connection to the Debug Access Port.
        """
        super(DAPLink, self).connect()

        # read ID code to confirm synchronization
        logging.info('IDCODE: %s', self.DP.IDCODE.value)

        # clear errors
        self.DP.ABORT = 0x1F

        # Reset CTRL flags to default values
        self.DP.CTRLSTAT.MASKLANE = 0xF
        self.DP.CTRLSTAT.TRNMODE = 0

        # Reset the AP, AP bank, and CTRLSEL to their default
        self.DP.SELECT = 0

        # set clock frequency
        # self.setSWJClock(frequency)

        # configure transfer
        # self.transferConfigure()

        # configure swd protocol
        # self.swdConfigure()

        # Do a system and debug power up request
        self.DP.SELECT = 0
        self.DP.CTRLSTAT.pack(CSYSPWRUPREQ=1, CDBGPWRUPREQ=1)
        mask = self.DP.CTRLSTAT.CSYSPWRUPACK._mask | self.DP.CTRLSTAT.CDBGPWRUPACK._mask
        while (self.DP.CTRLSTAT&mask) != mask: None

        # Prod for support of transfers smaller than 32 bits
        self.MEMAP.CSW.SIZE = 0
        if self.MEMAP.CSW.SIZE == 0:
            self._lane_width = 8 << 0
            return

        self.MEMAP.CSW.SIZE = 1
        if self.MEMAP.CSW.SIZE == 1:
            self._lane_width = 8 << 1
            return

        self._lane_width = 8 << 2

    def select(self, port, bank):
        apsel = self.DP.SELECT.APSEL.value
        banksel = self.DP.SELECT.APBANKSEL.value

        if apsel != port:
            self.DP.SELECT.APSEL = port
        if banksel != bank:
            self.DP.SELECT.APBANKSEL = bank

    def _read(self, APnDP, address):
        assert (address&~0b1100) == 0, "Invalid register address; should be of form 0bxx00"

        try:
            self.transport.sendRequest(APnDP, 1, address & 0x0F)
        except Transport.TransferFault:
            self.DP.ABORT.STKERRCLR = 1
            raise

        return self.transport.readPacket()
    read = _read

    def _write(self, APnDP, address, data):
        assert (address&~0b1100) == 0, "Invalid register address; should be of form 0bxx00"

        try:
            self.transport.sendRequest(APnDP, 0, address & 0x0F)
        except Transport.TransferFault:
            self.DP.ABORT.STKERRCLR = 1
            raise

        self.transport.sendPacket(data)
    write = _write

    def memWrite(self, addr, data, accessSize=32):
        self.DP.SELECT = 0
        self.MEMAP.CSW = 0x23000052 | accessSize >> 4
        self.MEMAP.TAR = addr

        if accessSize == 8:
            self.MEMAP.DRW = data << ((addr & 0x03) << 3)
        elif accessSize == 16:
            self.MEMAP.DRW = data << ((addr & 0x02) << 3)
        else:
            self.MEMAP.DRW = data

    def memRead(self, addr, accessSize=32):
        self.DP.SELECT = 0
        self.MEMAP.CSW = 0x23000052 | accessSize >> 4
        self.MEMAP.TAR = addr

        if accessSize == 8:
            return self.MEMAP.DRW >> ((addr & 0x03) << 3) & 0xff
        elif accessSize == 16:
            return self.MEMAP.DRW >> ((addr & 0x02) << 3) & 0xffff
        else:
            return self.MEMAP.DRW.value
