from datetime import datetime
from flask import Blueprint, request, jsonify, g
from config import Config
from models import (
    db_session, Report, Photo, AIPrediction, ReportStatusHistory, 
    FacilityType, ReportStatus, User, SystemParameter
)
from services.spatial_service import validate_location, detect_duplicates
from services.photo_service import process_and_save_photo, allowed_file
from services.ai_service import predict, get_category_suggestion, suggest_severity
from services.auth_service import login_required, roles_required, get_current_user

report_bp = Blueprint("report_bp", __name__, url_prefix="/api")

# Valid status transitions (PRD 7.2, 8.3 F-12)
ALLOWED_STATUS_TRANSITIONS = {
    "MENUNGGU_VERIFIKASI": ["DIVERIFIKASI"],
    "DIVERIFIKASI": ["DIPROSES"],
    "DIPROSES": ["SELESAI"],
    "SELESAI": []  # Final state
}


@report_bp.route("/reports/validate-location", methods=["POST"])
def check_location():
    """
    Validates if coordinates are within Desa Blater boundary (F-03).
    Returns 200 if valid, 422 if outside boundary or invalid.
    """
    data = request.get_json(silent=True) or request.form
    lat = data.get("lat")
    lng = data.get("lng")
    
    is_valid, message = validate_location(lat, lng)
    if not is_valid:
        return jsonify({"is_valid": False, "message": message}), 422
        
    return jsonify({"is_valid": True, "message": message}), 200


@report_bp.route("/photos/upload", methods=["POST"])
def upload_photo():
    """
    Uploads a photo, strips EXIF for public copy, blurs faces & plates,
    extracts coordinates from EXIF, and runs AI prediction for instant feedback (F-04, F-07, F-08).
    """
    if "photo" not in request.files:
        return jsonify({"error": "Berkas foto wajib diunggah."}), 400
        
    file = request.files["photo"]
    if file.filename == "":
        return jsonify({"error": "Tidak ada berkas yang dipilih."}), 400
        
    if not allowed_file(file.filename):
        return jsonify({"error": "Format berkas tidak didukung. Gunakan JPG, PNG, atau WEBP."}), 415
        
    # Check file size (5MB limit)
    file.seek(0, 2)
    size = file.tell()
    file.seek(0)
    if size > Config.MAX_CONTENT_LENGTH:
        return jsonify({"error": "Ukuran foto melebihi batas 5 MB."}), 413
        
    # Process photo
    processed = process_and_save_photo(file)
    original_path = str(Config.UPLOAD_FOLDER_ORIGINAL / processed["file_name"])
    
    # Run AI prediction
    ai_result = predict(original_path)
    
    # Check category suggestion if user pre-selected facility
    user_fac = request.form.get("facility_type")
    suggestion = None
    if user_fac:
        suggestion = get_category_suggestion(user_fac, ai_result["predicted_class"], ai_result["confidence"])
        
    return jsonify({
        "photo_id": processed["file_name"],
        "public_name": processed["public_name"],
        "public_url": f"/uploads/photos/public/{processed['public_name']}",
        "width": processed["width"],
        "height": processed["height"],
        "exif": processed["exif"],
        "ai_prediction": ai_result,
        "category_suggestion": suggestion
    }), 201


