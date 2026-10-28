from flask import Blueprint, request, jsonify, session, redirect, url_for
from models import db_session, User
from services.auth_service import generate_token, get_current_user, login_required

auth_bp = Blueprint("auth_bp", __name__, url_prefix="/api/auth")

@auth_bp.route("/login", methods=["POST"])
def login():
    """
    Login endpoint for pengelola and admin.
    Returns JWT token and user info.
    """
    data = request.get_json(silent=True) or request.form
    email = data.get("email", "").strip()
    password = data.get("password", "")
    
    if not email or not password:
        return jsonify({"error": "Email dan password wajib diisi."}), 400
        
    db = db_session()
    user = db.query(User).filter_by(email=email).first()
    
    if not user or not user.check_password(password):
        return jsonify({"error": "Email atau kata sandi salah."}), 401
        
    # Store in session as well for browser seamless session
    session["user_id"] = user.id
    session["user_role"] = user.role
    session["user_name"] = user.name
    
    token = generate_token(user)
    return jsonify({
        "message": "Login berhasil.",
        "token": token,
        "user": user.to_dict(include_sensitive=True)
    }), 200


@auth_bp.route("/logout", methods=["POST", "GET"])
def logout():
    session.clear()
    # Redirect to login page if called via browser link (GET) or text/html request
    if request.method == "GET" or "application/json" not in request.headers.get("Accept", ""):
        return redirect(url_for("web_bp.login_page"))
    return jsonify({"message": "Berhasil logout."}), 200


@auth_bp.route("/me", methods=["GET"])
@login_required
def get_me():
    user = get_current_user()
    return jsonify({"user": user.to_dict(include_sensitive=True)}), 200
