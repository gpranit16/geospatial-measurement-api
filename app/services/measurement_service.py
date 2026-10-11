import logging
from typing import Optional, Dict, Any
from shapely.geometry.base import BaseGeometry
import pyproj
from app.services.crs_service import CRSService

logger = logging.getLogger(__name__)

class MeasurementService:
    """
    Computes geometric measurements (Area, Length) on reprojected metric coordinates.
    Handles Polygon, MultiPolygon, LineString, MultiLineString, and gracefully
    handles Point, MultiPoint, GeometryCollection, and empty/invalid geometries.
    """

    POLYGON_TYPES = {"Polygon", "MultiPolygon"}
    LINESTRING_TYPES = {"LineString", "MultiLineString", "LinearRing"}
    POINT_TYPES = {"Point", "MultiPoint"}

    @classmethod
    def calculate_measurements(
        cls, 
        geometry: BaseGeometry, 
        source_crs_input: any
    ) -> Dict[str, Any]:
        """
        Calculates measurements for a single Shapely geometry.
        
        Returns a dictionary with:
        - status: "CALCULATED" | "NOT_APPLICABLE" | "UNSUPPORTED" | "ERROR"
        - geometry_type: str
        - projected_crs: str
        - area_sq_meters, area_hectares, area_sq_km
        - length_meters, length_km
        - notes: str
        - calculation_details: dict
        """
        if geometry is None or geometry.is_empty:
            return {
                "status": "UNSUPPORTED",
                "geometry_type": "None" if geometry is None else geometry.geom_type,
                "projected_crs": None,
                "area_sq_meters": None,
                "area_hectares": None,
                "area_sq_km": None,
                "length_meters": None,
                "length_km": None,
                "notes": "Empty or null geometry provided.",
                "calculation_details": {}
            }

        geom_type = geometry.geom_type

        # Point geometries: No measurement required by specifications
        if geom_type in cls.POINT_TYPES:
            return {
                "status": "NOT_APPLICABLE",
                "geometry_type": geom_type,
                "projected_crs": None,
                "area_sq_meters": None,
                "area_hectares": None,
                "area_sq_km": None,
                "length_meters": None,
                "length_km": None,
                "notes": f"{geom_type} is zero-dimensional; measurement not required.",
                "calculation_details": {
                    "dimensions": 0,
                    "coordinates": list(geometry.coords) if hasattr(geometry, "coords") else []
                }
            }

        # Check if geometry type is supported
        if geom_type not in cls.POLYGON_TYPES and geom_type not in cls.LINESTRING_TYPES:
            return {
                "status": "UNSUPPORTED",
                "geometry_type": geom_type,
                "projected_crs": None,
                "area_sq_meters": None,
                "area_hectares": None,
                "area_sq_km": None,
                "length_meters": None,
                "length_km": None,
                "notes": f"Geometry type '{geom_type}' is currently not supported for direct measurement.",
                "calculation_details": {}
            }

        try:
            # Transform geometry to metric projected coordinate system (e.g. UTM)
            proj_geom, target_crs, projection_desc = CRSService.transform_geometry_to_projected(
                geometry, source_crs_input
            )

            result = {
                "status": "CALCULATED",
                "geometry_type": geom_type,
                "projected_crs": target_crs.to_string(),
                "area_sq_meters": None,
                "area_hectares": None,
                "area_sq_km": None,
                "length_meters": None,
                "length_km": None,
                "notes": f"Projected using {projection_desc}.",
                "calculation_details": {
                    "projection_strategy": "Dynamic Local UTM Transformation",
                    "projected_crs_name": target_crs.name if hasattr(target_crs, "name") else str(target_crs),
                    "source_crs": str(source_crs_input)
                }
            }

            if geom_type in cls.POLYGON_TYPES:
                area_m2 = float(proj_geom.area)
                perimeter_m = float(proj_geom.length)
                
                result["area_sq_meters"] = round(area_m2, 4)
                result["area_hectares"] = round(area_m2 / 10000.0, 6)
                result["area_sq_km"] = round(area_m2 / 1_000_000.0, 8)
                result["length_meters"] = round(perimeter_m, 4)
                result["length_km"] = round(perimeter_m / 1000.0, 6)
                result["notes"] += f" Area: {result['area_sq_meters']:.2f} m² ({result['area_hectares']:.4f} ha). Perimeter: {result['length_meters']:.2f} m."

            elif geom_type in cls.LINESTRING_TYPES:
                length_m = float(proj_geom.length)
                
                result["area_sq_meters"] = None
                result["area_hectares"] = None
                result["area_sq_km"] = None
                result["length_meters"] = round(length_m, 4)
                result["length_km"] = round(length_m / 1000.0, 6)
                result["notes"] += f" Length: {result['length_meters']:.2f} m ({result['length_km']:.4f} km)."

            return result

        except Exception as e:
            logger.error(f"Error calculating measurement for {geom_type}: {e}", exc_info=True)
            return {
                "status": "ERROR",
                "geometry_type": geom_type,
                "projected_crs": None,
                "area_sq_meters": None,
                "area_hectares": None,
                "area_sq_km": None,
                "length_meters": None,
                "length_km": None,
                "notes": f"Calculation failed: {str(e)}",
                "calculation_details": {"error": str(e)}
            }