@report_bp.route("/reports", methods=["POST"])
def create_report():
    """
    Creates a new report according to PRD Section 8.1 & 12.
    Validates location against Desa Blater (422), detects duplicates (409),
    and triggers AI classification.
    """
    db = db_session()
    
    # Handle both JSON and multipart form data
    if request.is_json:
        data = request.get_json()
        loc = data.get("location", {})
        lat = loc.get("lat")
        lng = loc.get("lng")
        fac_type_input = data.get("facility_type")
        description = data.get("description", "").strip()
        location_source = data.get("location_source", "manual_map")
        source_type = data.get("source_type", "warga")
        photo_filename = data.get("photo_id")
        force_submit = data.get("force_submit", False)
        reporter_name = data.get("reporter_name")
        reporter_phone = data.get("reporter_phone")
        reporter_email = data.get("reporter_email")
    else:
        data = request.form
        lat = data.get("lat")
        lng = data.get("lng")
        fac_type_input = data.get("facility_type")
        description = data.get("description", "").strip()
        location_source = data.get("location_source", "manual_map")
        source_type = data.get("source_type", "warga")
        photo_filename = data.get("photo_id")
        force_submit = data.get("force_submit", "").lower() in ["true", "1", "yes"]
        reporter_name = data.get("reporter_name")
        reporter_phone = data.get("reporter_phone")
        reporter_email = data.get("reporter_email")

    # If photo file was directly attached in multipart
    file_uploaded = None
    if "photo" in request.files and request.files["photo"].filename != "":
        file = request.files["photo"]
        if not allowed_file(file.filename):
            return jsonify({"error": "Format berkas foto tidak didukung."}), 415
        file.seek(0, 2)
        if file.tell() > Config.MAX_CONTENT_LENGTH:
            return jsonify({"error": "Ukuran foto melebihi batas 5 MB."}), 413
        file.seek(0)
        file_uploaded = process_and_save_photo(file)
        photo_filename = file_uploaded["file_name"]

    # 1. Validation: Required fields
    if not fac_type_input:
        return jsonify({"error": "Jenis fasilitas wajib dipilih."}), 400
    if not description:
        return jsonify({"error": "Deskripsi kerusakan wajib diisi."}), 400
    if len(description) > 500:
        return jsonify({"error": "Deskripsi maksimal 500 karakter."}), 400
    if lat is None or lng is None:
        return jsonify({"error": "Titik lokasi wajib ditentukan."}), 400
    if not photo_filename and not file_uploaded:
        return jsonify({"error": "Minimal satu foto wajib diunggah."}), 400

    # 2. Validation: Location inside Blater boundary (F-03)
    is_valid, loc_msg = validate_location(lat, lng)
    if not is_valid:
        return jsonify({
            "error": "Lokasi berada di luar wilayah administratif Desa Blater.",
            "detail": loc_msg
        }), 422

    # 3. Resolve facility type
    filters = [
        FacilityType.code == str(fac_type_input).upper(),
        FacilityType.name.ilike(f"%{fac_type_input}%")
    ]
    if str(fac_type_input).isdigit():
        filters.append(FacilityType.id == int(fac_type_input))
        
    from sqlalchemy import or_
    fac_type = db.query(FacilityType).filter(or_(*filters)).first()
    if not fac_type:
        return jsonify({"error": f"Jenis fasilitas '{fac_type_input}' tidak valid."}), 400

    # 4. Duplicate report detection in 6 meters (F-05)
    duplicates = detect_duplicates(db, float(lat), float(lng), fac_type.id)
    if duplicates and not force_submit:
        return jsonify({
            "warning": "Laporan serupa terdeteksi di sekitar lokasi ini dalam radius 6 meter.",
            "code": "DUPLICATE_SUSPECT",
            "duplicate_reports": duplicates,
            "message": "Sudah ada laporan kerusakan untuk fasilitas ini di titik yang sama. Anda dapat memilih 'Tetap Kirim' jika merupakan kerusakan baru."
        }), 409

    # 5. Handle reporter user
    user = get_current_user()
    reporter_id = user.id if user else None
    
    # If anonymous user provided contact info, optionally store or link
    if not reporter_id and (reporter_name or reporter_phone or reporter_email):
        # Create non-login citizen user record
        citizen = User(
            name=reporter_name or "Warga Blater",
            email=reporter_email if reporter_email else None,
            phone=reporter_phone if reporter_phone else None,
            role="warga"
        )
        db.add(citizen)
        db.flush()
        reporter_id = citizen.id

    # 6. Default status: MENUNGGU_VERIFIKASI
    initial_status = db.query(ReportStatus).filter_by(code="MENUNGGU_VERIFIKASI").first()
    if not initial_status:
        initial_status = db.query(ReportStatus).order_by(ReportStatus.sort_order.asc()).first()

    # 7. Create Report
    report = Report(
        reporter_id=reporter_id,
        facility_type_id=fac_type.id,
        status_id=initial_status.id,
        description=description,
        latitude=float(lat),
        longitude=float(lng),
        location_source=location_source,
        source_type=source_type,
        is_duplicate_of=duplicates[0]["report_id"] if duplicates and force_submit else None
    )
    db.add(report)
    db.flush()

    # 8. Save Photo Record & Run AI Prediction
    orig_path = Config.UPLOAD_FOLDER_ORIGINAL / photo_filename
    pub_name = file_uploaded["public_name"] if file_uploaded else f"pub_{photo_filename.replace('orig_', '')}"
    if not pub_name.endswith(".jpg"):
        pub_name = pub_name.rsplit(".", 1)[0] + ".jpg"

    photo = Photo(
        report_id=report.id,
        file_path=photo_filename,
        public_path=pub_name,
        exif_lat=file_uploaded["exif"]["lat"] if file_uploaded else None,
        exif_lng=file_uploaded["exif"]["lng"] if file_uploaded else None,
        exif_taken_at=file_uploaded["exif"]["taken_at"] if file_uploaded else None,
        width=file_uploaded["width"] if file_uploaded else None,
        height=file_uploaded["height"] if file_uploaded else None
    )
    db.add(photo)
    db.flush()

    # AI Classification (F-07)
    ai_result = predict(str(orig_path))
    prediction = AIPrediction(
        photo_id=photo.id,
        predicted_class=ai_result["predicted_class"],
        confidence=ai_result["confidence"],
        model_name=ai_result["model_name"],
        model_version=ai_result["model_version"]
    )
    db.add(prediction)

    # Link AI category if confidence >= 0.85 (F-08)
    ai_fac_code = ai_result["predicted_class"].replace("_RUSAK", "").replace("_TERSUMBAT", "")
    ai_fac = db.query(FacilityType).filter_by(code=ai_fac_code).first()
    if ai_fac:
        report.ai_category_id = ai_fac.id

    # Severity suggestion from AI (PRD 8.3 F-13)
    suggested_sev = suggest_severity(ai_result["predicted_class"], ai_result["confidence"])
    report.severity = suggested_sev

    # 9. Record initial status history
    history = ReportStatusHistory(
        report_id=report.id,
        from_status_id=None,
        to_status_id=initial_status.id,
        changed_by=reporter_id,
        note="Laporan berhasil dibuat oleh warga/pelapor."
    )
    db.add(history)
    db.commit()

    return jsonify({
        "message": "Laporan berhasil dikirim dan tersimpan.",
        "report_id": report.id,
        "status": initial_status.name,
        "tracking_url": f"/laporan/{report.id}",
        "ai_prediction": ai_result,
        "severity_suggestion": suggested_sev,
        "report": report.to_dict()
    }), 201


