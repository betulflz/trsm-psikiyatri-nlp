"""Psikord mobil uygulamasının /api/m uç noktaları."""
from contextlib import closing
from datetime import date
from functools import wraps

from flask import Blueprint, g, jsonify, request
from werkzeug.exceptions import RequestEntityTooLarge

from trsm.db import create_schema, get_connection
from trsm.mobile_api import queries
from trsm.mobile_api.ocr import MAX_IMAGE_BYTES, OcrError, read_report
from trsm.mobile_api.auth import issue_token, make_serializer, read_token
from trsm.mobile_api.users import authenticate, get_user, list_users

CLINICAL_ROLES = ("doktor", "hemsire")
DEFAULT_NOTE_LIMIT = 20
MAX_NOTE_LIMIT = 50
MAX_INT_ARG = 2**63 - 1  # PostgreSQL BIGINT sınırı; üstü 400 olarak reddedilir


def _error(status, code, message):
    return jsonify({"hata": message, "kod": code}), status


def _public(user):
    return {
        "id": user["id"],
        "kullanici_adi": user["kullanici_adi"],
        "ad_soyad": user["ad_soyad"],
        "rol": user["rol"],
        "google_bagli": user["google_sub"] is not None,
    }


def _int_arg(name, default):
    raw = request.args.get(name)
    if raw is None or raw == "":
        return default
    value = int(raw)  # ValueError çağıranda 400'e çevrilir
    if abs(value) > MAX_INT_ARG:
        raise ValueError("aralık dışı")
    return value


def create_mobile_blueprint(database_url, secret_key, *, confidence_threshold=90, today=date.today,
                            status_extra=lambda: {}):
    serializer = make_serializer(secret_key)
    with closing(get_connection(database_url)) as conn:
        create_schema(conn)
    bp = Blueprint("mobile_api", __name__, url_prefix="/api/m")

    def connect():
        return closing(get_connection(database_url))

    def requires(*roles):
        def decorator(view):
            @wraps(view)
            def wrapper(*args, **kwargs):
                header = request.headers.get("Authorization", "")
                token = header[len("Bearer "):] if header.startswith("Bearer ") else ""
                user_id = read_token(serializer, token) if token else None
                user = None
                if user_id is not None:
                    with connect() as conn:
                        user = get_user(conn, user_id)
                if user is None:
                    return _error(401, "oturum_gecersiz", "Oturum geçersiz ya da süresi doldu.")
                if roles and user["rol"] not in roles:
                    return _error(403, "yetki_yok", "Bu alan rolünüze kapalı.")
                g.mobil_kullanici = user
                return view(*args, **kwargs)
            return wrapper
        return decorator

    @bp.get("/saglik")
    def health():
        return jsonify({"durum": "ok"})

    @bp.post("/giris")
    def login():
        body = request.get_json(silent=True)
        if not isinstance(body, dict):
            body = {}
        username = str(body.get("kullanici_adi") or "").strip()
        password = str(body.get("sifre") or "")
        if not username or not password:
            return _error(400, "eksik_bilgi", "Kullanıcı adı ve şifre gerekli.")
        with connect() as conn:
            user = authenticate(conn, username, password)
        if user is None:
            return _error(401, "hatali_giris", "Kullanıcı adı ya da şifre hatalı.")
        return jsonify({"token": issue_token(serializer, user["id"]), "kullanici": _public(user)})

    @bp.get("/ben")
    @requires()
    def me():
        return jsonify(_public(g.mobil_kullanici))

    @bp.get("/ozet")
    @requires(*CLINICAL_ROLES)
    def overview():
        with connect() as conn:
            return jsonify(queries.summary(conn, confidence_threshold))

    @bp.post("/rapor/ocr")
    @requires(*CLINICAL_ROLES)
    def report_ocr():
        request.max_content_length = MAX_IMAGE_BYTES + 64 * 1024
        try:
            photo = request.files.get("foto")
            if photo is None:
                return _error(400, "foto_gerekli", "Bir rapor fotoğrafı seçin.")
            return jsonify(read_report(photo.read(MAX_IMAGE_BYTES + 1)))
        except RequestEntityTooLarge:
            return _error(413, "foto_buyuk", "Fotoğraf en fazla 12 MB olabilir.")
        except OcrError as exc:
            return _error(exc.status, "ocr_hatasi", str(exc))

    @bp.get("/hastalar")
    @requires(*CLINICAL_ROLES)
    def patients():
        with connect() as conn:
            return jsonify({"hastalar": queries.list_patients(conn, today())})

    @bp.get("/hastalar/<int:patient_id>")
    @requires(*CLINICAL_ROLES)
    def patient(patient_id):
        if patient_id > MAX_INT_ARG:
            return _error(404, "dosya_yok", "Dosya bulunamadı.")
        with connect() as conn:
            detail = queries.patient_detail(conn, patient_id, today(), confidence_threshold)
        if detail is None:
            return _error(404, "dosya_yok", "Dosya bulunamadı.")
        return jsonify(detail)

    @bp.get("/hastalar/<int:patient_id>/notlar")
    @requires(*CLINICAL_ROLES)
    def notes(patient_id):
        if patient_id > MAX_INT_ARG:
            return _error(404, "dosya_yok", "Dosya bulunamadı.")
        try:
            before_id = _int_arg("once", None)
            limit = min(MAX_NOTE_LIMIT, max(1, _int_arg("limit", DEFAULT_NOTE_LIMIT)))
        except ValueError:
            return _error(400, "gecersiz_parametre", "Sayfalama parametreleri sayı olmalı.")
        with connect() as conn:
            if conn.execute("SELECT 1 FROM hasta WHERE id = %s", (patient_id,)).fetchone() is None:
                return _error(404, "dosya_yok", "Dosya bulunamadı.")
            try:
                page = queries.patient_notes(conn, patient_id, confidence_threshold, before_id, limit)
            except ValueError:
                return _error(400, "gecersiz_imlec", "Sayfalama imleci bu dosyaya ait değil.")
        return jsonify(page)

    @bp.get("/sistem")
    @requires("admin")
    def system():
        with connect() as conn:
            status = queries.system_status(conn)
        return jsonify({**status, **status_extra()})

    @bp.get("/kullanicilar")
    @requires("admin")
    def users():
        with connect() as conn:
            return jsonify({"kullanicilar": [_public(u) for u in list_users(conn)]})

    return bp
