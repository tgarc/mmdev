from jsvon_parse import JSVONParser
from svd_parse import SVDParser

PARSERS = { 
            'json': JSVONParser.from_devfile, 'jsvon': JSVONParser.from_devfile,
            'svd': SVDParser
          }
