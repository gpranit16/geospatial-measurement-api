import json
from datetime import datetime
from sqlalchemy import create_engine, Column, String, Integer, Float, DateTime, Text, ForeignKey, JSON
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from app.config import settings

engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class GeoFile(Base):
    __tablename__ = "geo_files"

    id = Column(String(32), primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    file_type = Column(String(32), nullable=False)  # "SHAPEFILE_ZIP", "KML"
    file_size_bytes = Column(Integer, nullable=False, default=0)
    file_path = Column(String(512), nullable=False)
    feature_count = Column(Integer, nullable=False, default=0)
    crs = Column(String(128), nullable=False, default="EPSG:4326")
    status = Column(String(32), nullable=False, default="PENDING")  # PENDING, PROCESSING, COMPLETED, FAILED
    error_message = Column(Text, nullable=True)
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    processed_at = Column(DateTime, nullable=True)

    features = relationship("GeoFeature", back_populates="file", cascade="all, delete-orphan")

class GeoFeature(Base):
    __tablename__ = "geo_features"

    id = Column(Integer, primary_key=True, autoincrement=True)
    file_id = Column(String(32), ForeignKey("geo_files.id", ondelete="CASCADE"), nullable=False, index=True)
    feature_index = Column(Integer, nullable=False)
    feature_identifier = Column(String(128), nullable=True)  # Name or original ID if present
    geometry_type = Column(String(64), nullable=False)
    geometry_json = Column(Text, nullable=False)  # GeoJSON string
    properties_json = Column(Text, nullable=False, default="{}")
    source_crs = Column(String(128), nullable=False)

    file = relationship("GeoFile", back_populates="features")
    measurement = relationship("GeoMeasurement", back_populates="feature", uselist=False, cascade="all, delete-orphan")

class GeoMeasurement(Base):
    __tablename__ = "geo_measurements"

    id = Column(Integer, primary_key=True, autoincrement=True)
    feature_id = Column(Integer, ForeignKey("geo_features.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    geometry_type = Column(String(64), nullable=False)
    status = Column(String(32), nullable=False)  # "CALCULATED", "NOT_APPLICABLE", "UNSUPPORTED", "ERROR"
    projected_crs = Column(String(128), nullable=True)
    
    # Area measurements (Polygon / MultiPolygon)
    area_sq_meters = Column(Float, nullable=True)
    area_hectares = Column(Float, nullable=True)
    area_sq_km = Column(Float, nullable=True)
    
    # Length measurements (LineString / MultiLineString / Polygon perimeter)
    length_meters = Column(Float, nullable=True)
    length_km = Column(Float, nullable=True)
    
    notes = Column(Text, nullable=True)
    calculation_details_json = Column(Text, nullable=True)  # Additional metadata (e.g. centroid, geodesic comparison)

    feature = relationship("GeoFeature", back_populates="measurement")

def init_db():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
