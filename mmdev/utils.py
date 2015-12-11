def to_gdbinit(dev):
    import StringIO

    fh = StringIO.StringIO()
    blkfmt = "set $%s = (unsigned long *) 0x%08x"
    bitfmt = "set $%s = (unsigned long) 0x%08x"    
    for blkname, blk in dev.iteritems():
        print >> fh, '#', blkname, blk.name
        print >> fh, '#', '='*58
        print >> fh, blkfmt % (blkname.lower(), blk.address)
        print >> fh
        for regname, reg in blk.iteritems():
            print >> fh, '#', regname.lower(), reg.name.lower()
            print >> fh, '#', '-'*(len(regname)+len(reg.name)+1)
            print >> fh, blkfmt % (regname.lower(),reg.address)
            for bfname, bits in reg.iteritems():
                print >> fh, bitfmt % (bfname.lower(), bits.mask)
            print >> fh
    gdbinit = fh.getvalue()
    fh.close()

    return gdbinit

def export(devnode, glbls):
    glbls.update(devnode.iteritems())

def to_json(dev, **kwargs):
    return json.dumps(dev.to_ordered_dict(), **kwargs)

def to_ordered_dict(dev):
    dct = _OrderedDict()
    dct['mnemonic'] = dev.mnemonic
    dct['name'] = dev.name
    dct['descr'] = dev.descr

    blocks = _OrderedDict()
    registers = _OrderedDict()
    bitfields = _OrderedDict()

    blknames = []
    for blkname, blk in dev.iteritems():
        blkd = _OrderedDict()
        blkd['mnemonic'] = blk.mnemonic
        blkd['name'] = blk.name
        blkd['descr'] = blk.descr
        blkd['address'] = "0x%08x" % blk.address
        blknames.append(blkname)

        regnames = []
        for regname, reg in blk.iteritems():
            regd = _OrderedDict()
            regd['mnemonic'] = reg.mnemonic
            regd['name'] = reg.name
            regd['descr'] = reg.descr
            regd['address'] = "0x%08x" % reg.address
            regnames.append(regname)

            bitnames = []
            for bfname, bits in reg.iteritems():
                bitsd = _OrderedDict()
                bitsd['mnemonic'] = bits.mnemonic
                bitsd['name'] = bits.name
                bitsd['descr'] = bits.descr
                bitsd['mask'] = "0x%08x" % bits.mask
                bitnames.append(bfname)

                bitfields[bfname] = bitsd
            regd['bitfields'] = bitnames
            registers[regname] = regd
        blkd['registers'] = regnames
        blocks[blkname] = blkd

    dct['blocks'] = blocks
    dct['registers'] = registers
    dct['bitfields'] = bitfields

    return dct


