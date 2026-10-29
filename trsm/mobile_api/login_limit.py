"""Hatalı giriş sınırı: kaba kuvvetle şifre denemeyi yavaşlatır.

İki sınır birlikte uygulanır:
- kullanıcı adı + istemci adresi: 10 dakikada 5 hata (başkası doktoru kolayca kilitleyemez),
- yalnızca kullanıcı adı: 10 dakikada 20 hata (adres değiştirerek sınırsız deneme yapılamaz).

Bilinçli tercih: ikinci sınır aşılınca hesap herkese 10 dakika kapanır. Bu, bir saldırganın
hesabı geçici olarak kilitleyebilmesi demektir; sağlık verisinde kaba kuvvete açık kalmaktan iyidir.
"""
import hashlib
import secrets
import threading
import time

from flask import request

MAX_FAILURES = 5
MAX_FAILURES_PER_USER = 20
WINDOW_SECONDS = 600
BUCKETS = 4096
LOOPBACK = {"127.0.0.1", "::1", "::ffff:127.0.0.1"}


def client_source():
    """X-Forwarded-For yalnızca istek yerel proxy'den (Tailscale) geldiyse ve son, proxy'nin eklediği değer alınır."""
    forwarded = request.headers.get("X-Forwarded-For", "")
    if forwarded and request.remote_addr in LOOPBACK:
        return forwarded.split(",")[-1].strip()[:64]
    return request.remote_addr or ""


class _Counter:
    """Sabit sayıda kovalı sayaç: her anahtar bir kovaya düşer, "izlenmeyen anahtar" yoktur.

    Bellek sabittir ve tablo doldurularak sınır atlatılamaz. Kova, süreç başına rastgele
    anahtarla hesaplanır; saldırgan kurbanla aynı kovaya düşen anahtar seçemez. Nadir
    çakışma yalnızca fazladan kilit üretir, hiçbir zaman eksik saymaz.
    """

    def __init__(self, limit, window, clock, buckets=BUCKETS):
        self.limit, self.window, self.clock = limit, window, clock
        self.buckets = [[] for _ in range(buckets)]
        self._salt = secrets.token_bytes(16)

    def _slot(self, key):
        digest = hashlib.blake2b(key.encode(), key=self._salt, digest_size=8).digest()
        return self.buckets[int.from_bytes(digest, "big") % len(self.buckets)]

    def _recent(self, slot):
        cutoff = self.clock() - self.window
        slot[:] = [t for t in slot if t > cutoff]
        return slot

    def is_locked(self, key):
        return len(self._recent(self._slot(key))) >= self.limit

    def add(self, key):
        slot = self._recent(self._slot(key))
        slot.append(self.clock())
        del slot[:-self.limit]

    def clear(self, key):
        self._slot(key).clear()


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
            self._by_client.clear(client)
