"""İmzalı, süreli oturum token'ları ve imza anahtarının yüklenmesi."""
import os
import secrets
from pathlib import Path

from itsdangerous import BadSignature, URLSafeTimedSerializer

TOKEN_MAX_AGE_SECONDS = 12 * 60 * 60


def make_serializer(secret_key):
    return URLSafeTimedSerializer(secret_key, salt="psikord-mobil-oturum")


def issue_token(serializer, user_id):
    return serializer.dumps({"uid": int(user_id)})


def read_token(serializer, token, max_age=TOKEN_MAX_AGE_SECONDS):
    """Geçerli token için kullanıcı id'si; bozuk/süresi dolmuşsa None."""
    try:
        payload = serializer.loads(token, max_age=max_age)
    except BadSignature:  # SignatureExpired da BadSignature alt sınıfıdır
        return None
    user_id = payload.get("uid") if isinstance(payload, dict) else None
    return user_id if isinstance(user_id, int) else None


def load_or_create_secret(path, env):
    if env.get("TRSM_SECRET_KEY"):
        return env["TRSM_SECRET_KEY"]
    path = Path(path)
    if path.exists():
        if os.stat(path).st_mode & 0o077:  # başkaları okuyabiliyorsa sıkılaştır
            os.chmod(path, 0o600)
        return path.read_text(encoding="utf-8").strip()
    path.parent.mkdir(parents=True, exist_ok=True)
    secret = secrets.token_hex(32)
    # Anahtar yalnızca sahibi okuyabilsin (başka yerel kullanıcılar token üretemesin).
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(secret)
    return secret
