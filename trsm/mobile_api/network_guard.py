"""Sunucu ağa ya da Tailscale Funnel ile internete açıldığında eski (kimliksiz) demo uç noktalarını korur."""
import hashlib
import os
import time

from flask import jsonify, request

from trsm.mobile_api.login_limit import LoginLimiter, client_source

LOOPBACK = {"127.0.0.1", "::1", "::ffff:127.0.0.1"}
MOBILE_PREFIX = "/api/m/"
# Funnel ve tailscale serve isteği 127.0.0.1'den iletir; dışarıdan geldiğini bu başlıklar gösterir.
# Başlığı taklit etmek yalnızca isteği "dışarıdan" gösterir, yetki kazandırmaz.
PROXY_HEADERS = ("Tailscale-Funnel-Request", "X-Forwarded-For", "Forwarded", "X-Real-IP")
LOGIN_CACHE_SECONDS = 120
LOGIN_CACHE_MAX = 256


def is_local_request():
    """``TRSM_REQUIRE_LOGIN=1`` iken hiçbir istek yerel sayılmaz (başlıklar eksik gelse de kapı kapalı kalır)."""
    if os.getenv("TRSM_REQUIRE_LOGIN", "").strip().lower() in {"1", "true", "evet"}:
        return False
    return request.remote_addr in LOOPBACK and not any(h in request.headers for h in PROXY_HEADERS)


def restrict_legacy_to_loopback(app, authenticate=None, limiter=None):
    """Dışarıdan gelen istekler /api/m altına serbestçe, geri kalanına yalnızca girişle ulaşır.

    ``authenticate(kullanici_adi, sifre)`` verilmezse dışarıya tamamen kapalıdır (403).
    Verilirse tarayıcı HTTP Basic ile mobil hesap bilgilerini sorar.
    """
    accepted = {}
    limiter = limiter or LoginLimiter()

    def logged_in():
        auth = request.authorization
        if auth is None or not auth.username or not auth.password:
            return None
        key = hashlib.sha256(f"{auth.username}\0{auth.password}".encode()).hexdigest()
        now = time.time()
        if accepted.get(key, 0) > now:
            return True
        source = client_source()
        if limiter.locked(auth.username, source):
            return "kilitli"
        if not authenticate(auth.username, auth.password):
            limiter.failed(auth.username, source)
            return False
        limiter.succeeded(auth.username, source)
        if len(accepted) >= LOGIN_CACHE_MAX:
            accepted.clear()
        accepted[key] = now + LOGIN_CACHE_SECONDS  # şifre özeti her istekte yeniden hesaplanmasın
        return True

    @app.before_request
    def _guard():
        if request.path.startswith(MOBILE_PREFIX) or is_local_request():
            return None
        if authenticate is None:
            return jsonify({"hata": "Bu uç nokta yalnızca bu bilgisayardan erişilebilir.", "kod": "yalniz_yerel"}), 403
        state = logged_in()
        if state is True:
            return None
        if state == "kilitli":
            return jsonify({"hata": "Çok fazla hatalı giriş. 10 dakika sonra tekrar deneyin.", "kod": "giris_kilitli"}), 429
        response = jsonify({"hata": "Giriş gerekli. Psikord kullanıcı adı ve şifrenizi girin.", "kod": "giris_gerekli"})
        response.status_code = 401
        response.headers["WWW-Authenticate"] = 'Basic realm="TRSM", charset="UTF-8"'
        return response
