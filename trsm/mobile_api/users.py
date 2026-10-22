"""Mobil uygulama kullanıcıları: oluşturma, şifre doğrulama, okuma."""
from datetime import datetime, timezone

from werkzeug.security import check_password_hash, generate_password_hash

ROLLER = ("admin", "doktor", "hemsire")
_KEYS = ("id", "kullanici_adi", "ad_soyad", "rol", "sifre_hash", "google_sub", "google_eposta")
_SELECT = "SELECT " + ", ".join(_KEYS) + " FROM kullanici"


def _to_user(row):
    return dict(zip(_KEYS, row)) if row is not None else None


def ensure_user(conn, kullanici_adi, ad_soyad, rol, sifre):
    """Kullanıcı yoksa oluşturur; varsa hiçbir alanına (şifre dahil) dokunmaz."""
    if rol not in ROLLER:
        raise ValueError(f"Bilinmeyen rol: {rol}")
    if conn.execute("SELECT 1 FROM kullanici WHERE kullanici_adi = %s", (kullanici_adi,)).fetchone():
        return False
    conn.execute(
        """INSERT INTO kullanici (kullanici_adi, ad_soyad, rol, sifre_hash, olusturma_zamani)
           VALUES (%s, %s, %s, %s, %s)""",
        (
            kullanici_adi,
            ad_soyad,
            rol,
            generate_password_hash(sifre),
            datetime.now(timezone.utc).isoformat(timespec="seconds"),
        ),
    )
    conn.commit()
    return True


def authenticate(conn, kullanici_adi, sifre):
    user = _to_user(conn.execute(_SELECT + " WHERE kullanici_adi = %s", (kullanici_adi,)).fetchone())
    if user is None or not check_password_hash(user["sifre_hash"], sifre):
        return None
    return user


def get_user(conn, user_id):
    return _to_user(conn.execute(_SELECT + " WHERE id = %s", (user_id,)).fetchone())


def list_users(conn):
    return [_to_user(row) for row in conn.execute(_SELECT + " ORDER BY id")]
