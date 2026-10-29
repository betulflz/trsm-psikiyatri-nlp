"""Kullanıcı adı başına hatalı giriş sınırı: kaba kuvvetle şifre denemeyi yavaşlatır."""
import threading
import time

MAX_FAILURES = 5
WINDOW_SECONDS = 600


class LoginLimiter:
    def __init__(self, max_failures=MAX_FAILURES, window_seconds=WINDOW_SECONDS, clock=time.time):
        self._max = max_failures
        self._window = window_seconds
        self._clock = clock
        self._failures = {}
        self._lock = threading.Lock()

    def _recent(self, username):
        limit = self._clock() - self._window
        recent = [t for t in self._failures.get(username, []) if t > limit]
        if recent:
            self._failures[username] = recent
        else:
            self._failures.pop(username, None)
        return recent

    def locked(self, username):
        with self._lock:
            return len(self._recent(username.lower())) >= self._max

    def failed(self, username):
        with self._lock:
            self._recent(username.lower())
            self._failures.setdefault(username.lower(), []).append(self._clock())

    def succeeded(self, username):
        with self._lock:
            self._failures.pop(username.lower(), None)
