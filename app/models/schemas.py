from typing import Any, Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field

class FileInfoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    filename: str
    file_type: str
    feature_count: int
    crs: str
    status: str
    uploaded_at: datetime
    processed_at: Optional[datetime] = None
    error_message: Optional[str] = None

class MeasurementValue(BaseModel):
    area_sq_meters: Optional[float] = None
    area_hectares: Optional[float] = None
    area_sq_km: Optional[float] = None
    length_meters: Optional[float] = None
    length_km: Optional[float] = None

class FeatureMeasurementItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    feature_id: int
    feature_index: int
    feature_identifier: Optional[str] = None
    geometry_type: str
    status: str  # CALCULATED, NOT_APPLICABLE, UNSUPPORTED, ERROR
    source_crs: str
    projected_crs: Optional[str] = None
    measurements: MeasurementValue
    notes: Optional[str] = None
    properties: dict[str, Any] = Field(default_factory=dict)
    calculation_details: Optional[dict[str, Any]] = None

class MeasurementSummary(BaseModel):
    total_features: int
    features_measured: int
    features_not_applicable: int
    features_unsupported: int
    geometry_type_breakdown: dict[str, int]
    total_polygon_area_sq_meters: float
    total_polygon_area_hectares: float
    total_polygon_area_sq_km: float
    total_linestring_length_meters: float
    total_linestring_length_km: float

class FileMeasurementsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    file_id: str
    filename: str
    crs: str
    summary: MeasurementSummary
    features: list[FeatureMeasurementItem]

class FeatureGeoJSON(BaseModel):
    type: str = "Feature"
    id: int
    geometry: dict[str, Any]
    properties: dict[str, Any]

class FeatureCollectionGeoJSON(BaseModel):
    type: str = "FeatureCollection"
    file_id: str
    filename: str
    crs: str
    features: list[FeatureGeoJSON]

class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    supported_formats: list[str]
    gdal_pyogrio_drivers: list[str]
