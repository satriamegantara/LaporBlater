import json
import math
from pathlib import Path
from datetime import datetime
import numpy as np
from scipy import stats
from shapely.geometry import shape, Point, Polygon, MultiPolygon
from shapely.ops import transform
import pyproj
from sklearn.cluster import DBSCAN
from sklearn.neighbors import NearestNeighbors

from config import Config
from models import Report, ReportStatus, FacilityType, SystemParameter

# Transformer between WGS 84 (EPSG:4326) and UTM Zone 49S (EPSG:32749)
_wgs84_to_utm = pyproj.Transformer.from_crs("EPSG:4326", "EPSG:32749", always_xy=True)
_utm_to_wgs84 = pyproj.Transformer.from_crs("EPSG:32749", "EPSG:4326", always_xy=True)

# Cache boundary shape
_cached_boundary_polygon = None
_cached_boundary_geojson = None
_cached_roads_geojson = None


def to_utm(lng: float, lat: float):
    """Converts (lng, lat) in EPSG:4326 to (x, y) in UTM 49S meters."""
    return _wgs84_to_utm.transform(lng, lat)


def to_wgs84(x: float, y: float):
    """Converts (x, y) in UTM 49S meters to (lng, lat) in EPSG:4326."""
    return _utm_to_wgs84.transform(x, y)


def get_boundary_geojson():
    """Loads and returns the GeoJSON of Desa Blater boundary."""
    global _cached_boundary_geojson
    if _cached_boundary_geojson is None:
        if Config.BOUNDARY_GEOJSON.exists():
            with open(Config.BOUNDARY_GEOJSON, "r", encoding="utf-8") as f:
                _cached_boundary_geojson = json.load(f)
        else:
            raise FileNotFoundError(f"Boundary file not found at {Config.BOUNDARY_GEOJSON}")
    return _cached_boundary_geojson


def get_roads_geojson():
    """Loads and returns the GeoJSON of roads in Desa Blater."""
    global _cached_roads_geojson
    if _cached_roads_geojson is None:
        if Config.ROADS_GEOJSON.exists():
            with open(Config.ROADS_GEOJSON, "r", encoding="utf-8") as f:
                _cached_roads_geojson = json.load(f)
        else:
            _cached_roads_geojson = {"type": "FeatureCollection", "features": []}
    return _cached_roads_geojson


def get_boundary_polygon():
    """Returns a Shapely Polygon/MultiPolygon of Desa Blater."""
    global _cached_boundary_polygon
    if _cached_boundary_polygon is None:
        boundary_data = get_boundary_geojson()
        features = boundary_data.get("features", [])
        if features:
            geom = features[0].get("geometry")
            _cached_boundary_polygon = shape(geom)
        else:
            raise ValueError("No feature found in boundary GeoJSON.")
    return _cached_boundary_polygon


def validate_location(lat: float, lng: float):
    """
    Validates coordinates:
    1. Range check: lat [-90, 90], lng [-180, 180]
    2. ST_Within check: Point inside Desa Blater boundary polygon
    Returns (is_valid: bool, message: str)
    """
    if lat is None or lng is None:
        return False, "Koordinat latitude dan longitude wajib diisi."
        
    try:
        lat = float(lat)
        lng = float(lng)
    except (ValueError, TypeError):
        return False, "Format koordinat tidak valid."
        
    if not (-90.0 <= lat <= 90.0 and -180.0 <= lng <= 180.0):
        return False, "Koordinat di luar rentang wajar permukaan bumi."
        
    poly = get_boundary_polygon()
    pt = Point(lng, lat)  # Note: Shapely uses (x=longitude, y=latitude)
    
    if not poly.contains(pt) and not poly.touches(pt):
        return False, "Lokasi laporan berada di luar wilayah administratif Desa Blater."
        
    return True, "Lokasi valid berada di dalam Desa Blater."


