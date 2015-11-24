# mmdev
futzing around with representing a DUT as a memory mapped device

# Tutorial

### Setting up a device

``mmdev.parser`` contains the parser framework for converting a device definition file to a ``Device`` object. An SVD parser is included since it is the only standardized device definition file for microcontrollers that I'm aware of. There are a few toy formats included (jcfg and pycfg) along with their parsers to give further examples of how to write a parser.

Anyway, ``Device`` includes a ``from_xxxfmt`` function that calls out to the proper parser and create a device object.

```python
>>> import mmdev as mmd
>>> arm = mmd.device.Device.from_svd('STM32F20x.svd')
>>> arm
<Device 'STM32F20x'>
```

### Sub-blocks as attributes

A Device object is simply a collection of peripheral objects which are in turn collections of register objects which...well, you get the picture. Device objects and their constituent components (termed sub-blocks) are organized in a tree fashion with ``Device``, ``Register``, ``Peripheral``, and ``BitField`` all inheriting from the ``BlockNode`` class (i.e. all mmdev objects are blocks). At each block level, subblocks exist as attributes bound to their parent block by their mnemonic (shorthand name or abbreviation).

```python
>>> arm.
arm.adc1             arm.ethernet_ptp     arm.gpioi            arm.otg_fs_pwrclk    arm.tim1             arm.tree
arm.adc2             arm.exti             arm.i2c1             arm.otg_hs_device    arm.tim10            arm.typename
arm.adc3             arm.find             arm.i2c2             arm.otg_hs_global    arm.tim11            arm.uart4
arm.adc_common       arm.flash            arm.i2c3             arm.otg_hs_host      arm.tim12            arm.uart5
arm.attrs            arm.from_devfile     arm.items            arm.otg_hs_pwrclk    arm.tim13            arm.usart1
arm.can1             arm.from_json        arm.iteritems        arm.parent           arm.tim14            arm.usart2
arm.can2             arm.from_pycfg       arm.iterkeys         arm.pwr              arm.tim2             arm.usart3
arm.crc              arm.from_svd         arm.itervalues       arm.rcc              arm.tim3             arm.usart6
arm.dac              arm.fsmc             arm.iwdg             arm.read             arm.tim4             arm.values
arm.dbg              arm.gpioa            arm.keys             arm.rng              arm.tim5             arm.vendor
arm.dcmi             arm.gpiob            arm.ls               arm.root             arm.tim6             arm.width
arm.description      arm.gpioc            arm.mnemonic         arm.rtc              arm.tim7             arm.write
arm.dma1             arm.gpiod            arm.name             arm.sdio             arm.tim8             arm.wwdg
arm.dma2             arm.gpioe            arm.nvic             arm.spi1             arm.tim9             
arm.ethernet_dma     arm.gpiof            arm.otg_fs_device    arm.spi2             arm.to_gdbinit       
arm.ethernet_mac     arm.gpiog            arm.otg_fs_global    arm.spi3             arm.to_json          
arm.ethernet_mmc     arm.gpioh            arm.otg_fs_host      arm.syscfg           arm.to_ordered_dict  
```

### ls and tree
``ls`` and ``tree`` are two convenience functions for interactive viewing.

``ls`` simply lists all the components at the current block level.

```python
>>> arm.ls
Device (STM32F20x, 32-bit, vendor=Unknown)
        0xE0042000 DBG
        0xE000E000 NVIC
        0xA0000000 FSMC
        0x50060800 RNG
        0x50050000 DCMI
        0x50000E00 OTG_FS_PWRCLK
        0x50000800 OTG_FS_DEVICE
        0x50000400 OTG_FS_HOST
        0x50000000 OTG_FS_GLOBAL
        0x40040E00 OTG_HS_PWRCLK
        0x40040800 OTG_HS_DEVICE
        0x40040400 OTG_HS_HOST
        0x40040000 OTG_HS_GLOBAL
        0x40029000 Ethernet_DMA
        0x40028700 Ethernet_PTP
...
```

``tree`` is very similar to ``ls`` but descends two block levels.

```python
>>> arm.dbg.tree
Peripheral (DBG, 0xE0042000)
DBGMCU_APB2_FZ (DBGMCU_APB2_FZ, 0xE004200C)
        0x00040000 DBG_TIM11_STOP
        0x00020000 DBG_TIM10_STOP
        0x00010000 DBG_TIM9_STOP
        0x00000002 DBG_TIM8_STOP
        0x00000001 DBG_TIM1_STOP
DBGMCU_APB1_FZ (DBGMCU_APB1_FZ, 0xE0042008)
        0x04000000 DBG_CAN2_STOP
        0x02000000 DBG_CAN1_STOP
        0x00800000 DBG_J2C3SMBUS_TIMEOUT
        0x00400000 DBG_J2C2_SMBUS_TIMEOUT
        0x00200000 DBG_J2C1_SMBUS_TIMEOUT
...
DBGMCU_CR (DBGMCU_CR, 0xE0042004)
        0x00000080 TRACE_MODE
        0x00000020 TRACE_IOEN
        0x00000004 DBG_STANDBY
        0x00000002 DBG_STOP
        0x00000001 DBG_SLEEP
DBGMCU_IDCODE (DBGMCU_IDCODE, 0xE0042000)
        0x00100000 REV_ID
        0x0000000C DEV_ID
```

### Encoding of device attributes

There are a couple of ways in which block level metadata is encoded.

**attrs**

Just gives the block relevant attributes as a dictionary. This will likely be expanded in the future to include metadata that is not part of the block model.

```python
>>> arm.dbg.attrs
{'address': 3758366720,
 'description': 'Debug support',
 'mnemonic': 'DBG',
 'name': 'Peripheral',
 'typename': 'Peripheral'}
```

**\__repr__**

The ``__repr__`` for a block node gives a pythonic object level description of a block, listing the most relevant attributes.

```python
>>> arm
<Device 'STM32F20x'>
>>> arm.dbg
<Peripheral 'DBG' in Device 'STM32F20x' at 0xe0042000>
>>> arm.dbg.dbgmcu_cr
<Register 'DBGMCU_CR' in Peripheral 'DBG' at 0xe0042004>
>>> arm.dbg.dbgmcu_cr.trace_ioen
<BitField 'TRACE_IOEN' in Register 'DBGMCU_CR' & 0x00000020>
```

**\__doc__**

When available, block descriptions are included in the ``__doc__`` strings. YMMV since the level of detail is completely up to the vendor.

```python
>>> arm.dbg.dbgmcu_cr?
Type:        Register
String form: <Register 'DBGMCU_CR' in Peripheral 'DBG' at 0xe0042004>
File:        ~/git/mmdev/mmdev/blocks.py
Docstring:   Control Register
```
