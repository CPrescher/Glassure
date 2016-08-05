import sys
import os


def _we_are_frozen():
    # All of the modules are built-in to the interpreter, e.g., by py2exe
    return hasattr(sys, "frozen")


def _module_path():
    return os.path.dirname(__file__)



from .pattern import Pattern

from .calc import *
from .utility import *
from .optimization import *
from .soller_correction import *

from ._version import get_versions
__version__ = get_versions()['version']
del get_versions
