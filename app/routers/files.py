from typing import List
from fastapi import APIRouter, Depends, UploadFile, File, Query, status
from sqlalchemy.orm import Session

from app.models.database import get_db
from app.models.schemas import (
    FileInfoResponse,
    FileMeasurementsResponse,
    FeatureCollectionGeoJSON,
)
from app.services.file_service import FileService

router = APIRouter(prefix="/files", tags=["Files & Measurements"])

@router.post(
    "/",
    response_model=FileInfoResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload and process geospatial file",
    description="Accepts a `.zip` archive containing a Shapefile or a `.kml` file. Extracts features, reprojects coordinates, and calculates measurements."
)
async def upload_file(
    file: UploadFile = File(..., description="Geospatial file (.zip Shapefile or .kml)"),
    db: Session = Depends(get_db)
):
    geo_file = await FileService.process_uploaded_file(file, db)
    return FileInfoResponse.model_validate(geo_file)

@router.get(
    "/{id}/",
    response_model=FileInfoResponse,
    summary="Get file information",
    description="Returns metadata about the uploaded file including status, feature count, and CRS."
)
def get_file_info(
    id: str,
    db: Session = Depends(get_db)
):
    return FileService.get_file_info(id, db)

@router.get(
    "/{id}/measurements/",
    response_model=FileMeasurementsResponse,
    summary="Get file measurements",
    description="Returns computed measurements (area for polygons, length for linestrings, not applicable for points) and summary metrics."
)
def get_file_measurements(
    id: str,
    db: Session = Depends(get_db)
):
    return FileService.get_measurements(id, db)

@router.get(
    "/{id}/features/",
    response_model=FeatureCollectionGeoJSON,
    summary="Get GeoJSON FeatureCollection",
    description="Returns the extracted features formatted as a GeoJSON FeatureCollection with attached measurement properties."
)
def get_file_features(
    id: str,
    db: Session = Depends(get_db)
):
    return FileService.get_features_geojson(id, db)

@router.get(
    "/",
    response_model=List[FileInfoResponse],
    summary="List all uploaded files",
    description="Returns a paginated list of all uploaded files with their statuses."
)
def list_files(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    return FileService.list_files(db, limit=limit, offset=offset)

@router.delete(
    "/{id}/",
    summary="Delete file",
    description="Deletes the uploaded file, extracted data, and database records."
)
def delete_file(
    id: str,
    db: Session = Depends(get_db)
):
    return FileService.delete_file(id, db)