def calculate_metric_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Calculates Euclidean distance in meters between two points using UTM 49S."""
    x1, y1 = to_utm(lng1, lat1)
    x2, y2 = to_utm(lng2, lat2)
    return math.hypot(x2 - x1, y2 - y1)


def detect_duplicates(session, lat: float, lng: float, facility_type_id: int, radius_meters: float = None):
    """
    Detects potential duplicate reports:
    Same facility_type within radius_meters (default 6m) from existing active reports.
    """
    if radius_meters is None:
        param = session.query(SystemParameter).filter_by(key="duplicate_params").first()
        radius_meters = param.value.get("radius_meters", Config.DUPLICATE_RADIUS_METERS) if param else Config.DUPLICATE_RADIUS_METERS

    # Query active reports with same facility_type_id
    selesai_status = session.query(ReportStatus).filter_by(code="SELESAI").first()
    selesai_id = selesai_status.id if selesai_status else -1
    
    # Simple bounding box pre-filter in degrees (~1 deg lat ~ 111,000m, 1 deg lng ~ 110,000m)
    deg_buffer = (radius_meters + 10.0) / 100000.0
    
    candidates = session.query(Report).filter(
        Report.facility_type_id == facility_type_id,
        Report.status_id != selesai_id,
        Report.latitude.between(lat - deg_buffer, lat + deg_buffer),
        Report.longitude.between(lng - deg_buffer, lng + deg_buffer)
    ).all()
    
    duplicates = []
    for cand in candidates:
        dist = calculate_metric_distance(lat, lng, cand.latitude, cand.longitude)
        if dist <= radius_meters:
            duplicates.append({
                "report_id": cand.id,
                "distance_meters": round(dist, 2),
                "description": cand.description,
                "created_at": cand.created_at.isoformat() if cand.created_at else None,
                "status": cand.status.name if cand.status else None
            })
            
    return duplicates


def compute_kde(reports, bandwidth_meters=100.0, grid_resolution=30):
    """
    Computes 2D Kernel Density Estimation across Desa Blater using UTM 49S coordinates.
    Returns GeoJSON feature collection with grid points and normalized density (0 to 1).
    """
    if not reports:
        return {"type": "FeatureCollection", "features": [], "max_density": 0}
        
    coords_utm = np.array([to_utm(r.longitude, r.latitude) for r in reports])
    if len(coords_utm) < 2:
        # Trivial single point
        lng, lat = reports[0].longitude, reports[0].latitude
        return {
            "type": "FeatureCollection",
            "features": [{
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [lng, lat]},
                "properties": {"density": 1.0}
            }],
            "max_density": 1.0
        }

    # Bounding box of Desa Blater in UTM
    poly = get_boundary_polygon()
    min_lng, min_lat, max_lng, max_lat = poly.bounds
    min_x, min_y = to_utm(min_lng, min_lat)
    max_x, max_y = to_utm(max_lng, max_lat)
    
    # Create grid
    x_grid = np.linspace(min_x, max_x, grid_resolution)
    y_grid = np.linspace(min_y, max_y, grid_resolution)
    xx, yy = np.meshgrid(x_grid, y_grid)
    grid_coords = np.vstack([xx.ravel(), yy.ravel()])
    
    # Fit gaussian KDE
    kde = stats.gaussian_kde(coords_utm.T, bw_method=bandwidth_meters / np.std(coords_utm))
    density = kde(grid_coords).reshape(xx.shape)
    
    max_val = np.max(density)
    norm_density = density / max_val if max_val > 0 else density
    
    features = []
    for i in range(grid_resolution):
        for j in range(grid_resolution):
            val = float(norm_density[i, j])
            if val > 0.05:  # Only points with non-trivial density
                wgs_lng, wgs_lat = to_wgs84(float(xx[i, j]), float(yy[i, j]))
                pt = Point(wgs_lng, wgs_lat)
                if poly.contains(pt):  # keep inside village boundary
                    features.append({
                        "type": "Feature",
                        "geometry": {
                            "type": "Point",
                            "coordinates": [round(wgs_lng, 6), round(wgs_lat, 6)]
                        },
                        "properties": {
                            "density": round(val, 4)
                        }
                    })
                    
    return {
        "type": "FeatureCollection",
        "features": features,
        "bandwidth_meters": bandwidth_meters,
        "max_density": float(max_val)
    }


def compute_dbscan(reports, eps_meters=50.0, min_pts=3):
    """
    Computes DBSCAN clustering on active reports using UTM 49S metric coordinates.
    Returns clustered GeoJSON point collection with cluster labels and sizes.
    """
    if not reports:
        return {"type": "FeatureCollection", "features": [], "total_clusters": 0}
        
    coords_utm = np.array([to_utm(r.longitude, r.latitude) for r in reports])
    
    if len(reports) < min_pts:
        # All labeled as noise
        features = []
        for r in reports:
            features.append({
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [r.longitude, r.latitude]},
                "properties": {
                    "report_id": r.id,
                    "cluster_id": -1,
                    "is_noise": True,
                    "cluster_size": 1
                }
            })
        return {"type": "FeatureCollection", "features": features, "total_clusters": 0}
        
    db = DBSCAN(eps=eps_meters, min_samples=min_pts, metric="euclidean").fit(coords_utm)
    labels = db.labels_
    
    # Count cluster sizes
    unique_labels = set(labels)
    cluster_sizes = {}
    for l in unique_labels:
        cluster_sizes[l] = int(np.sum(labels == l))
        
    total_clusters = len([l for l in unique_labels if l != -1])
    
    features = []
    for r, label in zip(reports, labels):
        features.append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [round(r.longitude, 6), round(r.latitude, 6)]
            },
            "properties": {
                "report_id": r.id,
                "cluster_id": int(label),
                "is_noise": bool(label == -1),
                "cluster_size": cluster_sizes.get(label, 1),
                "facility_type": r.facility_type.name if r.facility_type else None,
                "severity": r.severity
            }
        })
        
    return {
        "type": "FeatureCollection",
        "features": features,
        "total_clusters": total_clusters,
        "eps_meters": eps_meters,
        "min_pts": min_pts
    }


def compute_getis_ord(reports, distance_threshold_meters=150.0):
    """
    Computes local Getis-Ord Gi* spatial autocorrelation on report points.
    Returns points with z-score, p-value, and statistical significance flags (p < 0.05).
    """
    n = len(reports)
    if n < 3:
        return {"type": "FeatureCollection", "features": [], "significant_count": 0}
        
    coords_utm = np.array([to_utm(r.longitude, r.latitude) for r in reports])
    
    # Value x_i represents severity / weight of each report
    severity_map = {"berat": 3.0, "sedang": 2.0, "ringan": 1.0}
    x = np.array([severity_map.get(r.severity, 1.5) for r in reports], dtype=float)
    
    x_bar = np.mean(x)
    s = np.std(x)
    if s == 0:
        s = 1.0  # avoid division by zero
        
    # Spatial weight matrix: binary distance band or Gaussian decay
    # In Gi*, w_ii is typically included (Gi*)
    dist_matrix = np.linalg.norm(coords_utm[:, None, :] - coords_utm[None, :, :], axis=-1)
    W = (dist_matrix <= distance_threshold_meters).astype(float)
    
    features = []
    significant_count = 0
    
    for i in range(n):
        w_i = W[i]
        sum_w = np.sum(w_i)
        sum_w_sq = np.sum(w_i ** 2)
        
        numerator = np.sum(w_i * x) - (x_bar * sum_w)
        denominator = s * math.sqrt((n * sum_w_sq - (sum_w ** 2)) / (n - 1.0)) if (n * sum_w_sq - (sum_w ** 2)) > 0 else 1.0
        
        z_score = numerator / denominator if denominator != 0 else 0.0
        p_val = 2.0 * (1.0 - stats.norm.cdf(abs(z_score)))
        
        # Classification
        hotspot_type = "Tidak Signifikan"
        if p_val < 0.05:
            significant_count += 1
            if z_score > 0:
                hotspot_type = "Hotspot Signifikan (Klaster Kerusakan Tinggi)"
            else:
                hotspot_type = "Coldspot Signifikan"
                
        r = reports[i]
        features.append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [round(r.longitude, 6), round(r.latitude, 6)]
            },
            "properties": {
                "report_id": r.id,
                "z_score": round(float(z_score), 4),
                "p_value": round(float(p_val), 5),
                "is_significant": bool(p_val < 0.05),
                "hotspot_type": hotspot_type,
                "severity": r.severity
            }
        })
        
    return {
        "type": "FeatureCollection",
        "features": features,
        "significant_count": significant_count,
        "distance_threshold_meters": distance_threshold_meters
    }


def compute_priority_scores(session, custom_weights=None):
    """
    Computes priority scores according to PRD Section 8.5 (F-24, F-25):
    S = w1 * Severity + w2 * Density + w3 * SafetyRisk + w4 * Duration
    Excludes reports with status 'SELESAI'.
    Returns list of dicts ordered by priority score descending.
    """
    # Fetch parameters or use defaults
    param = session.query(SystemParameter).filter_by(key="priority_weights").first()
    weights = custom_weights or (param.value if param else Config.PRIORITY_WEIGHTS)
    
    w_sev = float(weights.get("severity", 0.35))
    w_den = float(weights.get("density", 0.30))
    w_saf = float(weights.get("safety_risk", 0.20))
    w_dur = float(weights.get("unhandled_duration", 0.15))
    
    selesai_status = session.query(ReportStatus).filter_by(code="SELESAI").first()
    selesai_id = selesai_status.id if selesai_status else -1
    
    active_reports = session.query(Report).filter(Report.status_id != selesai_id).all()
    if not active_reports:
        return []
        
    now = datetime.utcnow()
    n = len(active_reports)
    
    # 1. Severity scores
    severity_values = []
    severity_scores = []
    for r in active_reports:
        sev = (r.severity or "").lower()
        if sev == "berat":
            s_val = 1.0
        elif sev == "sedang":
            s_val = 0.66
        elif sev == "ringan":
            s_val = 0.33
        else:
            # Fallback based on AI prediction if available
            pred = None
            if r.photos and r.photos[0].ai_predictions:
                pred = r.photos[0].ai_predictions[0].predicted_class
            if pred and "RUSAK" in pred:
                s_val = 0.66
            else:
                s_val = 0.33
        severity_values.append(s_val)
        severity_scores.append(s_val)
        
    # 2. Density scores (using distance to neighbors or DBSCAN cluster size)
    coords_utm = np.array([to_utm(r.longitude, r.latitude) for r in active_reports])
    density_scores = []
    if n > 1:
        # Measure local density via count of reports within 100m
        dist_matrix = np.linalg.norm(coords_utm[:, None, :] - coords_utm[None, :, :], axis=-1)
        counts = np.sum(dist_matrix <= 100.0, axis=-1).astype(float)
        min_c, max_c = np.min(counts), np.max(counts)
        if max_c > min_c:
            density_scores = list((counts - min_c) / (max_c - min_c))
        else:
            density_scores = [0.5] * n
    else:
        density_scores = [0.5]
        
    # 3. Safety risk scores (facility type & campus/kost proximity)
    # FT UNSOED Blater is roughly at (-7.4235, 109.3400)
    campus_pt_utm = to_utm(109.3400, -7.4235)
    safety_scores = []
    for r in active_reports:
        fac_code = r.facility_type.code if r.facility_type else ""
        sev = (r.severity or "").lower()
        base_risk = 0.5
        if fac_code == "PJU":
            base_risk = 0.85
        elif fac_code == "JALAN":
            base_risk = 0.90 if sev == "berat" else 0.70
        elif fac_code == "DRAINASE":
            base_risk = 0.75 if sev == "berat" else 0.50
            
        # Proximity buffer to campus/settlement (within 300m adds risk)
        rx, ry = to_utm(r.longitude, r.latitude)
        dist_campus = math.hypot(rx - campus_pt_utm[0], ry - campus_pt_utm[1])
        if dist_campus <= 300.0:
            base_risk = min(1.0, base_risk + 0.15)
        safety_scores.append(base_risk)
        
    # 4. Unhandled duration (days since creation)
    days = [(now - r.created_at).total_seconds() / 86400.0 for r in active_reports]
    min_d, max_d = min(days), max(days)
    if max_d > min_d:
        duration_scores = [(d - min_d) / (max_d - min_d) for d in days]
    else:
        duration_scores = [0.5] * n
        
    # Aggregate S
    results = []
    for i, r in enumerate(active_reports):
        s1 = severity_scores[i]
        s2 = density_scores[i]
        s3 = safety_scores[i]
        s4 = duration_scores[i]
        
        contrib1 = w_sev * s1
        contrib2 = w_den * s2
        contrib3 = w_saf * s3
        contrib4 = w_dur * s4
        total_score = contrib1 + contrib2 + contrib3 + contrib4
        
        # Primary reason / highest contributing factor
        factors = [
            ("Tingkat Keparahan", contrib1),
            ("Kepadatan Laporan di Sekitar", contrib2),
            ("Risiko Keselamatan Warga", contrib3),
            ("Lama Belum Ditangani", contrib4)
        ]
        factors.sort(key=lambda x: x[1], reverse=True)
        primary_reason = factors[0][0]
        
        results.append({
            "report_id": r.id,
            "report": r.to_dict(is_admin_or_officer=True),
            "priority_score": round(float(total_score), 4),
            "primary_reason": primary_reason,
            "components": {
                "severity_score": round(float(s1), 3),
                "density_score": round(float(s2), 3),
                "safety_risk_score": round(float(s3), 3),
                "unhandled_duration_days": round(float(days[i]), 1),
                "duration_score": round(float(s4), 3)
            }
        })
        
    results.sort(key=lambda x: x["priority_score"], reverse=True)
    return results
