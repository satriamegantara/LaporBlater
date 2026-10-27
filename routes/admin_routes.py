from datetime import datetime
from flask import Blueprint, jsonify, request
from models import db_session, SystemParameter, User, FacilityType
from services.auth_service import roles_required

admin_bp = Blueprint("admin_bp", __name__, url_prefix="/api/admin")

@admin_bp.route("/parameters", methods=["GET"])
@roles_required("admin")
def get_parameters():
    """Returns system and spatial analysis parameters (F-30)."""
    db = db_session()
    params = db.query(SystemParameter).all()
    return jsonify({p.key: p.to_dict() for p in params}), 200


@admin_bp.route("/parameters", methods=["PUT"])
@roles_required("admin")
def update_parameters():
    """Updates system analysis parameters (F-30)."""
    db = db_session()
    data = request.get_json(silent=True) or {}
    
    updated = []
    for key, val in data.items():
        param = db.query(SystemParameter).filter_by(key=key).first()
        if param:
            param.value = val
            param.updated_at = datetime.utcnow()
            updated.append(key)
        else:
            new_param = SystemParameter(key=key, value=val, description="Kustom parameter admin")
            db.add(new_param)
            updated.append(key)
            
    db.commit()
    return jsonify({
        "message": f"Berhasil memperbarui {len(updated)} parameter.",
        "updated_keys": updated
    }), 200


@admin_bp.route("/users", methods=["GET"])
@roles_required("admin")
def list_users():
    """Lists officers and admin accounts (F-29)."""
    db = db_session()
    users = db.query(User).filter(User.role.in_(["pengelola", "admin"])).all()
    return jsonify({"users": [u.to_dict(include_sensitive=True) for u in users]}), 200


@admin_bp.route("/users", methods=["POST"])
@roles_required("admin")
def create_user():
    """Creates a new officer or admin account (F-29)."""
    db = db_session()
    data = request.get_json(silent=True) or request.form
    name = data.get("name")
    email = data.get("email")
    password = data.get("password")
    role = data.get("role", "pengelola")
    phone = data.get("phone")
    
    if not name or not email or not password:
        return jsonify({"error": "Nama, email, dan kata sandi wajib diisi."}), 400
        
    if db.query(User).filter_by(email=email).first():
        return jsonify({"error": f"Email '{email}' sudah terdaftar."}), 400
        
    user = User(name=name, email=email, phone=phone, role=role)
    user.set_password(password)
    db.add(user)
    db.commit()
    
    return jsonify({
        "message": f"Pengguna {name} ({role}) berhasil ditambahkan.",
        "user": user.to_dict(include_sensitive=True)
    }), 201


@admin_bp.route("/facilities", methods=["GET"])
def list_facilities():
    """Public list of facility types (F-28)."""
    db = db_session()
    facs = db.query(FacilityType).all()
    return jsonify({"facilities": [f.to_dict() for f in facs]}), 200