@report_bp.route("/reports/<int:report_id>/status", methods=["GET"])
def get_report_status_public(report_id: int):
    """
    Public tracking endpoint for citizens (F-26).
    Returns status and timeline without personal identifiers or EXIF.
    """
    db = db_session()
    report = db.query(Report).filter_by(id=report_id).first()
    if not report:
        return jsonify({"error": f"Laporan dengan ID {report_id} tidak ditemukan."}), 404
        
    primary_photo = report.photos[0] if report.photos else None
    
    return jsonify({
        "id": report.id,
        "facility_type": report.facility_type.name if report.facility_type else None,
        "status": report.status.name if report.status else None,
        "status_code": report.status.code if report.status else None,
        "severity": report.severity,
        "description": report.description,
        "created_at": report.created_at.isoformat(),
        "updated_at": report.updated_at.isoformat(),
        "public_photo_url": f"/uploads/photos/public/{primary_photo.public_path}" if primary_photo else None,
        "timeline": [
            {
                "status": h.to_status.name if h.to_status else None,
                "note": h.note,
                "date": h.changed_at.isoformat()
            } for h in report.status_history
        ]
    }), 200


@report_bp.route("/reports", methods=["GET"])
@roles_required("pengelola", "admin")
def list_reports():
    """
    Listing reports for officers/admin with pagination, sorting, and filters (F-11).
    """
    db = db_session()
    query = db.query(Report)
    
    # Filters
    fac = request.args.get("facility_type")
    if fac:
        query = query.join(FacilityType, Report.facility_type_id == FacilityType.id).filter(FacilityType.code == fac.upper())
        
    status = request.args.get("status")
    if status:
        query = query.join(ReportStatus, Report.status_id == ReportStatus.id).filter(ReportStatus.code == status.upper())
        
    severity = request.args.get("severity")
    if severity:
        query = query.filter(Report.severity == severity.lower())
        
    source_type = request.args.get("source_type")
    if source_type:
        query = query.filter(Report.source_type == source_type)
        
    search = request.args.get("q")
    if search:
        query = query.filter(Report.description.ilike(f"%{search}%"))
        
    # Ordering
    sort_by = request.args.get("sort_by", "created_at")
    order = request.args.get("order", "desc")
    if hasattr(Report, sort_by):
        col = getattr(Report, sort_by)
        query = query.order_by(col.desc() if order == "desc" else col.asc())
    else:
        query = query.order_by(Report.created_at.desc())
        
    # Pagination
    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 20))
    total = query.count()
    reports = query.offset((page - 1) * per_page).limit(per_page).all()
    
    return jsonify({
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": (total + per_page - 1) // per_page,
        "reports": [r.to_dict(is_admin_or_officer=True) for r in reports]
    }), 200


