"""Dependencies used only by the Python reference and legacy object interfaces."""

from importlib import import_module


def import_legacy(module):
    """Load an optional dependency only when its interface is requested."""
    try:
        return import_module(module)
    except ModuleNotFoundError as error:
        raise ImportError(
            f"{module} is needed for this legacy interface. "
            "Install it with: python -m pip install 'glassure[legacy]'"
        ) from error
