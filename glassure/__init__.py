import sys
import os

from .pattern import Pattern

__version__ = "1.4.3.post1.dev0+5a8281b"


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
