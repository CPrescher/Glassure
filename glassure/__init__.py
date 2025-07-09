import sys
import os

from .pattern import Pattern

__version__ = "2.0.0"


def _module_path():
    return os.path.dirname(__file__)


from .utility import *
from .optimization import *
from .soller_correction import *
from .normalization import *
from .transform import *


def _we_are_frozen():
    # All the modules are built-in to the interpreter, e.g., by py2exe
    return hasattr(sys, "frozen")