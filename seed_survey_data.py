import os
import random
from datetime import datetime, timedelta
from PIL import Image, ImageDraw
from config import Config
from models import (
    init_db, db_session, Report, Photo, AIPrediction, 
    FacilityType, ReportStatus, User, ReportStatusHistory
)
from services.spatial_service import get_boundary_polygon, to_utm

def create_sample_image(filename: str, color: tuple, label: str):
    """Creates a sample dummy image for test reports."""
    Config.UPLOAD_FOLDER_ORIGINAL.mkdir(parents=True, exist_ok=True)
    Config.UPLOAD_FOLDER_PUBLIC.mkdir(parents=True, exist_ok=True)
    
    orig_path = Config.UPLOAD_FOLDER_ORIGINAL / filename
    pub_path = Config.UPLOAD_FOLDER_PUBLIC / f"pub_{filename.replace('orig_', '')}"
    
    if not orig_path.exists():
        img = Image.new("RGB", (640, 480), color=color)
        draw = ImageDraw.Draw(img)
        draw.rectangle([20, 20, 620, 460], outline="white", width=4)
        draw.text((40, 40), f"[Dokumentasi Survei LaporBlater]\n{label}", fill="white")
        img.save(orig_path, "JPEG")
        img.save(pub_path, "JPEG")
        
    return str(orig_path), str(pub_path)


