from trsm.mobile_api import login_limit
from trsm.mobile_api.login_limit import LoginLimiter


def test_lock_after_failures_and_unlock_after_window():
    now = [1000.0]
    limiter = LoginLimiter(max_failures=3, window_seconds=60, clock=lambda: now[0])
    for _ in range(3):
        assert not limiter.locked("doktor", "1.2.3.4")
        limiter.failed("doktor", "1.2.3.4")
    assert limiter.locked("doktor", "1.2.3.4")
    assert not limiter.locked("doktor", "5.6.7.8")  # başka cihaz etkilenmez
    now[0] += 61
    assert not limiter.locked("doktor", "1.2.3.4")


def test_rotating_addresses_still_hit_the_username_limit():
    limiter = LoginLimiter(max_failures=3, max_per_user=5)
    for i in range(5):
        limiter.failed("doktor", f"10.0.0.{i}")
    assert limiter.locked("doktor", "10.0.0.99")


def test_success_resets_client_failures():
    limiter = LoginLimiter(max_failures=2)
    limiter.failed("doktor", "x")
    limiter.succeeded("doktor", "x")
    limiter.failed("doktor", "x")
    assert not limiter.locked("doktor", "x")


def test_full_table_never_drops_locked_entries(monkeypatch):
    monkeypatch.setattr(login_limit, "MAX_TRACKED", 3)
    limiter = LoginLimiter(max_failures=2, max_per_user=1000)
    limiter.failed("kurban", "a")
    limiter.failed("kurban", "a")
    for i in range(10):
        limiter.failed(f"dolgu{i}", "b")
    assert limiter.locked("kurban", "a")
