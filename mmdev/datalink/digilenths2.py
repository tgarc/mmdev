from mmdev.lib.userconfig import UserConfig
from ftd2xx import FTD2xx

digilent_cfg = UserConfig()
digilent_cfg.FTDI_GPIO_MASK = 0x60a3
digilent_cfg.GPIO_WMASK = 0x60a0
digilent_cfg.GPIO_RMASK = 0x6080
digilent_cfg.CABLE_NAME = 'Digilent USB Device'
digilent_cfg.SHOW_CONFIG = False
digilent_cfg.CABLE_DRIVER = 'ftdi'

class DigilentHS2(FTD2xx):
    def __init__(self):
        super(DigilentHS2, self).__init__(digilent_cfg)

