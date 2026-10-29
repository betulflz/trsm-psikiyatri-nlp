from trsm.mobile_api.login_limit import LoginLimiter


def test_lock_after_failures_and_unlock_after_window():
    now = [1000.0]
    limiter = LoginLimiter(max_failures=3, window_seconds=60, clock=lambda: now[0])
    for _ in range(3):
        assert not limiter.locked("doktor|1.2.3.4")
        limiter.failed("doktor|1.2.3.4")
    assert limiter.locked("doktor|1.2.3.4")
    assert not limiter.locked("doktor|5.6.7.8")  # başka cihaz etkilenmez
    now[0] += 61
    assert not limiter.locked("doktor|1.2.3.4")


def test_success_resets_failures():
    limiter = LoginLimiter(max_failures=2)
    limiter.failed("doktor|x")
    limiter.succeeded("doktor|x")
    limiter.failed("doktor|x")
    assert not limiter.locked("doktor|x")
