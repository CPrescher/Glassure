import sys
import os

from .pattern import Pattern


def _module_path():
    return os.path.dirname(__file__)


from .calc import *
from .utility import *
from .optimization import *
from .soller_correction import *


def _we_are_frozen():
    # All the modules are built-in to the interpreter, e.g., by py2exe
    return hasattr(sys, "frozen")
