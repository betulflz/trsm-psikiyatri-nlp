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


def _app_with_login():
    app = Flask(__name__)

    @app.get("/")
    def index():
        return "demo"

    calls = []

    def authenticate(user, password):
        calls.append(user)
        return (user, password) == ("doktor", "dogru")

    restrict_legacy_to_loopback(app, authenticate)
    return app.test_client(), calls


def _basic(user, password):
    import base64
    return {"Authorization": "Basic " + base64.b64encode(f"{user}:{password}".encode()).decode()}


def test_funnel_requests_from_loopback_are_treated_as_remote():
    client = _app()
    for header in ("Tailscale-Funnel-Request", "X-Forwarded-For"):
        response = client.get("/", headers={header: "?1"}, environ_overrides={"REMOTE_ADDR": "127.0.0.1"})
        assert response.status_code == 403


def test_remote_login_with_mobile_account():
    client, calls = _app_with_login()
    funnel = {"Tailscale-Funnel-Request": "?1"}
    response = client.get("/", headers=funnel)
    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"].startswith("Basic")
    assert client.get("/", headers={**funnel, **_basic("doktor", "yanlis")}).status_code == 401
    assert client.get("/", headers={**funnel, **_basic("doktor", "dogru")}).status_code == 200
    assert client.get("/", headers={**funnel, **_basic("doktor", "dogru")}).status_code == 200
    assert calls == ["doktor", "doktor"]  # başarılı giriş önbellekte; şifre yeniden doğrulanmaz
    assert _get(client, "/", "192.168.1.40").status_code == 401


def test_require_login_env_closes_loopback_too(monkeypatch):
    monkeypatch.setenv("TRSM_REQUIRE_LOGIN", "1")
    client, _ = _app_with_login()
    assert _get(client, "/", "127.0.0.1").status_code == 401
    assert client.get("/", headers=_basic("doktor", "dogru")).status_code == 200


def test_repeated_wrong_passwords_lock_the_account():
    client, calls = _app_with_login()
    funnel = {"Tailscale-Funnel-Request": "?1"}
    for _ in range(5):
        assert client.get("/", headers={**funnel, **_basic("doktor", "yanlis")}).status_code == 401
    response = client.get("/", headers={**funnel, **_basic("doktor", "dogru")})
    assert response.status_code == 429
    assert len(calls) == 5  # kilitliyken şifre denenmez bile
    other_device = {"Tailscale-Funnel-Request": "?1", "X-Forwarded-For": "100.64.0.9"}
    assert client.get("/", headers={**other_device, **_basic("doktor", "dogru")}).status_code == 200