@report_bp.route("/reports/<int:report_id>", methods=["GET"])
@roles_required("pengelola", "admin")
def get_report_detail(report_id: int):
    """
    Detailed report view for officers/admin including predictions and original photo (F-14).
    """
    db = db_session()
    report = db.query(Report).filter_by(id=report_id).first()
    if not report:
        return jsonify({"error": "Laporan tidak ditemukan."}), 404
        
    return jsonify({
        "report": report.to_dict(is_admin_or_officer=True),
        "history": [h.to_dict() for h in report.status_history]
    }), 200


@report_bp.route("/reports/<int:report_id>/status", methods=["PATCH"])
@roles_required("pengelola", "admin")
def update_report_status(report_id: int):
    """
    Updates report status according to predefined workflow (F-12).
    Disallows skipping status transitions.
    """
    db = db_session()
    report = db.query(Report).filter_by(id=report_id).first()
    if not report:
        return jsonify({"error": "Laporan tidak ditemukan."}), 404
        
    data = request.get_json(silent=True) or request.form
    target_code = data.get("status", "").upper()
    note = data.get("note", "").strip()
    
    target_status = db.query(ReportStatus).filter_by(code=target_code).first()
    if not target_status:
        return jsonify({"error": f"Status '{target_code}' tidak valid."}), 400
        
    current_code = report.status.code if report.status else "MENUNGGU_VERIFIKASI"
    allowed = ALLOWED_STATUS_TRANSITIONS.get(current_code, [])
    
    # Check valid transition
    if target_code not in allowed:
        return jsonify({
            "error": f"Perubahan status dari '{current_code}' ke '{target_code}' tidak diizinkan.",
            "allowed_next_statuses": allowed,
            "message": "Status harus mengikuti alur: Menunggu Verifikasi -> Diverifikasi -> Sedang Diproses -> Selesai."
        }), 400
        
    # Save change
    user = get_current_user()
    history = ReportStatusHistory(
        report_id=report.id,
        from_status_id=report.status_id,
        to_status_id=target_status.id,
        changed_by=user.id if user else None,
        note=note or f"Status diubah menjadi {target_status.name} oleh {user.name if user else 'Pengelola'}."
    )
    
    report.status_id = target_status.id
    report.updated_at = datetime.utcnow()
    db.add(history)
    db.commit()
    
    return jsonify({
        "message": f"Status berhasil diperbarui menjadi {target_status.name}.",
        "report": report.to_dict(is_admin_or_officer=True)
    }), 200


@report_bp.route("/reports/<int:report_id>/severity", methods=["PATCH"])
@roles_required("pengelola", "admin")
def update_report_severity(report_id: int):
    """
    Updates report severity level: 'ringan', 'sedang', or 'berat' (F-13).
    """
    db = db_session()
    report = db.query(Report).filter_by(id=report_id).first()
    if not report:
        return jsonify({"error": "Laporan tidak ditemukan."}), 404
        
    data = request.get_json(silent=True) or request.form
    sev = data.get("severity", "").lower()
    if sev not in ["ringan", "sedang", "berat"]:
        return jsonify({"error": "Tingkat keparahan harus salah satu dari: ringan, sedang, berat."}), 400
        
    report.severity = sev
    report.updated_at = datetime.utcnow()
    db.commit()
    
    return jsonify({
        "message": f"Tingkat keparahan ditetapkan menjadi {sev}.",
        "report": report.to_dict(is_admin_or_officer=True)
    }), 200


@report_bp.route("/photos/<int:photo_id>/predict", methods=["POST"])
@roles_required("pengelola", "admin")
def re_predict_photo(photo_id: int):
    """
    Triggers re-classification for an existing photo (F-07).
    """
    db = db_session()
    photo = db.query(Photo).filter_by(id=photo_id).first()
    if not photo:
        return jsonify({"error": "Foto tidak ditemukan."}), 404
        
    orig_path = Config.UPLOAD_FOLDER_ORIGINAL / photo.file_path
    ai_result = predict(str(orig_path))
    
    pred = AIPrediction(
        photo_id=photo.id,
        predicted_class=ai_result["predicted_class"],
        confidence=ai_result["confidence"],
        model_name=ai_result["model_name"],
        model_version=ai_result["model_version"]
    )
    db.add(pred)
    db.commit()
    
    return jsonify({
        "message": "Klasifikasi ulang berhasil.",
        "ai_prediction": ai_result
    }), 200
