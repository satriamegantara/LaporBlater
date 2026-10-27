from flask import Blueprint, jsonify, request
from models import db_session, Report, FacilityType, ReportStatus
from services.spatial_service import (
    get_boundary_geojson, get_roads_geojson, 
    compute_kde, compute_dbscan, compute_getis_ord
)
from services.auth_service import roles_required

map_bp = Blueprint("map_bp", __name__, url_prefix="/api/map")

@map_bp.route("/boundary", methods=["GET"])
def get_boundary():
    """Returns boundary GeoJSON of Desa Blater (F-15)."""
    return jsonify(get_boundary_geojson()), 200


@map_bp.route("/roads", methods=["GET"])
def get_roads():
    """Returns road network GeoJSON of Desa Blater (F-15)."""
    return jsonify(get_roads_geojson()), 200


@map_bp.route("/reports", methods=["GET"])
def get_map_reports():
    """
    Returns public GeoJSON FeatureCollection of reports with optional filters (F-15, F-16, F-17).
    Filters: facility_type, status, severity, source_type.
    """
    db = db_session()
    query = db.query(Report)
    
    fac = request.args.get("facility_type")
    if fac:
        query = query.join(FacilityType, Report.facility_type_id == FacilityType.id).filter(FacilityType.code == fac.upper())
        
    status = request.args.get("status")
    if status:
        query = query.join(ReportStatus, Report.status_id == ReportStatus.id).filter(ReportStatus.code == status.upper())
        
    severity = request.args.get("severity")
    if severity:
        query = query.filter(Report.severity == severity.lower())
        
    reports = query.all()
    
    features = []
    for r in reports:
        photo = r.photos[0] if r.photos else None
        features.append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [round(r.longitude, 6), round(r.latitude, 6)]
            },
            "properties": {
                "id": r.id,
                "facility_type": r.facility_type.name if r.facility_type else "Umum",
                "facility_code": r.facility_type.code if r.facility_type else "UMUM",
                "status": r.status.name if r.status else "Menunggu",
                "status_code": r.status.code if r.status else "MENUNGGU_VERIFIKASI",
                "severity": r.severity or "Belum Ditentukan",
                "description": r.description[:120] + "..." if len(r.description) > 120 else r.description,
                "photo_url": f"/uploads/photos/public/{photo.public_path}" if photo else None,
                "created_at": r.created_at.strftime("%d %b %Y, %H:%M") if r.created_at else None
            }
        })
        
    return jsonify({
        "type": "FeatureCollection",
        "features": features,
        "count": len(features)
    }), 200


@map_bp.route("/heatmap", methods=["GET"])
def get_heatmap():
    """
    Computes and returns Kernel Density Estimation (KDE) surface (F-18).
    Supports bandwidth query parameter (in meters).
    """
    db = db_session()
    bandwidth = float(request.args.get("bandwidth", 100.0))
    
    # Analyze active reports
    selesai_status = db.query(ReportStatus).filter_by(code="SELESAI").first()
    selesai_id = selesai_status.id if selesai_status else -1
    
    reports = db.query(Report).filter(Report.status_id != selesai_id).all()
    kde_result = compute_kde(reports, bandwidth_meters=bandwidth)
    return jsonify(kde_result), 200


@map_bp.route("/clusters", methods=["GET"])
def get_clusters():
    """
    Computes and returns DBSCAN clusters (F-19).
    Supports eps (meters) and min_pts query parameters.
    """
    db = db_session()
    eps = float(request.args.get("eps", 50.0))
    min_pts = int(request.args.get("min_pts", 3))
    
    selesai_status = db.query(ReportStatus).filter_by(code="SELESAI").first()
    selesai_id = selesai_status.id if selesai_status else -1
    
    reports = db.query(Report).filter(Report.status_id != selesai_id).all()
    dbscan_result = compute_dbscan(reports, eps_meters=eps, min_pts=min_pts)
    return jsonify(dbscan_result), 200


@map_bp.route("/hotspots", methods=["GET"])
def get_hotspots():
    """
    Computes and returns Getis-Ord Gi* hotspot statistics (F-20).
    Only statistically significant points (p < 0.05) or all scored points.
    """
    db = db_session()
    dist_thresh = float(request.args.get("threshold", 150.0))
    
    selesai_status = db.query(ReportStatus).filter_by(code="SELESAI").first()
    selesai_id = selesai_status.id if selesai_status else -1
    
    reports = db.query(Report).filter(Report.status_id != selesai_id).all()
    gi_result = compute_getis_ord(reports, distance_threshold_meters=dist_thresh)
    return jsonify(gi_result), 200