def seed():
    init_db()
    db = db_session()
    
    # Check if reports already exist
    if db.query(Report).count() > 0:
        print("Data reports already exist, skipping seed.")
        return
        
    print("Seeding initial field survey data for Desa Blater...")
    
    fac_jalan = db.query(FacilityType).filter_by(code="JALAN").first()
    fac_pju = db.query(FacilityType).filter_by(code="PJU").first()
    fac_drainase = db.query(FacilityType).filter_by(code="DRAINASE").first()
    
    st_menunggu = db.query(ReportStatus).filter_by(code="MENUNGGU_VERIFIKASI").first()
    st_diverifikasi = db.query(ReportStatus).filter_by(code="DIVERIFIKASI").first()
    st_diproses = db.query(ReportStatus).filter_by(code="DIPROSES").first()
    st_selesai = db.query(ReportStatus).filter_by(code="SELESAI").first()
    
    admin_user = db.query(User).filter_by(role="admin").first()
    
    survey_points = [
        # Jalan
        {
            "facility": fac_jalan, "status": st_menunggu, "severity": "berat",
            "lat": -7.4245, "lng": 109.3385,
            "desc": "Badan jalan amblas dan berlubang sedalam 15 cm di depan kost mahasiswa FT Unsoed.",
            "color": (120, 70, 50), "ai_class": "JALAN_RUSAK", "conf": 0.94
        },
        {
            "facility": fac_jalan, "status": st_diverifikasi, "severity": "berat",
            "lat": -7.4250, "lng": 109.3392,
            "desc": "Lubang jalan aspal menganga diameter 80 cm membahayakan pengendara motor malam hari.",
            "color": (100, 60, 40), "ai_class": "JALAN_RUSAK", "conf": 0.91
        },
        {
            "facility": fac_jalan, "status": st_diproses, "severity": "sedang",
            "lat": -7.4228, "lng": 109.3340,
            "desc": "Aspal terkelupas dan retak buaya di jalan utama Dusun 1 Blater.",
            "color": (90, 80, 70), "ai_class": "JALAN_RUSAK", "conf": 0.88
        },
        {
            "facility": fac_jalan, "status": st_selesai, "severity": "ringan",
            "lat": -7.4215, "lng": 109.3325,
            "desc": "Kerikil berserakan dan retakan rambut dekat gapura perbatasan desa.",
            "color": (110, 100, 90), "ai_class": "JALAN_RUSAK", "conf": 0.82
        },
        # PJU
        {
            "facility": fac_pju, "status": st_menunggu, "severity": "berat",
            "lat": -7.4239, "lng": 109.3398,
            "desc": "Lampu penerangan jalan padam total selama 5 hari, ruas jalan gang kampus sangat gelap.",
            "color": (30, 30, 60), "ai_class": "PJU_RUSAK", "conf": 0.95
        },
        {
            "facility": fac_pju, "status": st_diverifikasi, "severity": "berat",
            "lat": -7.4262, "lng": 109.3370,
            "desc": "Tiang PJU keropos dan miring ke arah badan jalan setelah tersenggol truk.",
            "color": (40, 40, 70), "ai_class": "PJU_RUSAK", "conf": 0.89
        },
        {
            "facility": fac_pju, "status": st_diproses, "severity": "sedang",
            "lat": -7.4280, "lng": 109.3355,
            "desc": "Lampu PJU berkedip-kedip tidak stabil dan kap penutup lampu pecah.",
            "color": (50, 50, 80), "ai_class": "PJU_RUSAK", "conf": 0.87
        },
        # Drainase
        {
            "facility": fac_drainase, "status": st_menunggu, "severity": "berat",
            "lat": -7.4241, "lng": 109.3380,
            "desc": "Saluran drainase tertutup sampah plastik dan lumpur tebal mengakibatkan genangan saat hujan.",
            "color": (40, 70, 90), "ai_class": "DRAINASE_TERSUMBAT", "conf": 0.92
        },
        {
            "facility": fac_drainase, "status": st_diverifikasi, "severity": "sedang",
            "lat": -7.4271, "lng": 109.3362,
            "desc": "Tanggul saluran parit ambrol sepanjang 3 meter terkikis aliran air sawah.",
            "color": (35, 65, 85), "ai_class": "DRAINASE_TERSUMBAT", "conf": 0.86
        },
        {
            "facility": fac_drainase, "status": st_diproses, "severity": "sedang",
            "lat": -7.4290, "lng": 109.3410,
            "desc": "Gorong-gorong penyaluran air tersumbat endapan pasir.",
            "color": (45, 75, 95), "ai_class": "DRAINASE_TERSUMBAT", "conf": 0.84
        },
        # Dense cluster around campus intersection (KDE & DBSCAN hotspot testing)
        {
            "facility": fac_jalan, "status": st_menunggu, "severity": "berat",
            "lat": -7.4243, "lng": 109.3388,
            "desc": "Lubang jalan aspal tepat di tikungan gang kost.",
            "color": (115, 65, 45), "ai_class": "JALAN_RUSAK", "conf": 0.93
        },
        {
            "facility": fac_pju, "status": st_menunggu, "severity": "berat",
            "lat": -7.4244, "lng": 109.3386,
            "desc": "Lampu tiang penerangan gang mati total.",
            "color": (35, 35, 65), "ai_class": "PJU_RUSAK", "conf": 0.91
        }
    ]
    
    now = datetime.utcnow()
    
    for idx, item in enumerate(survey_points):
        # Days ago
        days_ago = random.randint(1, 14)
        created_at = now - timedelta(days=days_ago, hours=random.randint(1, 10))
        
        report = Report(
            facility_type_id=item["facility"].id,
            status_id=item["status"].id,
            severity=item["severity"],
            description=item["desc"],
            latitude=item["lat"],
            longitude=item["lng"],
            location_source="exif",
            source_type="survei_tim",
            created_at=created_at,
            updated_at=created_at + timedelta(hours=2)
        )
        db.add(report)
        db.flush()
        
        # Sample photo
        img_name = f"orig_survey_{idx+1}.jpg"
        create_sample_image(img_name, item["color"], f"{item['facility'].name} - {item['severity']}")
        
        photo = Photo(
            report_id=report.id,
            file_path=img_name,
            public_path=f"pub_survey_{idx+1}.jpg",
            exif_lat=item["lat"],
            exif_lng=item["lng"],
            exif_taken_at=created_at,
            width=640,
            height=480,
            uploaded_at=created_at
        )
        db.add(photo)
        db.flush()
        
        # AI prediction
        ai_pred = AIPrediction(
            photo_id=photo.id,
            predicted_class=item["ai_class"],
            confidence=item["conf"],
            model_name="mobilenetv2_sig_blater",
            model_version="v1.0.0",
            created_at=created_at
        )
        db.add(ai_pred)
        
        # Initial status history
        hist = ReportStatusHistory(
            report_id=report.id,
            from_status_id=None,
            to_status_id=st_menunggu.id,
            changed_by=admin_user.id if admin_user else None,
            note="Laporan survei tim lapangan SIG dimasukkan ke sistem.",
            changed_at=created_at
        )
        db.add(hist)
        
        # Additional transition if status progressed
        if item["status"].code != "MENUNGGU_VERIFIKASI":
            hist2 = ReportStatusHistory(
                report_id=report.id,
                from_status_id=st_menunggu.id,
                to_status_id=item["status"].id,
                changed_by=admin_user.id if admin_user else None,
                note=f"Status diperbarui menjadi {item['status'].name}.",
                changed_at=created_at + timedelta(days=1)
            )
            db.add(hist2)
            
    db.commit()
    print(f"Successfully seeded {len(survey_points)} survey reports!")


if __name__ == "__main__":
    seed()
