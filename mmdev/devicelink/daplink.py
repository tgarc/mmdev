from mmdev import utils
from mmdev.transport import Transport
from mmdev.devicelink import DeviceLink
import logging

logger = logging.getLogger(__name__)


# AP Control and Status Word definitions
CSW_DBGSTAT  =  0x00000040
CSW_TINPROG  =  0x00000080
CSW_HPROT    =  0x02000000
CSW_MSTRTYPE =  0x20000000
CSW_MSTRCORE =  0x00000000
CSW_MSTRDBG  =  0x20000000
CSW_RESERVED =  0x01000000


class DAPLink(DeviceLink):
    """
    Models an ADIv5 compliant Serial Wire Debug interface.
    """
    def __new__(cls, transport, descriptorfile='data/dap.json', **kwparse):
        return super(DAPLink, cls).__new__(cls, transport, descriptorfile, **kwparse)

    def __init__(self, transport, descriptorfile='data/dap.json', **kwparse):
        super(DAPLink, self).__init__(transport, descriptorfile, **kwparse)

        for blk in self:
            blk._macrovalue = utils.HexValue(blk._macrovalue, 8)
            blk.root = self

    def connect(self):
        """
        Establish a connection to the Debug Access Port.
        """
        super(DAPLink, self).connect()

        # read ID code to confirm synchronization
        logger.info('IDCODE: %s', self.DP.IDCODE.value)

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
            self.MEMAP._laneWidth = 8 << 0
            return

        self.MEMAP.CSW.SIZE = 1
        if self.MEMAP.CSW.SIZE == 1:
            self.MEMAP._laneWidth = 8 << 1
            return

        self.MEMAP._laneWidth = 8 << 2

    def probe(self):
        baseaddr = self.MEMAP.BASE.BASEADDR.value
        self.MEMAP.TAR = baseaddr << self.MEMAP.BASE.BASEADDR._address
        try:
            read = self.MEMAP.DRW.value
        except Transport.FaultResponse:
            raise DeviceLink.DeviceLinkException("No such luck. Base address of the debug components is inaccessible.")

    def apselect(self, port, bank):
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
        except Transport.FaultResponse:
            self.DP.ABORT.STKERRCLR = 1
            raise

        return self.transport.readPacket()
    read = _read

    def _write(self, APnDP, address, data):
        assert (address&~0b1100) == 0, "Invalid register address; should be of form 0bxx00"

        try:
            self.transport.sendRequest(APnDP, 0, address & 0x0F)
        except Transport.FaultResponse:
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
