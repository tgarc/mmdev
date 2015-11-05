mnemonic = 'armv7m'
name = 'ARMv7-M'

BLK_NAME = \
{
    'ITM': "Instrumentation Trace Macrocell"
  , 'SCS': "System Control Space"
}

REG_NAME = \
{
    'DEMCR'   : "Debug Exception and Monitor Control Register"
  , 'DHCSR'   : "Debug Halt Control and Status Register"    
  , 'ITM_TCR' : "Trace Control Register"
}

BLK_DESCR = {}

REG_DESCR = {}

BIT_DESCR = {}

BLK_MAP = \
{
    'SCS': ('AIRCR', 'DHCSR', 'DCRSR', 'DCRDR', 'DEMCR')
  , 'ITM': ('ITM_TCR',)
}

MEM_MAP = \
{
    'TPIU'      : (0xE0040000, 0xE0041000)
  , 'ETM'       : (0xE0041000, 0xE0042000)
  , 'EPPB'      : (0xE0042000, 0xE00FF000)
  , 'ROM_TABLE' : (0xE00FF000, 0xE00FFFFF)
  , 'ITM'       : (0xE0000000, 0xE0001000)
  , 'DWT'       : (0xE0001000, 0xE0002000)
  , 'FPB'       : (0xE0002000, 0xE0003000)
  , 'SCS'       : (0xE000E000, 0xE000F000)
}

REG_MAP = \
{
    'DEMCR'   : 0xE000EDFC
  , 'DHCSR'   : 0xE000EDF0
  , 'DCRSR'   : 0xE000EDF4
  , 'DCRDR'   : 0xE000EDF8
  , 'AIRCR'   : 0xE000ED0C
  , 'ITM_TCR' : 0xE0000E80
}

BIT_MAP = \
{
    'DEMCR' : {
        'TRCENA'       : (0x01000000, 24)
      , 'MON_REQ'      : (0x00080000, 19)
      , 'MON_STEP'     : (0x00040000, 18)
      , 'MON_PEND'     : (0x00020000, 17)
      , 'MON_EN'       : (0x00010000, 16)
      , 'VC_HARDERR'   : (0x00000400, 10)
      , 'VC_INTERR'    : (0x00000200,  9)
      , 'VC_BUSERR'    : (0x00000100,  8)
      , 'VC_STATERR'   : (0x00000080,  7)
      , 'VC_CHKERR'    : (0x00000040,  6)
      , 'VC_NOCPERR'   : (0x00000020,  5)
      , 'VC_MMERR'     : (0x00000010,  4)
      , 'VC_CORERESET' : (0x00000001,  0)
  }
  , 'DFSR': {
        'EXTERNAL' : (0x00000010, 4)
      , 'VCATCH'   : (0x00000008, 3)
      , 'DWTTRAP'  : (0x00000004, 2)
      , 'BKPT'     : (0x00000002, 1)
      , 'HALTED'   : (0x00000001, 0)
  }
  , 'DCRSR':  {
        'REGWnR': (0x00010000, 16)
      , 'REGSEL': (0x0008001F,  0)
  }
  , 'DCRDR':  {
        'DBGTMP': (0xFFFFFFFF, 0)
  }
  , 'DHCSR':  {
        'S_RESET_ST'  : (0x02000000, 25)
      , 'S_RETIRE_ST' : (0x01000000, 24)
      , 'S_LOCKUP'    : (0x00080000, 19)
      , 'S_SLEEP'     : (0x00040000, 18)
      , 'S_HALT'      : (0x00020000, 17)
      , 'S_REGRDY'    : (0x00010000, 16)
      , 'C_SNAPSTALL' : (0x00000020,  5)
      , 'C_MASKINTS'  : (0x00000008,  3)
      , 'C_STEP'      : (0x00000004,  2)
      , 'C_HALT'      : (0x00000002,  1)
      , 'C_DEBUGEN'   : (0x00000001,  0)
  }
  , 'AIRCR':   { 
        'ENDIANNESS'    : (0x00008000, 15)
      , 'PRIGROUP'      : (0x00000700,  8)
      , 'SYSRESETREQ'   : (0x00000004,  2)
      , 'VECTCLRACTIVE' : (0x00000002,  1)
      , 'VECTRESET'     : (0x00000001,  0)
  }
  , 'ITM_TCR': {
        'BUSY'       : (0x00800000, 23)
      , 'TraceBusID' : (0x007F0000, 16)
      , 'TSPrescale' : (0x00000300,  8)
      , 'SWOENA'     : (0x00000010,  4)
      , 'TXENA'      : (0x00000008,  3)
      , 'SYNCENA'    : (0x00000004,  2)
      , 'TSENA'      : (0x00000002,  1)
      , 'ITMENA'     : (0x00000001,  0)
  }
}
