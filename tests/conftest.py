import pytest

from tests.pg import drop_test_schemas


@pytest.fixture(scope="session", autouse=True)
def _cleanup_test_schemas():
    yield
    try:
        drop_test_schemas()
    except Exception:
        # PostgreSQL'e hiç bağlanamayan oturumda temizlenecek bir şey yoktur.
        pass
