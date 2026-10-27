import io
import pytest
from PIL import Image
from app import create_app
from models import db_session, Report, FacilityType, ReportStatus, User

@pytest.fixture
def app():
    app = create_app()
    app.config.update({
        "TESTING": True,
    })
    yield app
    db_session.remove()

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def officer_token(client):
    # Login as default seeded officer
    res = client.post("/api/auth/login", json={
        "email": "petugas@blater.desa.id",
        "password": "petugas123"
    })
    assert res.status_code == 200
    return res.get_json()["token"]

def generate_test_image(size=(100, 100), color="blue"):
    file_bytes = io.BytesIO()
    img = Image.new("RGB", size, color=color)
    img.save(file_bytes, "JPEG")
    file_bytes.seek(0)
    return file_bytes

# --- Test Scenario 1: Ekstraksi EXIF dan Validasi Format Derajat ---
def test_exif_extraction_and_conversion():
    from services.photo_service import _convert_to_degrees
    class FakeVal:
        def __init__(self, num, den):
            self.num = num
            self.den = den
    class FakeTag:
        def __init__(self, d, m, s):
            self.values = [FakeVal(d, 1), FakeVal(m, 1), FakeVal(s, 1)]
            
    deg = _convert_to_degrees(FakeTag(7, 25, 28))
    # 7 + 25/60 + 28/3600 = 7.424444...
    assert round(deg, 4) == 7.4244

# --- Test Spatial Analytics: KDE, DBSCAN, Getis-Ord, Priorities ---
def test_spatial_analysis_endpoints(client, officer_token):
    headers = {"Authorization": f"Bearer {officer_token}"}
    
    # 1. KDE
    r_kde = client.get("/api/map/heatmap?bandwidth=100")
    assert r_kde.status_code == 200
    assert "features" in r_kde.get_json()

    # 2. DBSCAN
    r_db = client.get("/api/map/clusters?eps=50&min_pts=3")
    assert r_db.status_code == 200
    assert "total_clusters" in r_db.get_json()

    # 3. Getis-Ord Gi*
    r_gi = client.get("/api/map/hotspots?threshold=150")
    assert r_gi.status_code == 200
    assert "significant_count" in r_gi.get_json()

    # 4. Priorities
    r_prio = client.get("/api/dashboard/priorities", headers=headers)
    assert r_prio.status_code == 200
    prios = r_prio.get_json()["top_priorities"]
    assert len(prios) <= 10
    if prios:
        # Check priority scores descending
        scores = [p["priority_score"] for p in prios]
        assert scores == sorted(scores, reverse=True)


# --- Test Scenario 1 & 2: Buat Laporan dengan Titik Valid ---
def test_create_report_valid_location(client):
    img = generate_test_image()
    # Point inside Blater
    lat = -7.4245
    lng = 109.3365

    # 1. Upload photo first
    up_res = client.post("/api/photos/upload", data={"photo": (img, "damage.jpg")})
    assert up_res.status_code == 201
    photo_id = up_res.get_json()["photo_id"]

    # 2. Create report
    payload = {
        "facility_type": "JALAN",
        "description": "Jalan berlubang cukup parah di depan warung.",
        "location": {"lat": lat, "lng": lng},
        "location_source": "manual_map",
        "photo_id": photo_id,
        "force_submit": True
    }
    res = client.post("/api/reports", json=payload)
    assert res.status_code == 201
    data = res.get_json()
    assert "report_id" in data
    assert data["status"] == "Menunggu Verifikasi"

# --- Test Scenario 3: Titik di Luar Batas Desa Ditolak (422) ---
def test_create_report_outside_boundary_rejected(client):
    img = generate_test_image()
    # Coordinates in Jakarta (outside Blater)
    lat = -6.2088
    lng = 106.8456

    up_res = client.post("/api/photos/upload", data={"photo": (img, "damage.jpg")})
    assert up_res.status_code == 201
    photo_id = up_res.get_json()["photo_id"]

    payload = {
        "facility_type": "JALAN",
        "description": "Kerusakan di luar desa.",
        "location": {"lat": lat, "lng": lng},
        "photo_id": photo_id
    }
    res = client.post("/api/reports", json=payload)
    assert res.status_code == 422
    assert "luar wilayah administratif Desa Blater" in res.get_json()["error"]

