"""Selection of the numerical backend, scoped to the current execution context.

Auto falls back only when the bundled native extension cannot be loaded. Once
a backend is selected, adapter/import/calculation errors propagate unchanged.
"""
from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from functools import wraps
from importlib import import_module
from inspect import Parameter, signature
from typing import Literal

Backend = Literal["auto", "python", "rust"]
_preference: ContextVar[Backend] = ContextVar("glassure_backend", default="auto")

__all__ = ["get_backend", "set_backend", "use_backend"]


def _validate(backend: Backend) -> Backend:
    if backend not in ("auto", "python", "rust"):
        raise ValueError("backend must be 'auto', 'python', or 'rust'")
    return backend


def _native_status():
    try:
        native = import_module("glassure._glassure_numpy")
    except (ImportError, OSError) as error:
        return False, error
    if not all(hasattr(native, name) for name in ("Engine", "run")):
        return False, ImportError("Installed native extension lacks the Glassure backend API")
    return True, None


def _resolve(backend: Backend) -> Literal["python", "rust"]:
    backend = _validate(backend)
    if backend == "python":
        return "python"
    available, error = _native_status()
    if available:
        return "rust"
    if backend == "auto":
        return "python"
    raise ImportError(
        "Rust backend is unavailable. Reinstall the glassure wheel, or install "
        "glassure[legacy] and select backend='python'."
    ) from error


def get_backend() -> Literal["python", "rust"]:
    """Return the effective backend for this context (resolves the auto default)."""
    return _resolve(_preference.get())


def set_backend(backend: Backend) -> None:
    """Set the default for this context; 'auto' prefers an importable Rust engine.

    Use use_backend for a temporary choice. Independent threads and async tasks
    have context-local settings, so one calculation cannot change another's mode.
    """
    _validate(backend)
    if backend == "rust":
        _resolve(backend)
    _preference.set(backend)


@contextmanager
def use_backend(backend: Backend):
    """Temporarily select a backend, restoring the previous mode even on error."""
    _validate(backend)
    if backend == "rust":
        _resolve(backend)
    token = _preference.set(backend)
    try:
        yield
    finally:
        _preference.reset(token)


def dispatch(function=None, *, name=None, native=None):
    """Add a keyword-only backend override without changing positional arguments.

    Pin the resolved selection for nested calls: a forced Python fit must never
    compare a Python optimizer against a Rust inner calculation inadvertently.
    """
    if function is None:
        return lambda function: dispatch(function, name=name, native=native)
    rust_name = name or function.__name__

    @wraps(function)
    def selected(*args, backend=None, **kwargs):
        mode = _resolve(_preference.get() if backend is None else backend)
        token = _preference.set(mode)
        try:
            if mode == "rust":
                implementation = native or getattr(import_module("glassure.rust"), rust_name)
            else:
                implementation = function
            return implementation(*args, **kwargs)
        finally:
            _preference.reset(token)

    original = signature(function)
    parameters = list(original.parameters.values())
    index = next(
        (i for i, p in enumerate(parameters) if p.kind == Parameter.VAR_KEYWORD),
        len(parameters),
    )
    parameters.insert(
        index,
        Parameter("backend", kind=Parameter.KEYWORD_ONLY, default=None, annotation=Backend | None),
    )
    selected.__signature__ = original.replace(parameters=parameters)
    return selected
