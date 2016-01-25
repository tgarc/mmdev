from mmdev.transport import Transport
import logging

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

        logging.debug("WDATA %s (0x%08x)" % (data[1:-1], int(data[-2:0:-1], base=2)))
        self.interface.write(data)

    def readPacket(self):
        # read 32bit word + 1 bit parity, and clock 1 additional cycle to
        # satisfy turnaround for next transmission
        x = self.interface.read(34)
        logging.debug("RDATA %s (0x%08x)" % (x[31::-1], int(x[:31], base=2)))
        data, presp = int(x[31::-1], 2), int(x[32], 2)

        parity = data
        parity = (parity ^ (parity >> 16))
        parity = (parity ^ (parity >> 8))
        parity = (parity ^ (parity >> 4))
        parity = (parity ^ (parity >> 2))
        parity = (parity ^ (parity >> 1)) & 1

        if parity ^ presp:
            raise Transport.TransferError("Parity Error")

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
        logging.debug('RQST %s (apndp=%d, rnw=%d, a23=0x%x)' % (rqst, apndp, rnw, a23))
        self.interface.write(rqst)

        # wait 1 TRN then read 3 bit ACK
        ack = self.interface.read(4)
        logging.debug('ACK %s' % ack[3:0:-1])
        ack = int(ack[3:0:-1],2)

        if ack!=ACK_OK and ack!=ACK_WAIT:
            raise Transport.TransferError('Received invalid ACK ({:#03b})'.format(ack))

        return ack
