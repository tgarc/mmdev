import logging as _logging
_logging.basicConfig()

import utils

import blocks
import components
import device

import datalink
import transport
import devicelink
import cables

import parsers
import dumpers


import os as _os
def from_devfile(devfile, file_format=None, raiseErr=True):
    """
    Parse a device file using the given file format. If file format is not
    given, file extension will be used.

    Supported Formats:
        + 'json' : JSON
        + 'svd'  : CMSIS-SVD
    """

    if file_format is None:
        file_format = _os.path.splitext(devfile)[1][1:]
    try:
        parsercls = parsers.PARSERS[file_format]
    except KeyError:
        raise KeyError("File extension '%s' not recognized" % file_format)

    return parsercls(devfile, raiseErr=raiseErr)
