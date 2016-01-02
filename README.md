# mmdev
futzing around with representing a DUT as an SVD-like device tree


# Purpose

There's two roles I wanted ``mmdev`` to fill when I started this project:

1. To serve as an exploratory tool and a reference

``mmdev`` should make it easy to 'poke around' and get familiar with the
features and functionality of a microcontroller from a programmers
perspective. Methods like ``find()``, ``ls()``, and ``tree()`` gives the user
the ability to quickly search and scan through a device without having to scour
a technical reference manual.

2. To serve as a tool for testing and verification

By adding device read and write capability to the functionality provided by (1),
``mmdev`` can provide an environment which allows the user to write test
routines in Python in a highly concise and readable format. SWD read/write
support will be added first since initial development is focused on ARM Cortex-M
products.

I would also like to eventually get ``mmdev`` to fill a third role:

3. To serve as a SVD device file generator/converter

My hope is that I can reduce the work it takes vendors to generate an SVD file
from their own proprietary format by writing a mmdev.device-to-SVD dumper. Then,
for vendors to generate an SVD file for their device, they would only need to
write their own ``mmdev`` parser. By reducing the workload for vendors, I hope
that it will encourage them to support a standardized public-use format (SVD
being the only one around) that would in turn incite the development of freely
available open source tools.


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

The core classes in mmdev - ``Device``, ``Register``, ``Peripheral``, and ``BitField`` - are conceptually hardware blocks, which contain a number of sub-blocks (BitField is the exception). mmdev organizes this natural hierarchy into a Device "tree" where all classes inherit from a common ``Block`` type. At each block level, subblocks exist as attributes bound to their parent block by their mnemonic (shorthand name or abbreviation). Subblocks are also accessible using dict-type attributes ``keys``, ``values`` and their iter* counterparts.

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

``tree`` is very similar to ``ls`` but descends two block levels (you can call _tree() to print all levels).

```python
>>> arm.dbg.tree
Peripheral (DBG, 0xE0042000)
|-- DBGMCU_APB2_FZ (DBGMCU_APB2_FZ, 0xE004200C)
|   |-- BitField (DBG_TIM11_STOP, 0x00040000)
|   |-- BitField (DBG_TIM10_STOP, 0x00020000)
|   |-- BitField (DBG_TIM9_STOP, 0x00010000)
|   |-- BitField (DBG_TIM8_STOP, 0x00000002)
|   `-- BitField (DBG_TIM1_STOP, 0x00000001)
|-- DBGMCU_APB1_FZ (DBGMCU_APB1_FZ, 0xE0042008)
|   |-- BitField (DBG_CAN2_STOP, 0x04000000)
|   |-- BitField (DBG_CAN1_STOP, 0x02000000)
|   |-- BitField (DBG_J2C3SMBUS_TIMEOUT, 0x00800000)
|   |-- BitField (DBG_J2C2_SMBUS_TIMEOUT, 0x00400000)
|   |-- BitField (DBG_J2C1_SMBUS_TIMEOUT, 0x00200000)
|   ...
|   `-- BitField (DBG_TIM2_STOP, 0x00000001)
|-- DBGMCU_CR (DBGMCU_CR, 0xE0042004)
|   |-- BitField (TRACE_MODE, 0x00000080)
|   |-- BitField (TRACE_IOEN, 0x00000020)
|   |-- BitField (DBG_STANDBY, 0x00000004)
|   |-- BitField (DBG_STOP, 0x00000002)
|   `-- BitField (DBG_SLEEP, 0x00000001)
`-- DBGMCU_IDCODE (DBGMCU_IDCODE, 0xE0042000)
    |-- BitField (REV_ID, 0x00100000)
    `-- BitField (DEV_ID, 0x0000000C)
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
