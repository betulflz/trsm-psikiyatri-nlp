from trsm.mobile_api.login_limit import LoginLimiter


def test_lock_after_failures_and_unlock_after_window():
    now = [1000.0]
    limiter = LoginLimiter(max_failures=3, window_seconds=60, clock=lambda: now[0])
    for _ in range(3):
        assert not limiter.locked("Doktor")
        limiter.failed("doktor")
    assert limiter.locked("DOKTOR")
    assert not limiter.locked("hemsire")
    now[0] += 61
    assert not limiter.locked("doktor")


def test_success_resets_failures():
    limiter = LoginLimiter(max_failures=2)
    limiter.failed("doktor")
    limiter.succeeded("doktor")
    limiter.failed("doktor")
    assert not limiter.locked("doktor")
