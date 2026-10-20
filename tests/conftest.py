"""Exercise the public API with auto, or explicitly select a reference backend."""
import pytest
from glassure import use_backend


def pytest_addoption(parser):
    parser.addoption("--glassure-backend", choices=("auto", "python", "rust"), default="auto")


@pytest.fixture(autouse=True)
def glassure_backend(request):
    with use_backend(request.config.getoption("--glassure-backend")):
        yield
