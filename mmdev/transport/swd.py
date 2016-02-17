from transport import Transport
import logging
import time

logger = logging.getLogger(__name__)

IDCODE = 0 << 2
READ = 1 << 1
WRITE = 0 << 1
VALUE_MATCH = 1 << 4
MATCH_MASK = 1 << 5

ACK_OK = 1
ACK_WAIT = 2
ACK_FAULT = 4

reverse_bits = lambda b,w: ("{0:0%db}" % w).format(b)[::-1]


class SWD(Transport):

    def connect(self):
        self.datalink.connect()

        # Perform a connect/reset sequence
        self.line_reset()

        # switch from jtag to swd
        self.JTAG2SWD()

    def disconnect(self):
        try:
            self.line_reset()
        finally:
            self.datalink.disconnect()

    def line_reset(self):
        self.datalink.write('1'*56)

    def JTAG2SWD(self):
        # send the 16bit JTAG-to-SWD sequence
        self.datalink.write(reverse_bits(0x9EE7,w=16))

        self.line_reset()

        self.datalink.write('0'*8)

    def sendPacket(self, data):
        parity = data
        parity = (parity ^ (parity >> 16))
        parity = (parity ^ (parity >> 8))
        parity = (parity ^ (parity >> 4))
        parity = (parity ^ (parity >> 2))
        parity = (parity ^ (parity >> 1)) & 1

        # Insert one turnaround period (needed between reception of ACK and
        # transmission of data) followed by the data word and parity bit
        data = '0' + reverse_bits(data,w=32) + ('1' if parity else '0')

        logger.debug("WDATA %s (0x%08x)" % (data[1:-1], int(data[-2:0:-1], base=2)))
        self.datalink.write(data)

    def readPacket(self):
        # read 32bit word + 1 bit parity, and clock 1 additional cycle to
        # satisfy turnaround for next transmission
        x = self.datalink.read(34)
        logger.debug("RDATA %s (0x%08x)" % (x[31::-1], int(x[31::-1], base=2)))
        data, presp = int(x[31::-1], 2), int(x[32], 2)

        parity = data
        parity = (parity ^ (parity >> 16))
        parity = (parity ^ (parity >> 8))
        parity = (parity ^ (parity >> 4))
        parity = (parity ^ (parity >> 2))
        parity = (parity ^ (parity >> 1)) & 1

        if parity ^ presp:
            raise self.InvalidResponse("Parity Error")

        return data

    def sendRequest(self, apndp, rnw, a23):
        """
        Sends an SWD 4 bit request packet (APnDP | RnW | A[2:3]) and
        verifies the response from the target
        """
        rqst = a23 | rnw << 1 | apndp
        parity = rqst
        parity ^= parity >> 1
        parity ^= parity >> 2        
        parity &= 1

        rqst = '1{}{}01'.format(reverse_bits(rqst,w=4), '1' if parity else '0')
        logger.debug('RQST %s (apndp=%d, rnw=%d, a23=0x%x)' % (rqst, apndp, rnw, a23))
        self.datalink.write(rqst)

        # wait 1 TRN then read 3 bit ACK
        ack = self.datalink.read(4)
        logger.debug('ACK %s' % ack[3:0:-1])
        ack = int(ack[3:0:-1],2)

        tries = 0
        while ack == ACK_WAIT and tries < 3:
            time.sleep(0.1)
            self.datalink.read(1) # insert a turnaround before sending next request

            logger.debug('RQST %s (apndp=%d, rnw=%d, a23=0x%x)' % (rqst, apndp, rnw, a23))
            self.datalink.write(rqst)

            ack = self.datalink.read(4)
            logger.debug('ACK %s' % ack[3:0:-1])
            ack = int(ack[3:0:-1],2)
            tries += 1
        if tries == 3:
            raise self.BusyResponse("DAP stuck in WAIT state")

        if ack==ACK_FAULT:
            raise self.FaultResponse('Target responded with FAULT error code')
        elif ack==0b111:
            raise self.NoACKResponse('No response from target.')
        elif ack!=ACK_OK:
            raise self.InvalidResponse('Received invalid ACK ({:#03b})'.format(ack))

        return ack
