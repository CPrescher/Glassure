__author__ = 'Clemens Prescher'

import sys
import os


def _we_are_frozen():
    # All of the modules are built-in to the interpreter, e.g., by py2exe
    return hasattr(sys, "frozen")


def _module_path():
    encoding = sys.getfilesystemencoding()
    if _we_are_frozen():
        return os.path.dirname(unicode(sys.executable, encoding))
    return os.path.dirname(unicode(__file__, encoding))



from .spectrum import Spectrum

from .calc import *
from .utility import *
from .optimization import *




