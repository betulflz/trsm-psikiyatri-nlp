"""Sunucu yerel ağa açıldığında eski (kimliksiz) demo uç noktalarını korur."""
from flask import jsonify, request

LOOPBACK = {"127.0.0.1", "::1", "::ffff:127.0.0.1"}
MOBILE_PREFIX = "/api/m/"


def restrict_legacy_to_loopback(app):
    """Ağdan gelen istekler yalnızca /api/m altına ulaşabilir; geri kalanı sadece bu makineye açık."""

    @app.before_request
    def _guard():
        if request.remote_addr in LOOPBACK or request.path.startswith(MOBILE_PREFIX):
            return None
        return jsonify({"hata": "Bu uç nokta yalnızca bu bilgisayardan erişilebilir.", "kod": "yalniz_yerel"}), 403
