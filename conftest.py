"""Keep shared throttle state isolated between independent regression tests."""
import pytest
from django.core.cache import cache


@pytest.fixture(autouse=True)
def isolate_test_cache():
    cache.clear()
    yield
    cache.clear()
