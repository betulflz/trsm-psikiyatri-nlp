"""Hatalı giriş sınırı: kaba kuvvetle şifre denemeyi yavaşlatır.

Anahtar kullanıcı adı + istemci adresidir; başka biri yanlış şifre deneyerek
doktorun kendi cihazından girişini kilitleyemez.
"""
import threading
import time

from flask import request

MAX_FAILURES = 5
WINDOW_SECONDS = 600
MAX_TRACKED = 1024


def client_key(username):
    """Funnel isteği 127.0.0.1'den iletir; gerçek adres X-Forwarded-For'un son (proxy'nin eklediği) değeridir."""
    forwarded = request.headers.get("X-Forwarded-For", "")
    source = forwarded.split(",")[-1].strip() if forwarded else (request.remote_addr or "")
    return f"{username[:64]}|{source[:64]}"


class LoginLimiter:
    def __init__(self, max_failures=MAX_FAILURES, window_seconds=WINDOW_SECONDS, clock=time.time):
        self._max = max_failures
        self._window = window_seconds
        self._clock = clock
        self._failures = {}
        self._lock = threading.Lock()

    def _recent(self, key):
        limit = self._clock() - self._window
        recent = [t for t in self._failures.get(key, []) if t > limit]
        if recent:
            self._failures[key] = recent
        else:
            self._failures.pop(key, None)
        return recent

    def locked(self, key):
        with self._lock:
            return len(self._recent(key)) >= self._max

    def failed(self, key):
        with self._lock:
            if len(self._failures) >= MAX_TRACKED:
                for old in list(self._failures):
                    self._recent(old)
                if len(self._failures) >= MAX_TRACKED:
                    self._failures.clear()
            self._failures.setdefault(key, []).append(self._clock())
            self._failures[key] = self._failures[key][-self._max:]

    def succeeded(self, key):
        with self._lock:
            self._failures.pop(key, None)
