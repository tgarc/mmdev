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
    'TPIU'      : 0xE0040000
  , 'ETM'       : 0xE0041000
  , 'EPPB'      : 0xE0042000
  , 'ROM_TABLE' : 0xE00FF000
  , 'ITM'       : 0xE0000000
  , 'DWT'       : 0xE0001000
  , 'FPB'       : 0xE0002000
  , 'SCS'       : 0xE000E000
}

REG_MAP = \
{
    'DEMCR'   : 0xE000EDFC
  , 'DHCSR'   : 0xE000EDF0
  , 'DCRSR'   : 0xE000EDF4
  , 'DCRDR'   : 0xE000EDF8
  , 'AIRCR'   : 0xE000ED0C
  , 'ITM_TCR' : 0xE0000E80
  , 'TPIU_TYPE': 0xE0040FC8
}

BIT_MAP = \
{
    'DEMCR' : {
        'TRCENA'       : 0x01000000
      , 'MON_REQ'      : 0x00080000
      , 'MON_STEP'     : 0x00040000
      , 'MON_PEND'     : 0x00020000
      , 'MON_EN'       : 0x00010000
      , 'VC_HARDERR'   : 0x00000400
      , 'VC_INTERR'    : 0x00000200
      , 'VC_BUSERR'    : 0x00000100
      , 'VC_STATERR'   : 0x00000080
      , 'VC_CHKERR'    : 0x00000040
      , 'VC_NOCPERR'   : 0x00000020
      , 'VC_MMERR'     : 0x00000010
      , 'VC_CORERESET' : 0x00000001
  }
  , 'DFSR': {
        'EXTERNAL' : 0x00000010
      , 'VCATCH'   : 0x00000008
      , 'DWTTRAP'  : 0x00000004
      , 'BKPT'     : 0x00000002
      , 'HALTED'   : 0x00000001
  }
  , 'DCRSR':  {
        'REGWnR': 0x00010000
      , 'REGSEL': 0x0008001F
  }
  , 'DCRDR':  {
        'DBGTMP': 0xFFFFFFFF
  }
  , 'DHCSR':  {
        'S_RESET_ST'  : 0x02000000
      , 'S_RETIRE_ST' : 0x01000000
      , 'S_LOCKUP'    : 0x00080000
      , 'S_SLEEP'     : 0x00040000
      , 'S_HALT'      : 0x00020000
      , 'S_REGRDY'    : 0x00010000
      , 'C_SNAPSTALL' : 0x00000020
      , 'C_MASKINTS'  : 0x00000008
      , 'C_STEP'      : 0x00000004
      , 'C_HALT'      : 0x00000002
      , 'C_DEBUGEN'   : 0x00000001
  }
  , 'AIRCR':   { 
        'ENDIANNESS'    : 0x00008000
      , 'PRIGROUP'      : 0x00000700
      , 'SYSRESETREQ'   : 0x00000004
      , 'VECTCLRACTIVE' : 0x00000002
      , 'VECTRESET'     : 0x00000001
  }
  , 'ITM_TCR': {
        'BUSY'       : 0x00800000
      , 'TraceBusID' : 0x007F0000
      , 'TSPrescale' : 0x00000300
      , 'SWOENA'     : 0x00000010
      , 'TXENA'      : 0x00000008
      , 'SYNCENA'    : 0x00000004
      , 'TSENA'      : 0x00000002
      , 'ITMENA'     : 0x00000001
  }
}
