from flask import Flask

from trsm.mobile_api.network_guard import restrict_legacy_to_loopback


def _app():
    app = Flask(__name__)

    @app.get("/")
    def index():
        return "demo"

    @app.get("/api/sorgu")
    def legacy():
        return {"ok": True}

    @app.get("/api/m/saglik")
    def mobile():
        return {"durum": "ok"}

    restrict_legacy_to_loopback(app)
    return app.test_client()


def _get(client, path, addr):
    return client.get(path, environ_overrides={"REMOTE_ADDR": addr})


def test_remote_clients_reach_only_mobile_api():
    client = _app()
    assert _get(client, "/api/m/saglik", "192.168.1.40").status_code == 200
    for path in ("/", "/api/sorgu"):
        response = _get(client, path, "192.168.1.40")
        assert response.status_code == 403
        assert response.get_json()["kod"] == "yalniz_yerel"


def test_loopback_clients_keep_full_access():
    client = _app()
    for addr in ("127.0.0.1", "::1"):
        assert _get(client, "/api/sorgu", addr).status_code == 200
        assert _get(client, "/", addr).status_code == 200
