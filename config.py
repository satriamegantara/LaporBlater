import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "laporblater-gis-secret-key-unsoed-2026")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "jwt-super-secret-blater-sig-2026")
    JWT_EXPIRATION_HOURS = int(os.getenv("JWT_EXPIRATION_HOURS", "24"))
    
    # Database URL
    DATABASE_URL = os.getenv(
        "DATABASE_URL", 
        "postgresql+psycopg2://postgres:password@localhost:5432/laporblater"
    )
    
    # File Uploads
    MAX_CONTENT_LENGTH = int(os.getenv("MAX_UPLOAD_SIZE_MB", "5")) * 1024 * 1024  # 5 MB
    ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}
    UPLOAD_FOLDER_ORIGINAL = BASE_DIR / "uploads" / "photos" / "original"
    UPLOAD_FOLDER_PUBLIC = BASE_DIR / "uploads" / "photos" / "public"
    
    # Geo Data
    BOUNDARY_GEOJSON = BASE_DIR / "data" / "blater_boundary.geojson"
    ROADS_GEOJSON = BASE_DIR / "data" / "blater_roads.geojson"
    
    # Coordinate Reference Systems
    CRS_STORAGE = "EPSG:4326"
    CRS_METRIC = "EPSG:32749"  # UTM Zone 49S
    
    # Analysis & Business Defaults (PRD Section 19 & 8)
    AI_CONFIDENCE_THRESHOLD = float(os.getenv("AI_CONFIDENCE_THRESHOLD", "0.85"))
    DUPLICATE_RADIUS_METERS = float(os.getenv("DUPLICATE_RADIUS_METERS", "6.0"))
    DEFAULT_DBSCAN_EPS_METERS = float(os.getenv("DEFAULT_DBSCAN_EPS_METERS", "50.0"))
    DEFAULT_DBSCAN_MIN_PTS = int(os.getenv("DEFAULT_DBSCAN_MIN_PTS", "3"))
    DEFAULT_KDE_BANDWIDTH_METERS = float(os.getenv("DEFAULT_KDE_BANDWIDTH_METERS", "100.0"))
    
    # Priority Weights (PRD 8.5)
    # S = 0.35 * Severity + 0.30 * Density + 0.20 * SafetyRisk + 0.15 * Age
    PRIORITY_WEIGHTS = {
        "severity": 0.35,
        "density": 0.30,
        "safety_risk": 0.20,
        "unhandled_duration": 0.15
    }
