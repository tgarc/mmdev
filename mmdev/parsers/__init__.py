from pycfg_parse import PYCFGParser
from jcfg_parse import JCFGParser
from svd_parse import SVDParser

PARSERS = { 
            'pycfg': PYCFGParser, 
            'json': JCFGParser, 
            'svd': SVDParser,
          }
