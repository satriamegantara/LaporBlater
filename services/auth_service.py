import datetime
from functools import wraps
from flask import request, jsonify, g, session
import jwt

from config import Config
from models import db_session, User

def generate_token(user: User) -> str:
    """Generates a JWT token for the authenticated user."""
    payload = {
        "user_id": user.id,
        "name": user.name,
        "role": user.role,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=Config.JWT_EXPIRATION_HOURS)
    }
    return jwt.encode(payload, Config.JWT_SECRET_KEY, algorithm="HS256")


def decode_token(token: str) -> dict:
    """Decodes and validates a JWT token."""
    try:
        payload = jwt.decode(token, Config.JWT_SECRET_KEY, algorithms=["HS256"])
        return payload
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None


def get_current_user():
    """Retrieves current user from JWT Authorization header or Flask session."""
    # 1. Check Flask session first (for browser web pages)
    user_id = session.get("user_id")
    if user_id:
        db = db_session()
        return db.query(User).filter_by(id=user_id).first()

    # 2. Check Authorization Bearer header
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ", 1)[1]
        payload = decode_token(token)
        if payload:
            db = db_session()
            return db.query(User).filter_by(id=payload.get("user_id")).first()
            
    return None


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_current_user()
        if not user:
            return jsonify({"error": "Autentikasi diperlukan. Silakan login."}), 401
        g.current_user = user
        return f(*args, **kwargs)
    return decorated_function


def roles_required(*allowed_roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user = get_current_user()
            if not user:
                return jsonify({"error": "Autentikasi diperlukan. Silakan login."}), 401
            if user.role not in allowed_roles:
                return jsonify({"error": "Akses ditolak. Anda tidak memiliki izin untuk tindakan ini."}), 403
            g.current_user = user
            return f(*args, **kwargs)
        return decorated_function
    return decorator
