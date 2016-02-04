mnemonic = 'cm3'
name = 'ARM Cortex-M3'

BLK_NAME = {
    'ITM': "Instrumentation Trace Macrocell"
  , 'SCS': "System Control Space"
}

REG_NAME = {
    'DEMCR'      : "Debug Exception and Monitor Control Register"
  , 'DHCSR'      : "Debug Halt Control and Status Register"    
  , 'ITM_TCR'    : "Trace Control Register"
  , 'TPIU_ACPR'  : "Asynchronous Clock Prescaler Register"
  , 'TPIU_SPPR'  : "Selected Pin Protocol Register"
  , 'TPIU_CSPSR' : "Current Synchronous Port Size Register"
}

BIT_NAME = {}

BLK_DESCR = {}

REG_DESCR = {}

BIT_DESCR = {
      'TPIU_TYPE_b11': "Serial Wire Output (UART/NRZ) supported when this bit is set."
    , 'TPIU_TYPE_b10': "Serial Wire Output (Machester encoding) supported when this bit is set."
    , 'MODE': "00: Synchronous Trace Port Mode\n 01: Manchester\n 10: UART/NRZ\n 11: Reserved"
    , 'PRESCALE': "Value used as a division ratio (baud rate prescaler). SWO output clock ="\
                  "Asynchronous_Reference_Cock/(value+1)"
    , 'TSPrescale': "Timestamp prescaler, used with the trace packet reference clock. The reference"\
                    "clock source is selected by SWOENA. Defined as a power of"\
                    "four. These bits are cleared on Power-up reset."
    , 'TXENA':  "Enable hardware event packet emission to the TPIU from the DWT. This bit is"\
                "cleared on Power-up reset."
    , 'SWOENA': "Enables aysynchronous-specific usage model for timestamps (when TSENA==1).\n 0:"\
                "mode disabled\n 1: Timestamp counter uses lineout (data"\
                "related) clock from TPIU interface."
}

REG_MAP = {
    'SCS': {
        'AIRCR'   : 0xE000ED0C
      , 'DHCSR'   : 0xE000EDF0
      , 'DCRSR'   : 0xE000EDF4
      , 'DCRDR'   : 0xE000EDF8
      , 'DEMCR'   : 0xE000EDFC
      , 'DFSR'    : 0xE000ED30
    }
  , 'ITM': {
        'ITM_TCR' : 0xE0000E80
      , 'ITM_TER' : 0xE0000E00
      , 'ITM_TPR' : 0xE0000E40
      , 'ITM_LAR' : 0xE0000FB0
      , 'ITM_LSR' : 0xE0000FB4
      , 'ITM_STIM': 0xE0000000
    }
  , 'TPIU': {
        'TPIU_TYPE': 0xE0040FC8
      , 'TPIU_ACPR': 0xE0040010
      , 'TPIU_SPPR': 0xE00400F0
      , 'TPIU_CSPSR': 0xE0040004
      , 'TPIU_FFCR': 0xE0040304

    }
  , 'DWT': {
        'DWT_CTRL': 0xE0001000
    }
}

BLK_MAP = {
    'TPIU'      : 0xE0040000
  , 'ETM'       : 0xE0041000
  , 'EPPB'      : 0xE0042000
  , 'ROM_TABLE' : 0xE00FF000
  , 'ITM'       : 0xE0000000
  , 'DWT'       : 0xE0001000
  , 'FPB'       : 0xE0002000
  , 'SCS'       : 0xE000E000
}


BIT_MAP = {
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
      , 'DWTENA'     : 0x00000008
      , 'SYNCENA'    : 0x00000004
      , 'TSENA'      : 0x00000002
      , 'ITMENA'     : 0x00000001
    }
  , 'TPIU_TYPE': {
        'TPIU_TYPE_b11': 0x00000800
      , 'TPIU_TYPE_b10': 0x00000400
    }
  , 'TPIU_SPPR': {
        'MODE': 0x00000003
    }
  , 'TPIU_ACPR': {
        'PRESCALE': 0x0000FFFF
    }
  , 'ITM_TER' : {
        'STIMENA': 0xFFFFFFFF
    }
  , 'ITM_TPR' : {
        'PRIVMASK': 0xFFFFFFFF
    }
  , 'DWT_CTRL': {
        'EXCTRCENA': 0x00010000
    }
  , 'ITM_LSR': {
        'ByteAcc': 0x4
      , 'Access': 0x2
      , 'Present': 0x1
    }
  , 'ITM_LAR': {
        'Lock_Access': 0xFFFFFFFF
    }
  , 'ITM_STIM': {
        'STIMULUS': 0xFFFFFFFF
      , 'FIFOREADY': 0x1
    }
}
