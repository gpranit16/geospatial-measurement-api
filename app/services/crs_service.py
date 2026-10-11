import math
from typing import Tuple, Optional
import pyproj
from shapely.geometry.base import BaseGeometry
from shapely.ops import transform

class CRSService:
    """
    Handles coordinate reference system detection, validation, and dynamic
    projection transformations for accurate metric calculations.
    """

    @staticmethod
    def normalize_crs(crs_input: any) -> pyproj.CRS:
        """
        Parses and returns a valid pyproj.CRS object from various inputs:
        string, EPSG code, WKT, or existing pyproj/geopandas CRS.
        Defaults to EPSG:4326 if None or empty.
        """
        if crs_input is None:
            return pyproj.CRS.from_epsg(4326)
        
        try:
            if isinstance(crs_input, pyproj.CRS):
                return crs_input
            if isinstance(crs_input, int):
                return pyproj.CRS.from_epsg(crs_input)
            crs_str = str(crs_input).strip()
            if not crs_str:
                return pyproj.CRS.from_epsg(4326)
            return pyproj.CRS.from_user_input(crs_str)
        except Exception:
            # Fallback to WGS84 if parsing fails
            return pyproj.CRS.from_epsg(4326)

    @staticmethod
    def get_utm_epsg_for_coordinates(lon: float, lat: float) -> Tuple[int, str]:
        """
        Determines the optimal projected UTM (Universal Transverse Mercator) zone
        EPSG code based on longitude and latitude (WGS84).
        
        Returns:
            Tuple of (epsg_code, crs_name)
        """
        # Clamp latitude to polar regions if necessary
        if lat > 84.0:
            return 32661, "Universal Polar Stereographic (North)"
        if lat < -80.0:
            return 32761, "Universal Polar Stereographic (South)"

        # Standard UTM Zone calculation: 6-degree longitudinal strips
        # Zone 1 starts at -180 degrees.
        utm_zone = int(math.floor((lon + 180.0) / 6.0)) + 1
        utm_zone = max(1, min(60, utm_zone))

        if lat >= 0:
            epsg = 32600 + utm_zone
            name = f"WGS 84 / UTM zone {utm_zone}N (EPSG:{epsg})"
        else:
            epsg = 32700 + utm_zone
            name = f"WGS 84 / UTM zone {utm_zone}S (EPSG:{epsg})"

        return epsg, name

    @classmethod
    def get_appropriate_projected_crs(
        cls, 
        geometry: BaseGeometry, 
        source_crs: pyproj.CRS
    ) -> Tuple[pyproj.CRS, str]:
        """
        Chooses an appropriate projected metric coordinate reference system for a geometry.
        
        If the source CRS is already projected (units in meters), it can be used directly.
        If the source CRS is geographic (degrees), it reprojects to local UTM zone.
        """
        # If already projected and uses meters
        if source_crs.is_projected:
            axis_units = [axis.unit_name for axis in source_crs.axis_info]
            if any("metre" in u.lower() or "meter" in u.lower() for u in axis_units):
                return source_crs, f"Source Projected CRS ({source_crs.to_string()})"

        # Convert geometry centroid to EPSG:4326 to find long/lat
        wgs84 = pyproj.CRS.from_epsg(4326)
        if source_crs != wgs84:
            transformer_to_wgs84 = pyproj.Transformer.from_crs(source_crs, wgs84, always_xy=True)
            wgs84_geom = transform(transformer_to_wgs84.transform, geometry)
        else:
            wgs84_geom = geometry

        centroid = wgs84_geom.centroid
        lon, lat = centroid.x, centroid.y

        # Handle potential invalid centroid coordinates
        if math.isnan(lon) or math.isnan(lat):
            # Fallback to (0, 0)
            lon, lat = 0.0, 0.0

        epsg, name = cls.get_utm_epsg_for_coordinates(lon, lat)
        target_crs = pyproj.CRS.from_epsg(epsg)
        return target_crs, f"Dynamic UTM Projection: EPSG:{epsg} ({name})"

    @classmethod
    def transform_geometry_to_projected(
        cls, 
        geometry: BaseGeometry, 
        source_crs_input: any
    ) -> Tuple[BaseGeometry, pyproj.CRS, str]:
        """
        Transforms a geometry into an appropriate projected coordinate system (meters).
        
        Returns:
            Tuple of (projected_geometry, target_crs, projection_description)
        """
        source_crs = cls.normalize_crs(source_crs_input)
        target_crs, desc = cls.get_appropriate_projected_crs(geometry, source_crs)

        if source_crs == target_crs:
            return geometry, target_crs, desc

        transformer = pyproj.Transformer.from_crs(source_crs, target_crs, always_xy=True)
        projected_geom = transform(transformer.transform, geometry)

        return projected_geom, target_crs, desc
