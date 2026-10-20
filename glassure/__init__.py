import sys
import os

from .backend import get_backend, set_backend, use_backend

from .pattern import Pattern
from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("glassure")
except PackageNotFoundError:
    __version__ = "development"


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
