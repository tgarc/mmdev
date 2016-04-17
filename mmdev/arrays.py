from mmdev import blocks
from mmdev import components


class PeripheralArray(blocks.BlockArray):

    def _getsingleitem(self, i):
        if self._index[i] is None:
            template = self._template
            self._index[i] = components.Peripheral((template.mnemonic + self._suffix) % i, 
                                                   template._nodes,
                                                   template.address + self._intindex[i]*self._elementSize, 
                                                   template.size, 
                                                   bind=True, 
                                                   displayName=(template.displayName + self._suffix) % i,
                                                   description=template.description, kwattrs=template._kwattrs)
            self._index[i].parent = self.parent
            self._index[i].root = self.root

        return self._index[i]


class RegisterArray(blocks.IOBlockArray):

    def _getsingleitem(self, i):
        if self._index[i] is None:
            template = self._template
            newblk = components.Register((template.mnemonic + self._suffix) % i, 
                                         template._nodes,
                                         template.address + self._intindex[i]*self._elementSize, 
                                         template.size, 
                                         access=template.access,
                                         bind=True, 
                                         displayName=(template.displayName + self._suffix) % i,
                                         description=template.description, kwattrs=template._kwattrs)
            newblk.parent = self.parent
            newblk.root = self.root
            self._index[i] = newblk
        return self._index[i]
