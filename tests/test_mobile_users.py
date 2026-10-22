import pytest

from trsm.db import create_schema
from tests.pg import fresh_connection
from trsm.mobile_api.seed import DEFAULT_PASSWORDS, seed_demo_users
from trsm.mobile_api.users import authenticate, ensure_user, get_user, list_users


def _conn():
    conn = fresh_connection()
    create_schema(conn)
    return conn


def test_ensure_user_creates_once_and_never_overwrites_password():
    conn = _conn()
    assert ensure_user(conn, "doktor", "Demo Doktor", "doktor", "ilk") is True
    assert ensure_user(conn, "doktor", "Başka Ad", "doktor", "ikinci") is False
    assert authenticate(conn, "doktor", "ilk")["ad_soyad"] == "Demo Doktor"
    assert authenticate(conn, "doktor", "ikinci") is None
    assert len(list_users(conn)) == 1


def test_password_is_stored_hashed():
    conn = _conn()
    ensure_user(conn, "hemsire", "Demo Hemşire", "hemsire", "gizli")
    stored = conn.execute("SELECT sifre_hash FROM kullanici").fetchone()[0]
    assert stored != "gizli" and len(stored) > 20


def test_authenticate_rejects_unknown_user_and_wrong_password():
    conn = _conn()
    ensure_user(conn, "admin", "Demo Admin", "admin", "dogru")
    assert authenticate(conn, "yok", "dogru") is None
    assert authenticate(conn, "admin", "yanlis") is None
    user = authenticate(conn, "admin", "dogru")
    assert user["rol"] == "admin"
    assert get_user(conn, user["id"])["kullanici_adi"] == "admin"
    assert get_user(conn, 999) is None


def test_unknown_role_is_rejected():
    with pytest.raises(ValueError):
        ensure_user(_conn(), "x", "X", "sekreter", "s")


def test_seed_is_idempotent_and_uses_env_passwords():
    conn = _conn()
    first = seed_demo_users(conn, {"TRSM_SEED_PASSWORD_DOKTOR": "ozel"})
    second = seed_demo_users(conn, {})
    assert first == {"doktor": True, "hemsire": True, "admin": True}
    assert second == {"doktor": False, "hemsire": False, "admin": False}
    assert authenticate(conn, "doktor", "ozel") is not None
    assert authenticate(conn, "hemsire", DEFAULT_PASSWORDS["hemsire"]) is not None
    assert sorted(u["rol"] for u in list_users(conn)) == ["admin", "doktor", "hemsire"]


from trsm.mobile_api.auth import issue_token, load_or_create_secret, make_serializer, read_token  # noqa: E402


def test_token_roundtrip_and_rejections():
    serializer = make_serializer("anahtar")
    token = issue_token(serializer, 7)
    assert read_token(serializer, token) == 7
    assert read_token(make_serializer("baska"), token) is None
    assert read_token(serializer, "bozuk.token") is None
    assert read_token(serializer, token, max_age=-1) is None  # süresi dolmuş


def test_secret_prefers_env_then_file_then_creates(tmp_path):
    path = tmp_path / "data" / "mobile_secret.key"
    assert load_or_create_secret(path, {"TRSM_SECRET_KEY": "env"}) == "env"
    assert not path.exists()
    created = load_or_create_secret(path, {})
    assert path.exists() and len(created) == 64
    assert load_or_create_secret(path, {}) == created


import os  # noqa: E402
import stat  # noqa: E402


def test_secret_file_is_owner_only(tmp_path):
    path = tmp_path / "data" / "mobile_secret.key"
    load_or_create_secret(path, {})
    assert stat.S_IMODE(os.stat(path).st_mode) == 0o600


def test_existing_world_readable_secret_is_tightened(tmp_path):
    path = tmp_path / "mobile_secret.key"
    path.write_text("eski-anahtar", encoding="utf-8")
    os.chmod(path, 0o644)
    assert load_or_create_secret(path, {}) == "eski-anahtar"
    assert stat.S_IMODE(os.stat(path).st_mode) == 0o600
