from deviceparser import *

def _readint(x):
    if x.lower().startswith('0x'):
        return int(x, 16)
    if x.startswith('#'):
        raise Exception("Binary format not support")
    return int(x)


class SVDParser(DeviceParser):
    @classmethod
    def parse_device(cls, devfile):
        import xml.etree.ElementTree as ET

        svd = ET.parse(devfile).getroot()

        name = svd.findtext('displayName', '')
        mnem = svd.findtext('name')
        descr = svd.findtext('description')
        width = _readint(svd.findtext('width'))
        vendor = svd.findtext('vendor', '')

        dev = Device(mnem, fullname=name, descr=descr, width=width, vendor=vendor)
        for pphnode in svd.iter('peripheral'):
            pphaddr = _readint(pphnode.findtext('baseAddress'))
            pph = Peripheral(pphnode.findtext('name'), 
                             pphaddr,
                             fullname=pphnode.findtext('displayName', 'Peripheral'),
                             descr=pphnode.findtext('description', ''))
            for regnode in pphnode.iter('register'):
                reg = Register(regnode.findtext('name'),
                               _readint(regnode.findtext('addressOffset')) + pphaddr,
                               fullname=regnode.findtext('displayName', 'Register'),
                               descr=regnode.findtext('description', ''))
                for bitnode in regnode.iter('field'):
                    mask = _readint(bitnode.findtext('bitWidth')) \
                           << _readint(bitnode.findtext('bitOffset'))
                    bits = BitField(bitnode.findtext('name'),
                                    mask,
                                    fullname=bitnode.findtext('name','BitField'),
                                    descr=bitnode.findtext('description',''))
                    reg._attach_subblock(bits)
                pph._attach_subblock(reg)
            dev._attach_subblock(pph)

        return dev


    # @classmethod
    # def parse_device(cls, devfile):
    #     import xml.etree.ElementTree as ET

    #     svd = ET.parse(devfile).getroot()

    #     name = 'Device'
    #     mnem = svd.findtext('name')
    #     descr = svd.findtext('description')
    #     addressUnitBits = _readint(svd.findtext('addressUnitBits'))
    #     width = _readint(svd.findtext('width'))

    #     defwidth = _readint(svd.findtext('size'))
    #     defaccess = _readint(svd.findtext('access'))
    #     defrval = _readint(svd.findtext('resetValue'))
    #     defrmsk = _readint(svd.findtext('resetMask'))

    #     dev = Device(mnem, fullname=name, descr=descr, width=width)
    #     for pphnode in svd.iter('peripheral'):
    #         pphaddr = _readint(pphnode.findtext('baseAddress'))
    #         pphaddrblk = _parse_address_block(pphnode.findtext('addressBlock'), devaddrblk)
    #         pphvers = pphnode.findtext('version')
    #         pphppend = pphnode.findtext('prependToName')
    #         pphapend = pphnode.findtext('appendToName')
    #         grpname = pphnode.findtext('groupName')

    #         pphoffs = _readint(svd.findtext('offset'), defwidth)
    #         pphdefaccess = _readint(svd.findtext('size'), defaccess)
    #         pphdefrval = _readint(svd.findtext('usage'), defrval)

    #         pphdefwidth = _readint(svd.findtext('size'), defwidth)
    #         pphdefaccess = _readint(svd.findtext('access'), defaccess)
    #         pphdefrval = _readint(svd.findtext('resetValue'), defrval)
    #         pphdefrmsk = _readint(svd.findtext('resetMask'), defrmsk)

    #         pph = dev._create_peripheral(pphnode.findtext('name'), 
    #                                      pphaddr,
    #                                      fullname=pphnode.findtext('displayName', 'Peripheral'),
    #                                      descr=pphnode.findtext('description', ''))
    #         for regnode in pphnode.iter('register'):
    #             reg = pph._create_register(regnode.findtext('name'),
    #                                        _readint(regnode.findtext('addressOffset')) + pphaddr,
    #                                        fullname=regnode.findtext('displayName', 'Register'),
    #                                        descr=regnode.findtext('description', ''))
    #             for bitnode in regnode.iter('field'):
    #                 mask = _readint(bitnode.findtext('bitWidth')) << _readint(bitnode.findtext('bitOffset'))
    #                 reg._create_bitfield(bitnode.findtext('name'),
    #                                      mask,
    #                                      fullname=bitnode.findtext('name','BitField'),
    #                                      descr=bitnode.findtext('description',''))
    #     return dev


    def _parse_enumerated_value(cls, enumerated_value_node):
        return SVDEnumeratedValue(
            name=enumerated_value_node.findtext('name'),
            description=enumerated_value_node.findtext('description'),
            value=_get_int(enumerated_value_node, 'value'),
            is_default=_get_int(enumerated_value_node, 'isDefault')
        )


    def _parse_address_block(cls, address_block_node):
        return SVDAddressBlock(
            _readint(address_block_node.findtext('offset')),
            _readint(address_block_node.findtext('size')),
            address_block_node.findtext('usage')
        )

    def _parse_interrupt(cls, interrupt_node):
        return SVDInterrupt(
            name=interrupt_node.findtext('name'),
            value=_readint(interrupt_node.findtext('value'))
        )


    def parse_field(cls, field_node):
        # for bitnode in regnode.iter('field'):
        #     mask = _readint(bitnode.findtext('bitWidth')) << _readint(bitnode.findtext('bitOffset'))
        #     reg._create_bitfield(bitnode.findtext('name'),
        #                          mask,
        #                          fullname=bitnode.findtext('name','BitField'),
        #                          descr=bitnode.findtext('description',''))

        enumerated_values = []
        for enumerated_value_node in field_node.findall("./enumeratedValues/enumeratedValue"):
            enumerated_values.append(cls._parse_enumerated_value(enumerated_value_node))
			
        bit_range=field_node.findtext('bitRange')
        bit_offset=_readint(field_node.findtext('bitOffset'))
        bit_width=_readint(field_node.findtext('bitWidth'))
        msb=_readint(field_node.findtext('msb'))
        lsb=_readint(field_node.findtext('lsb'))
        if bit_range is not None:
            m=re.search('\[([0-9]+):([0-9]+)\]', bit_range)
            bit_offset=int(m.group(2))
            bit_width=1+(int(m.group(1))-int(m.group(2)))     
        elif msb is not None:
            bit_offset=lsb
            bit_width=1+(msb-lsb)

        return BitField(
            name=field_node.findtext('name'),
            description=field_node.findtext('description'),
            bit_offset=bit_offset,
            bit_width=bit_width,
            access=field_node.findtext('access'),
            enumerated_values=enumerated_values or None,
        )


    def parse_register(cls, register_node):
        fields = []
        for field_node in register_node.findall('.//field'):
            node = cls._parse_field(field_node)
            if cls.remove_reserved is 0 or 'reserved' not in node.name.lower():
                fields.append(node)
        dim = _readint(register_node.findtext('dim'))
        dim_index_text = register_node.findtext('dimIndex')
        if dim is not None:
            if dim_index_text is None:
                dim_index = range(0,dim)                        #some files omit dimIndex 
            elif ',' in dim_index_text:
                dim_index = dim_index_text.split(',')
            elif '-' in dim_index_text:                              #some files use <dimIndex>0-3</dimIndex> as an inclusive inclusive range
                m=re.search('([0-9]+)-([0-9]+)', dim_index_text)
                dim_index = range(int(m.group(1)),int(m.group(2))+1)
        else:
            dim_index = None
        return Register(
            name=register_node.findtext('name'),
            description=register_node.findtext('description'),
            address_offset=_readint(register_node.findtext('addressOffset')),
            size=_readint(register_node.findtext('size')),
            access=register_node.findtext('access'),
            reset_value=_readint(register_node.findtext('resetValue')),
            reset_mask=_readint(register_node.findtext('resetMask')),
            fields=fields,
            dim=dim, 
            dim_increment=_readint(register_node.findtext('dimIncrement')), 
            dim_index=dim_index
        )


    def parse_peripheral(cls, peripheral_node):
        # for regnode in pphnode.iter('register'):
        #     reg = pph._create_register(regnode.findtext('name'),
        #                                _readint(regnode.findtext('addressOffset')) + pphaddr,
        #                                fullname=regnode.findtext('displayName', 'Register'),
        #                                descr=regnode.findtext('description', ''))

        registers = []
        for register_node in peripheral_node.findall('./registers/register'):
            reg = cls._parse_register(register_node)
            if reg.dim and cls.expand_arrays_of_registers is 1:
                for r in duplicate_array_of_registers(reg):
                    registers.append(r)
            elif cls.remove_reserved is 0 or 'reserved' not in reg.name.lower() :
                registers.append(reg)

        interrupts = []
        for interrupt_node in peripheral_node.findall('./interrupt'):
            interrupts.append(cls._parse_interrupt(interrupt_node))

        address_block_nodes = peripheral_node.findall('./addressBlock')
        if address_block_nodes:
            address_block = cls._parse_address_block(address_block_nodes[0])
        else:
            address_block = None

        return Register(
            name=peripheral_node.findtext('name'),
            description=peripheral_node.findtext('description'),
            prepend_to_name=peripheral_node.findtext('prependToName'),
            base_address=_readint(peripheral_node.findtext('baseAddress')),
            address_block=address_block,
            interrupts=interrupts,
            registers=registers,
        )

    # def parse_device(cls, device_node):
    #     peripherals = []
    #     for peripheral_node in device_node.findall('.//peripheral'):
    #         peripherals.append(cls._parse_peripheral(peripheral_node))

    #     cpu_node = device_node.find('./cpu')
    #     cpu = SVDCpu(
    #         name = cpu_node.findtext('name'),
    #         revision = cpu_node.findtext('revision'),
    #         endian = cpu_node.findtext('endian'),
    #         mpu_present = _readint(cpu_node.findtext('mpuPresent')),
    #         fpu_present = _readint(cpu_node.findtext('fpuPresent')),
    #         vtor_present = _readint(cpu_node.findtext('vtorPresent')),
    #         nvic_prio_bits = _readint(cpu_node.findtext('nvicPrioBits')),
    #         vendor_systick_config = cpu_node.findtext('vendorSystickConfig')
    #     )

    #     return cls.create_device(
    #         vendor=device_node.findtext('vendor'),
    #         vendor_id=device_node.findtext('vendorID'),
    #         name=device_node.findtext('name'),
    #         version=device_node.findtext('version'),
    #         description=device_node.findtext('description'),
    #         cpu=cpu, 
    #         address_unit_bits=_readint(device_node.findtext('addressUnitBits')),
    #         width=_readint(device_node.findtext('width')),
    #         peripherals=peripherals,
    #     )

