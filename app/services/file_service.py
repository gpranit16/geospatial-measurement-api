import os
import uuid
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List, Dict, Any
from fastapi import UploadFile, HTTPException
from sqlalchemy.orm import Session
from shapely.geometry import mapping

from app.config import settings
from app.models.database import GeoFile, GeoFeature, GeoMeasurement
from app.services.parser_service import ParserService
from app.services.measurement_service import MeasurementService
from app.models.schemas import (
    FileInfoResponse,
    FileMeasurementsResponse,
    FeatureMeasurementItem,
    MeasurementValue,
    MeasurementSummary,
    FeatureCollectionGeoJSON,
    FeatureGeoJSON,
)

logger = logging.getLogger(__name__)

class FileService:

    @staticmethod
    def generate_file_id() -> str:
        return uuid.uuid4().hex[:12]

    @classmethod
    async def process_uploaded_file(cls, upload_file: UploadFile, db: Session) -> GeoFile:
        original_filename = upload_file.filename or "unknown"
        ext = Path(original_filename).suffix.lower()

        if ext not in settings.ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file extension '{ext}'. Allowed extensions: {', '.join(settings.ALLOWED_EXTENSIONS)}"
            )

        file_id = cls.generate_file_id()
        file_dir = settings.UPLOAD_DIR / file_id
        file_dir.mkdir(parents=True, exist_ok=True)
        saved_file_path = file_dir / original_filename

        content = await upload_file.read()
        file_size = len(content)

        if file_size > settings.MAX_FILE_SIZE_MB * 1024 * 1024:
            raise HTTPException(
                status_code=400,
                detail=f"File exceeds maximum allowed size of {settings.MAX_FILE_SIZE_MB}MB."
            )

        with open(saved_file_path, "wb") as f:
            f.write(content)

        file_type = "SHAPEFILE_ZIP" if ext == ".zip" else "KML"

        now_utc = datetime.now(timezone.utc)
        geo_file = GeoFile(
            id=file_id,
            filename=original_filename,
            file_type=file_type,
            file_size_bytes=file_size,
            file_path=str(saved_file_path),
            feature_count=0,
            crs=settings.DEFAULT_GEOGRAPHIC_CRS,
            status="PROCESSING",
            uploaded_at=now_utc
        )
        db.add(geo_file)
        db.commit()
        db.refresh(geo_file)

        try:
            detected_type, detected_crs, parsed_features = ParserService.parse_file(
                str(saved_file_path), original_filename
            )

            geo_file.crs = detected_crs
            geo_file.feature_count = len(parsed_features)

            for feat in parsed_features:
                geom_geojson_str = json.dumps(mapping(feat.geometry)) if feat.geometry else "{}"
                props_json_str = json.dumps(feat.properties or {}, default=str)

                geo_feature = GeoFeature(
                    file_id=geo_file.id,
                    feature_index=feat.index,
                    feature_identifier=feat.identifier,
                    geometry_type=feat.geometry_type,
                    geometry_json=geom_geojson_str,
                    properties_json=props_json_str,
                    source_crs=feat.crs or detected_crs
                )
                db.add(geo_feature)
                db.flush()

                # Calculate measurements
                m_result = MeasurementService.calculate_measurements(feat.geometry, feat.crs or detected_crs)

                geo_measurement = GeoMeasurement(
                    feature_id=geo_feature.id,
                    geometry_type=m_result["geometry_type"],
                    status=m_result["status"],
                    projected_crs=m_result["projected_crs"],
                    area_sq_meters=m_result["area_sq_meters"],
                    area_hectares=m_result["area_hectares"],
                    area_sq_km=m_result["area_sq_km"],
                    length_meters=m_result["length_meters"],
                    length_km=m_result["length_km"],
                    notes=m_result["notes"],
                    calculation_details_json=json.dumps(m_result.get("calculation_details", {}), default=str)
                )
                db.add(geo_measurement)

            geo_file.status = "COMPLETED"
            geo_file.processed_at = datetime.now(timezone.utc)
            db.commit()
            db.refresh(geo_file)
            return geo_file

        except Exception as e:
            logger.error(f"Error processing file {file_id}: {e}", exc_info=True)
            geo_file.status = "FAILED"
            geo_file.error_message = str(e)
            geo_file.processed_at = datetime.now(timezone.utc)
            db.commit()
            db.refresh(geo_file)
            raise HTTPException(status_code=422, detail=f"Failed to process geospatial file: {str(e)}")

    @classmethod
    def get_file_info(cls, file_id: str, db: Session) -> FileInfoResponse:
        geo_file = db.query(GeoFile).filter(GeoFile.id == file_id).first()
        if not geo_file:
            raise HTTPException(status_code=404, detail=f"File with ID '{file_id}' not found.")
        return FileInfoResponse.model_validate(geo_file)

    @classmethod
    def get_measurements(cls, file_id: str, db: Session) -> FileMeasurementsResponse:
        geo_file = db.query(GeoFile).filter(GeoFile.id == file_id).first()
        if not geo_file:
            raise HTTPException(status_code=404, detail=f"File with ID '{file_id}' not found.")

        features = (
            db.query(GeoFeature)
            .filter(GeoFeature.file_id == file_id)
            .order_by(GeoFeature.feature_index)
            .all()
        )

        items: List[FeatureMeasurementItem] = []
        breakdown: Dict[str, int] = {}
        total_poly_area_m2 = 0.0
        total_line_len_m = 0.0
        measured_count = 0
        na_count = 0
        unsupported_count = 0

        for f in features:
            m = f.measurement
            breakdown[f.geometry_type] = breakdown.get(f.geometry_type, 0) + 1

            props = {}
            if f.properties_json:
                try:
                    props = json.loads(f.properties_json)
                except Exception:
                    pass

            calc_details = {}
            if m and m.calculation_details_json:
                try:
                    calc_details = json.loads(m.calculation_details_json)
                except Exception:
                    pass

            m_val = MeasurementValue(
                area_sq_meters=m.area_sq_meters if m else None,
                area_hectares=m.area_hectares if m else None,
                area_sq_km=m.area_sq_km if m else None,
                length_meters=m.length_meters if m else None,
                length_km=m.length_km if m else None,
            )

            status = m.status if m else "ERROR"
            if status == "CALCULATED":
                measured_count += 1
                if m.area_sq_meters is not None:
                    total_poly_area_m2 += m.area_sq_meters
                if m.length_meters is not None and f.geometry_type in MeasurementService.LINESTRING_TYPES:
                    total_line_len_m += m.length_meters
            elif status == "NOT_APPLICABLE":
                na_count += 1
            else:
                unsupported_count += 1

            items.append(
                FeatureMeasurementItem(
                    feature_id=f.id,
                    feature_index=f.feature_index,
                    feature_identifier=f.feature_identifier,
                    geometry_type=f.geometry_type,
                    status=status,
                    source_crs=f.source_crs,
                    projected_crs=m.projected_crs if m else None,
                    measurements=m_val,
                    notes=m.notes if m else None,
                    properties=props,
                    calculation_details=calc_details
                )
            )

        summary = MeasurementSummary(
            total_features=len(features),
            features_measured=measured_count,
            features_not_applicable=na_count,
            features_unsupported=unsupported_count,
            geometry_type_breakdown=breakdown,
            total_polygon_area_sq_meters=round(total_poly_area_m2, 4),
            total_polygon_area_hectares=round(total_poly_area_m2 / 10000.0, 6),
            total_polygon_area_sq_km=round(total_poly_area_m2 / 1_000_000.0, 8),
            total_linestring_length_meters=round(total_line_len_m, 4),
            total_linestring_length_km=round(total_line_len_m / 1000.0, 6),
        )

        return FileMeasurementsResponse(
            file_id=geo_file.id,
            filename=geo_file.filename,
            crs=geo_file.crs,
            summary=summary,
            features=items
        )

    @classmethod
    def get_features_geojson(cls, file_id: str, db: Session) -> FeatureCollectionGeoJSON:
        geo_file = db.query(GeoFile).filter(GeoFile.id == file_id).first()
        if not geo_file:
            raise HTTPException(status_code=404, detail=f"File with ID '{file_id}' not found.")

        features = (
            db.query(GeoFeature)
            .filter(GeoFeature.file_id == file_id)
            .order_by(GeoFeature.feature_index)
            .all()
        )

        geojson_features = []
        for f in features:
            geom = {}
            if f.geometry_json:
                try:
                    geom = json.loads(f.geometry_json)
                except Exception:
                    pass

            props = {}
            if f.properties_json:
                try:
                    props = json.loads(f.properties_json)
                except Exception:
                    pass

            if f.measurement:
                m = f.measurement
                props["_measurement"] = {
                    "status": m.status,
                    "geometry_type": m.geometry_type,
                    "projected_crs": m.projected_crs,
                    "area_sq_meters": m.area_sq_meters,
                    "area_hectares": m.area_hectares,
                    "length_meters": m.length_meters,
                    "length_km": m.length_km,
                    "notes": m.notes
                }

            geojson_features.append(
                FeatureGeoJSON(
                    type="Feature",
                    id=f.id,
                    geometry=geom,
                    properties=props
                )
            )

        return FeatureCollectionGeoJSON(
            type="FeatureCollection",
            file_id=geo_file.id,
            filename=geo_file.filename,
            crs=geo_file.crs,
            features=geojson_features
        )

    @classmethod
    def list_files(cls, db: Session, limit: int = 50, offset: int = 0) -> List[FileInfoResponse]:
        files = db.query(GeoFile).order_by(GeoFile.uploaded_at.desc()).offset(offset).limit(limit).all()
        return [FileInfoResponse.model_validate(f) for f in files]

    @classmethod
    def delete_file(cls, file_id: str, db: Session) -> Dict[str, str]:
        geo_file = db.query(GeoFile).filter(GeoFile.id == file_id).first()
        if not geo_file:
            raise HTTPException(status_code=404, detail=f"File with ID '{file_id}' not found.")

        file_dir = settings.UPLOAD_DIR / file_id
        if file_dir.exists():
            import shutil
            shutil.rmtree(file_dir, ignore_errors=True)

        db.delete(geo_file)
        db.commit()
        return {"message": f"File '{file_id}' successfully deleted."}
