import datetime
from sqlalchemy import (
    create_engine, Column, Integer, String, Text, Float, 
    Boolean, DateTime, ForeignKey, Index, JSON
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker, scoped_session
from werkzeug.security import generate_password_hash, check_password_hash
from config import Config

Base = declarative_base()

# Database engine & session factory
engine = create_engine(Config.DATABASE_URL, pool_pre_ping=True)
db_session = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))
Base.query = db_session.query_property()


class FacilityType(Base):
    __tablename__ = "facility_types"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(20), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    
    reports = relationship("Report", back_populates="facility_type", foreign_keys="Report.facility_type_id")
    
    def to_dict(self):
        return {
            "id": self.id,
            "code": self.code,
            "name": self.name,
            "is_active": self.is_active
        }


class ReportStatus(Base):
    __tablename__ = "report_status"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(30), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    sort_order = Column(Integer, default=1, nullable=False)
    
    reports = relationship("Report", back_populates="status")
    
    def to_dict(self):
        return {
            "id": self.id,
            "code": self.code,
            "name": self.name,
            "sort_order": self.sort_order
        }


class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(150), nullable=False)
    email = Column(String(150), unique=True, nullable=True, index=True)
    phone = Column(String(30), nullable=True)
    password_hash = Column(String(255), nullable=True)
    role = Column(String(20), default="warga", nullable=False)  # warga, pengelola, admin
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    
    reports = relationship("Report", back_populates="reporter")
    
    def set_password(self, password: str):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password: str) -> bool:
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)
        
    def to_dict(self, include_sensitive=False):
        data = {
            "id": self.id,
            "name": self.name,
            "role": self.role,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
        if include_sensitive:
            data["email"] = self.email
            data["phone"] = self.phone
        return data


class Report(Base):
    __tablename__ = "reports"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    reporter_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    facility_type_id = Column(Integer, ForeignKey("facility_types.id"), nullable=False, index=True)
    ai_category_id = Column(Integer, ForeignKey("facility_types.id"), nullable=True)
    status_id = Column(Integer, ForeignKey("report_status.id"), nullable=False, index=True)
    severity = Column(String(20), nullable=True)  # ringan, sedang, berat
    description = Column(Text, nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    location_source = Column(String(20), default="manual_map", nullable=False)  # exif, device_gps, manual_map
    source_type = Column(String(20), default="warga", nullable=False)  # warga, survei_tim
    is_duplicate_of = Column(Integer, ForeignKey("reports.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow, nullable=False)
    
    # Relationships
    reporter = relationship("User", back_populates="reports")
    facility_type = relationship("FacilityType", foreign_keys=[facility_type_id])
    ai_category = relationship("FacilityType", foreign_keys=[ai_category_id])
    status = relationship("ReportStatus", back_populates="reports")
    photos = relationship("Photo", back_populates="report", cascade="all, delete-orphan")
    status_history = relationship("ReportStatusHistory", back_populates="report", cascade="all, delete-orphan", order_by="ReportStatusHistory.changed_at.desc()")
    
    __table_args__ = (
        Index("idx_reports_coords", "latitude", "longitude"),
        Index("idx_reports_status_fac", "status_id", "facility_type_id"),
    )
    
    def to_dict(self, is_admin_or_officer=False):
        primary_photo = self.photos[0] if self.photos else None
        photo_url = None
        if primary_photo:
            photo_url = f"/uploads/photos/original/{primary_photo.file_path}" if is_admin_or_officer else f"/uploads/photos/public/{primary_photo.public_path}"
            
        data = {
            "id": self.id,
            "facility_type": self.facility_type.to_dict() if self.facility_type else None,
            "ai_category": self.ai_category.to_dict() if self.ai_category else None,
            "status": self.status.to_dict() if self.status else None,
            "severity": self.severity,
            "description": self.description,
            "location": {
                "lat": self.latitude,
                "lng": self.longitude
            },
            "location_source": self.location_source,
            "source_type": self.source_type,
            "is_duplicate_of": self.is_duplicate_of,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "photo_url": photo_url,
            "photos": [p.to_dict(is_admin_or_officer) for p in self.photos]
        }
        
        if is_admin_or_officer and self.reporter:
            data["reporter"] = self.reporter.to_dict(include_sensitive=True)
        else:
            data["reporter"] = {"id": self.reporter_id, "name": "Anonim"} if not self.reporter else {"name": self.reporter.name}
            
        return data


class Photo(Base):
    __tablename__ = "photos"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    report_id = Column(Integer, ForeignKey("reports.id", ondelete="CASCADE"), nullable=False, index=True)
    file_path = Column(String(255), nullable=False)
    public_path = Column(String(255), nullable=False)
    exif_lat = Column(Float, nullable=True)
    exif_lng = Column(Float, nullable=True)
    exif_taken_at = Column(DateTime, nullable=True)
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    uploaded_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    
    report = relationship("Report", back_populates="photos")
    ai_predictions = relationship("AIPrediction", back_populates="photo", cascade="all, delete-orphan")
    
    def to_dict(self, is_admin_or_officer=False):
        return {
            "id": self.id,
            "report_id": self.report_id,
            "file_url": f"/uploads/photos/original/{self.file_path}" if is_admin_or_officer else f"/uploads/photos/public/{self.public_path}",
            "exif_lat": self.exif_lat if is_admin_or_officer else None,
            "exif_lng": self.exif_lng if is_admin_or_officer else None,
            "exif_taken_at": self.exif_taken_at.isoformat() if self.exif_taken_at and is_admin_or_officer else None,
            "width": self.width,
            "height": self.height,
            "ai_predictions": [p.to_dict() for p in self.ai_predictions]
        }


class AIPrediction(Base):
    __tablename__ = "ai_predictions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    photo_id = Column(Integer, ForeignKey("photos.id", ondelete="CASCADE"), nullable=False, index=True)
    predicted_class = Column(String(30), nullable=False)  # JALAN_RUSAK, PJU_RUSAK, DRAINASE_TERSUMBAT, KONDISI_NORMAL
    confidence = Column(Float, nullable=False)
    model_name = Column(String(50), default="mobilenetv2_ensemble", nullable=False)
    model_version = Column(String(30), default="v1.0.0", nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    
    photo = relationship("Photo", back_populates="ai_predictions")
    
    def to_dict(self):
        return {
            "id": self.id,
            "photo_id": self.photo_id,
            "predicted_class": self.predicted_class,
            "confidence": round(float(self.confidence), 4),
            "model_name": self.model_name,
            "model_version": self.model_version,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class ReportStatusHistory(Base):
    __tablename__ = "report_status_history"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    report_id = Column(Integer, ForeignKey("reports.id", ondelete="CASCADE"), nullable=False, index=True)
    from_status_id = Column(Integer, ForeignKey("report_status.id"), nullable=True)
    to_status_id = Column(Integer, ForeignKey("report_status.id"), nullable=False)
    changed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    note = Column(Text, nullable=True)
    changed_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    
    report = relationship("Report", back_populates="status_history")
    from_status = relationship("ReportStatus", foreign_keys=[from_status_id])
    to_status = relationship("ReportStatus", foreign_keys=[to_status_id])
    user = relationship("User", foreign_keys=[changed_by])
    
    def to_dict(self):
        return {
            "id": self.id,
            "report_id": self.report_id,
            "from_status": self.from_status.name if self.from_status else None,
            "to_status": self.to_status.name if self.to_status else None,
            "changed_by": self.user.name if self.user else "Sistem",
            "note": self.note,
            "changed_at": self.changed_at.isoformat() if self.changed_at else None
        }


class SystemParameter(Base):
    __tablename__ = "system_parameters"
    
    key = Column(String(50), primary_key=True)
    value = Column(JSON, nullable=False)
    description = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    def to_dict(self):
        return {
            "key": self.key,
            "value": self.value,
            "description": self.description,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


class SpatialAnalysisResult(Base):
    __tablename__ = "spatial_analysis_results"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    analysis_type = Column(String(50), nullable=False, index=True)  # kde, dbscan, getis_ord, priorities
    result_data = Column(JSON, nullable=False)
    calculated_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    
    def to_dict(self):
        return {
            "id": self.id,
            "analysis_type": self.analysis_type,
            "result_data": self.result_data,
            "calculated_at": self.calculated_at.isoformat() if self.calculated_at else None
        }


def init_db():
    """Initializes database tables, creates upload folders, and seeds default records."""
    # Ensure directories
    Config.UPLOAD_FOLDER_ORIGINAL.mkdir(parents=True, exist_ok=True)
    Config.UPLOAD_FOLDER_PUBLIC.mkdir(parents=True, exist_ok=True)
    
    # Create tables
    Base.metadata.create_all(bind=engine)
    session = db_session()
    
    try:
        # Seed facility_types
        if session.query(FacilityType).count() == 0:
            types = [
                FacilityType(code="JALAN", name="Jalan (Berlubang/Amblas/Retak)", is_active=True),
                FacilityType(code="PJU", name="PJU (Penerangan Jalan Umum)", is_active=True),
                FacilityType(code="DRAINASE", name="Drainase (Tersumbat/Tanggul Rusak)", is_active=True)
            ]
            session.add_all(types)
            session.commit()
            
        # Seed report_status
        if session.query(ReportStatus).count() == 0:
            statuses = [
                ReportStatus(code="MENUNGGU_VERIFIKASI", name="Menunggu Verifikasi", sort_order=1),
                ReportStatus(code="DIVERIFIKASI", name="Diverifikasi", sort_order=2),
                ReportStatus(code="DIPROSES", name="Sedang Diproses", sort_order=3),
                ReportStatus(code="SELESAI", name="Selesai", sort_order=4)
            ]
            session.add_all(statuses)
            session.commit()
            
        # Seed default users (Admin & Pengelola)
        if session.query(User).filter_by(role="admin").count() == 0:
            admin = User(
                name="Admin Blater",
                email="admin@blater.desa.id",
                phone="081234567890",
                role="admin"
            )
            admin.set_password("admin123")
            session.add(admin)
            
        if session.query(User).filter_by(role="pengelola").count() == 0:
            officer = User(
                name="Perangkat Desa Blater",
                email="petugas@blater.desa.id",
                phone="081298765432",
                role="pengelola"
            )
            officer.set_password("petugas123")
            session.add(officer)
        session.commit()
        
        # Seed system_parameters
        default_params = [
            ("priority_weights", {
                "severity": 0.35,
                "density": 0.30,
                "safety_risk": 0.20,
                "unhandled_duration": 0.15
            }, "Bobot kriteria perhitungan skor prioritas penanganan"),
            ("dbscan_params", {
                "eps_meters": Config.DEFAULT_DBSCAN_EPS_METERS,
                "min_pts": Config.DEFAULT_DBSCAN_MIN_PTS
            }, "Parameter klaster DBSCAN (eps dalam meter, minPts)"),
            ("kde_params", {
                "bandwidth_meters": Config.DEFAULT_KDE_BANDWIDTH_METERS
            }, "Bandwidth kernel density estimation (meter)"),
            ("ai_params", {
                "confidence_threshold": Config.AI_CONFIDENCE_THRESHOLD
            }, "Ambang keyakinan model AI untuk saran kategori"),
            ("duplicate_params", {
                "radius_meters": Config.DUPLICATE_RADIUS_METERS
            }, "Radius deteksi laporan ganda dalam meter")
        ]
        
        for k, v, desc in default_params:
            if not session.query(SystemParameter).filter_by(key=k).first():
                session.add(SystemParameter(key=k, value=v, description=desc))
        session.commit()
        
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()
