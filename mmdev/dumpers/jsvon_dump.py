from mmdev.dumpers.devicedumper import DeviceDumper
import json


class JSVONDumper(DeviceDumper):
    @classmethod
    def dump_device(cls, deviceblock):
        return deviceblock.to_json(recursive=True, indent=4)