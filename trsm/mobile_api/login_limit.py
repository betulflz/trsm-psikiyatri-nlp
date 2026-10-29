"""Hatalı giriş sınırı: kaba kuvvetle şifre denemeyi yavaşlatır.

İki sınır birlikte uygulanır:
- kullanıcı adı + istemci adresi: 10 dakikada 5 hata (başkası doktoru kolayca kilitleyemez),
- yalnızca kullanıcı adı: 10 dakikada 20 hata (adres değiştirerek sınırsız deneme yapılamaz).

Bilinçli tercih: ikinci sınır aşılınca hesap herkese 10 dakika kapanır. Bu, bir saldırganın
hesabı geçici olarak kilitleyebilmesi demektir; sağlık verisinde kaba kuvvete açık kalmaktan iyidir.
"""
import threading
import time

from flask import request

MAX_FAILURES = 5
MAX_FAILURES_PER_USER = 20
WINDOW_SECONDS = 600
MAX_TRACKED = 1024
LOOPBACK = {"127.0.0.1", "::1", "::ffff:127.0.0.1"}


def client_source():
    """X-Forwarded-For yalnızca istek yerel proxy'den (Tailscale) geldiyse ve son, proxy'nin eklediği değer alınır."""
    forwarded = request.headers.get("X-Forwarded-For", "")
    if forwarded and request.remote_addr in LOOPBACK:
        return forwarded.split(",")[-1].strip()[:64]
    return request.remote_addr or ""


class _Counter:
    def __init__(self, limit, window, clock):
        self.limit, self.window, self.clock = limit, window, clock
        self.failures = {}

    def recent(self, key):
        cutoff = self.clock() - self.window
        recent = [t for t in self.failures.get(key, []) if t > cutoff]
        if recent:
            self.failures[key] = recent
        else:
            self.failures.pop(key, None)
        return recent

    def _make_room(self):
        """Yalnızca kilitli olmayan kayıtları atar; kilitli kayıtlar hiçbir zaman atılmaz."""
        for old in list(self.failures):
            if len(self.recent(old)) < self.limit:
                self.failures.pop(old, None)
        return len(self.failures) < MAX_TRACKED

    def is_locked(self, key):
        if len(self.recent(key)) >= self.limit:
            return True
        # Tablo kilitli kayıtlarla doluysa izlenemeyen yeni anahtar da kilitli sayılır (güvenli taraf).
        return key not in self.failures and len(self.failures) >= MAX_TRACKED and not self._make_room()

    def add(self, key):
        if key not in self.failures and len(self.failures) >= MAX_TRACKED and not self._make_room():
            return
        self.failures.setdefault(key, []).append(self.clock())
        self.failures[key] = self.failures[key][-self.limit:]


class LoginLimiter:
    def __init__(self, max_failures=MAX_FAILURES, window_seconds=WINDOW_SECONDS, clock=time.time,
                 max_per_user=MAX_FAILURES_PER_USER):
        self._by_client = _Counter(max_failures, window_seconds, clock)
        self._by_user = _Counter(max_per_user, window_seconds, clock)
        self._lock = threading.Lock()

    @staticmethod
    def _keys(username, source):
        return f"{username[:64]}|{source}", username[:64]

    def locked(self, username, source=""):
        client, user = self._keys(username, source)
        with self._lock:
            return self._by_client.is_locked(client) or self._by_user.is_locked(user)

    def failed(self, username, source=""):
        client, user = self._keys(username, source)
        with self._lock:
            self._by_client.add(client)
            self._by_user.add(user)

    def succeeded(self, username, source=""):
        # Kullanıcı adı sayacı sıfırlanmaz; yoksa gerçek kullanıcının her girişi saldırgana yeni hak verir.
        client, _ = self._keys(username, source)
        with self._lock:
            self._by_client.failures.pop(client, None)
