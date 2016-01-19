from mmdev.jtag.discover import Chain
from mmdev.interface import Interface
from mmdev.utils import HexValue


class FTD2xx(Interface):

    def __init__(self, config):
        super(FTD2xx, self).__init__()
        self.config = config
        self.driver = None

    def connect(self):
        self.disconnect()

        cablemodule = self.config.getcable()
        if self.config.CABLE_NAME is None:
            cablemodule.showdevs()
            raise Exception("FTD2xx Error: Could not open device")

        self.driver = cablemodule.d2xx.FtdiDevice(self.config)
    
    def write(self, data, wlen=None):
        self._clock_out(len(data), self.config.GPIO_WMASK, data)

    def read(self, rlen):
        return self._clock_out(rlen, self.config.GPIO_RMASK)

    def _set_gpio(self, value):
        self.driver.write_gpio(value)

    def _get_gpio(self):
        return HexValue(self.driver.read_gpio())

    g = property(_get_gpio, _set_gpio)

    def _clock_out(self, clklen, gpio_mask, data=None):
        if data is None:
            data = '0'*clklen

        result = []
        for ch in data:
            value = gpio_mask
            value |= 2 if ch == '1' else 0
            self.g = value
            _ = self.g
            g = self.g
            self.g = value | 1
            #print hex(g),str(g)
            result.append('1' if g & 4 else '0')
        return ''.join(result)

    def disconnect(self):
        if self.driver is not None:
            return self.driver.Close()
