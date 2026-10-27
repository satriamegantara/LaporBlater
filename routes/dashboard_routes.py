from datetime import datetime
from flask import Blueprint, jsonify, request
from sqlalchemy import func
from models import db_session, Report, ReportStatus, FacilityType, AIPrediction
from services.spatial_service import compute_priority_scores
from services.auth_service import roles_required

dashboard_bp = Blueprint("dashboard_bp", __name__, url_prefix="/api/dashboard")

@dashboard_bp.route("/summary", methods=["GET"])
@roles_required("pengelola", "admin")
def get_summary():
    """
    Returns high-level statistics and aggregations for officer dashboard (F-23).
    """
    db = db_session()
    
    # 1. Total reports
    total_reports = db.query(Report).count()
    
    # 2. Count by status
    status_counts = {}
    statuses = db.query(ReportStatus).order_by(ReportStatus.sort_order).all()
    for s in statuses:
        c = db.query(Report).filter_by(status_id=s.id).count()
        status_counts[s.code] = {
            "name": s.name,
            "count": c
        }
        
    # 3. Count by facility type
    facility_counts = {}
    facilities = db.query(FacilityType).all()
    for f in facilities:
        c = db.query(Report).filter_by(facility_type_id=f.id).count()
        facility_counts[f.code] = {
            "name": f.name,
            "count": c
        }
        
    # 4. Count by severity
    severity_counts = {
        "berat": db.query(Report).filter_by(severity="berat").count(),
        "sedang": db.query(Report).filter_by(severity="sedang").count(),
        "ringan": db.query(Report).filter_by(severity="ringan").count(),
        "belum_ditentukan": db.query(Report).filter(Report.severity == None).count()
    }
    
    # 5. Source type distribution
    source_counts = {
        "warga": db.query(Report).filter_by(source_type="warga").count(),
        "survei_tim": db.query(Report).filter_by(source_type="survei_tim").count()
    }
    
    # 6. AI prediction distribution
    ai_classes = db.query(
        AIPrediction.predicted_class, 
        func.count(AIPrediction.id)
    ).group_by(AIPrediction.predicted_class).all()
    
    ai_distribution = {item[0]: item[1] for item in ai_classes}
    
    return jsonify({
        "total_reports": total_reports,
        "by_status": status_counts,
        "by_facility": facility_counts,
        "by_severity": severity_counts,
        "by_source": source_counts,
        "ai_distribution": ai_distribution
    }), 200


@dashboard_bp.route("/priorities", methods=["GET"])
@roles_required("pengelola", "admin")
def get_priorities():
    """
    Calculates and returns top priority reports with scores and rationale (F-24, F-25).
    Supports sensitivity test weights (±5% check).
    """
    db = db_session()
    
    # Check custom weights if testing sensitivity
    custom_weights = None
    if request.args.get("w_sev"):
        custom_weights = {
            "severity": float(request.args.get("w_sev", 0.35)),
            "density": float(request.args.get("w_den", 0.30)),
            "safety_risk": float(request.args.get("w_saf", 0.20)),
            "unhandled_duration": float(request.args.get("w_dur", 0.15))
        }
        
    ranked = compute_priority_scores(db, custom_weights=custom_weights)
    
    # Limit to top 10 as specified in PRD 8.5 F-25
    top_10 = ranked[:10]
    
    return jsonify({
        "total_active_reports": len(ranked),
        "weights_used": custom_weights or "default_system_weights",
        "top_priorities": top_10
    }), 200