# --- Test Scenario 4: Filter Peta & Daftar Laporan Sesuai ---
def test_filter_map_reports(client):
    res = client.get("/api/map/reports?facility_type=JALAN")
    assert res.status_code == 200
    data = res.get_json()
    assert "features" in data
    for feat in data["features"]:
        assert feat["properties"]["facility_code"] == "JALAN"

# --- Test Scenario 5: Pengelola Mengubah Status Sesuai Alur ---
def test_officer_update_status_workflow(client, officer_token):
    # Get latest active report
    db = db_session()
    rep = db.query(Report).filter(Report.status.has(code="MENUNGGU_VERIFIKASI")).first()
    assert rep is not None

    headers = {"Authorization": f"Bearer {officer_token}"}
    
    # Menunggu -> Diverifikasi (Valid)
    res = client.patch(f"/api/reports/{rep.id}/status", json={
        "status": "DIVERIFIKASI",
        "note": "Laporan disetujui untuk penanganan."
    }, headers=headers)
    assert res.status_code == 200
    assert res.get_json()["report"]["status"]["code"] == "DIVERIFIKASI"

# --- Test Scenario 6: Melompati Status Ditolak (400) ---
def test_officer_skip_status_rejected(client, officer_token):
    db = db_session()
    # Find a report in MENUNGGU_VERIFIKASI
    menunggu_status = db.query(ReportStatus).filter_by(code="MENUNGGU_VERIFIKASI").first()
    rep = Report(
        facility_type_id=1,
        status_id=menunggu_status.id,
        description="Laporan uji loncat status",
        latitude=-7.4245,
        longitude=109.3365
    )
    db.add(rep)
    db.commit()

    headers = {"Authorization": f"Bearer {officer_token}"}
    
    # Try to jump directly to SELESAI
    res = client.patch(f"/api/reports/{rep.id}/status", json={
        "status": "SELESAI",
        "note": "Mencoba langsung selesai."
    }, headers=headers)
    assert res.status_code == 400
    assert "tidak diizinkan" in res.get_json()["error"]

# --- Test Scenario 7: Warga Tanpa Token Ditolak Mengakses Endpoint Pengelola (401) ---
def test_citizen_forbidden_officer_endpoint(client):
    # Without Authorization header
    res = client.get("/api/reports")
    assert res.status_code == 401

# --- Test Scenario 8: Deteksi Laporan Ganda dalam 6 Meter (409) ---
def test_duplicate_detection(client):
    img = generate_test_image()
    up_res = client.post("/api/photos/upload", data={"photo": (img, "damage.jpg")})
    photo_id = up_res.get_json()["photo_id"]

    # Target point
    lat = -7.4245
    lng = 109.3365

    # 1. Create original report
    payload1 = {
        "facility_type": "PJU",
        "description": "Lampu PJU padam di depan gang.",
        "location": {"lat": lat, "lng": lng},
        "photo_id": photo_id,
        "force_submit": True
    }
    r1 = client.post("/api/reports", json=payload1)
    assert r1.status_code == 201

    # 2. Try creating duplicate at exactly same point or within 2 meters without force_submit
    payload2 = {
        "facility_type": "PJU",
        "description": "PJU mati lagi di gang ini.",
        "location": {"lat": lat + 0.00001, "lng": lng + 0.00001},  # ~1.5 meters away
        "photo_id": photo_id,
        "force_submit": False
    }
    r2 = client.post("/api/reports", json=payload2)
    assert r2.status_code == 409
    data2 = r2.get_json()
    assert data2["code"] == "DUPLICATE_SUSPECT"
    assert len(data2["duplicate_reports"]) > 0

# --- Test Scenario 9: Foto Melebihi Batas Ukuran Ditolak (413) ---
def test_photo_exceeds_size_rejected(client):
    # Create fake oversized buffer (> 5MB)
    big_file = io.BytesIO(b"0" * (5 * 1024 * 1024 + 1024))
    res = client.post("/api/photos/upload", data={"photo": (big_file, "huge.jpg")})
    assert res.status_code == 413

# --- Test Scenario 10: Cek Status Valid & Tidak Valid ---
def test_check_status_valid_and_invalid(client):
    # Valid existing report
    db = db_session()
    rep = db.query(Report).first()
    assert rep is not None

    res_valid = client.get(f"/api/reports/{rep.id}/status")
    assert res_valid.status_code == 200
    assert res_valid.get_json()["id"] == rep.id

    # Invalid ID
    res_invalid = client.get("/api/reports/999999/status")
    assert res_invalid.status_code == 404
