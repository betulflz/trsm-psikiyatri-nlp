"""Üç demo hesabını (doktor, hemşire, admin) idempotent olarak ekler."""
from trsm.mobile_api.users import ensure_user

DEMO_ACCOUNTS = (
    ("doktor", "Demo Doktor", "doktor"),
    ("hemsire", "Demo Hemşire", "hemsire"),
    ("admin", "Demo Admin", "admin"),
)
DEFAULT_PASSWORDS = {
    "doktor": "psikord-doktor",
    "hemsire": "psikord-hemsire",
    "admin": "psikord-admin",
}


def seed_demo_users(conn, env):
    results = {}
    for username, full_name, role in DEMO_ACCOUNTS:
        password = env.get(f"TRSM_SEED_PASSWORD_{role.upper()}") or DEFAULT_PASSWORDS[role]
        results[username] = ensure_user(conn, username, full_name, role, password)
    return results
