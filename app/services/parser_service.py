import os
import zipfile
import tempfile
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Tuple
import pandas as pd
import numpy as np
import geopandas as gpd
from shapely.geometry.base import BaseGeometry
import pyproj
from app.services.crs_service import CRSService

logger = logging.getLogger(__name__)

def sanitize_value(val: Any) -> Any:
    """
    Safely converts pandas, numpy, NaT, and custom types to standard JSON-serializable Python types.
    """
    if val is None:
        return None
    try:
        if pd.isna(val):
            return None
    except Exception:
        pass

    if isinstance(val, (pd.Timestamp, datetime)):
        return val.isoformat()
    if isinstance(val, (np.integer, int)):
        return int(val)
    if isinstance(val, (np.floating, float)):
        val_f = float(val)
        return None if np.isnan(val_f) or np.isinf(val_f) else val_f
    if isinstance(val, (np.bool_, bool)):
        return bool(val)
    if isinstance(val, np.ndarray):
        return [sanitize_value(x) for x in val.tolist()]
    if isinstance(val, (list, tuple)):
        return [sanitize_value(x) for x in val]
    if isinstance(val, dict):
        return {str(k): sanitize_value(v) for k, v in val.items()}
    if isinstance(val, (str, int, float, bool)):
        return val
    return str(val)

class FeatureData:
    def __init__(
        self,
        index: int,
        geometry: BaseGeometry,
        geometry_type: str,
        properties: Dict[str, Any],
        crs: str,
        identifier: str = None
    ):
        self.index = index
        self.geometry = geometry
        self.geometry_type = geometry_type
        self.properties = properties
        self.crs = crs
        self.identifier = identifier

class ParserService:
    """
    Parses geospatial files (Shapefile in .zip and KML), extracting features,
    geometries, attributes, and coordinate reference systems.
    """

    @classmethod
    def parse_file(cls, file_path: str, original_filename: str) -> Tuple[str, str, List[FeatureData]]:
        ext = Path(original_filename).suffix.lower()

        if ext == ".zip":
            return cls.parse_shapefile_zip(file_path)
        elif ext == ".kml":
            return cls.parse_kml(file_path)
        else:
            raise ValueError(f"Unsupported file extension '{ext}'. Only .zip and .kml are allowed.")

    @classmethod
    def parse_shapefile_zip(cls, zip_path: str) -> Tuple[str, str, List[FeatureData]]:
        extract_dir = tempfile.mkdtemp(prefix="shp_extract_")
        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                for member in zip_ref.infolist():
                    target_path = os.path.abspath(os.path.join(extract_dir, member.filename))
                    if not target_path.startswith(os.path.abspath(extract_dir)):
                        raise ValueError(f"Malicious archive entry detected: {member.filename}")
                zip_ref.extractall(extract_dir)

            shp_files = list(Path(extract_dir).rglob("*.shp"))
            if not shp_files:
                raise ValueError("No .shp file found inside the uploaded ZIP archive.")

            shp_file = shp_files[0]
            gdf = gpd.read_file(str(shp_file))

            crs_str = "EPSG:4326"
            if gdf.crs:
                try:
                    crs_str = gdf.crs.to_string()
                except Exception:
                    crs_str = str(gdf.crs)

            features = []
            for idx, row in gdf.iterrows():
                geom = row.geometry
                geom_type = geom.geom_type if geom else "None"
                
                props = {}
                for col in gdf.columns:
                    if col != gdf.geometry.name:
                        props[col] = sanitize_value(row[col])

                feat_id = str(props.get("id") or props.get("ID") or props.get("name") or props.get("Name") or f"feature_{idx}")

                features.append(
                    FeatureData(
                        index=int(idx),
                        geometry=geom,
                        geometry_type=geom_type,
                        properties=props,
                        crs=crs_str,
                        identifier=feat_id
                    )
                )

            return "SHAPEFILE_ZIP", crs_str, features

        finally:
            try:
                import shutil
                shutil.rmtree(extract_dir, ignore_errors=True)
            except Exception as e:
                logger.warning(f"Failed to cleanup temp dir {extract_dir}: {e}")

    @classmethod
    def parse_kml(cls, kml_path: str) -> Tuple[str, str, List[FeatureData]]:
        crs_str = "EPSG:4326"
        features: List[FeatureData] = []

        try:
            gdf = gpd.read_file(kml_path)
            if not gdf.empty:
                for idx, row in gdf.iterrows():
                    geom = row.geometry
                    geom_type = geom.geom_type if geom else "None"
                    props = {}
                    for col in gdf.columns:
                        if col != gdf.geometry.name:
                            props[col] = sanitize_value(row[col])

                    feat_id = str(props.get("Name") or props.get("name") or f"feature_{idx}")
                    features.append(
                        FeatureData(
                            index=int(idx),
                            geometry=geom,
                            geometry_type=geom_type,
                            properties=props,
                            crs=crs_str,
                            identifier=feat_id
                        )
                    )
                if features:
                    return "KML", crs_str, features
        except Exception as e:
            logger.info(f"GeoPandas KML read threw exception ({e}), falling back to direct XML parser...")

        features = cls._parse_kml_xml_fallback(kml_path)
        return "KML", crs_str, features

    @classmethod
    def _parse_kml_xml_fallback(cls, kml_path: str) -> List[FeatureData]:
        import xml.etree.ElementTree as ET
        from shapely.geometry import Polygon, LineString, Point

        tree = ET.parse(kml_path)
        root = tree.getroot()

        ns = ""
        if root.tag.startswith("{"):
            ns = root.tag.split("}")[0] + "}"

        features = []
        feature_index = 0

        for placemark in root.iter(f"{ns}Placemark"):
            name_elem = placemark.find(f"{ns}name")
            desc_elem = placemark.find(f"{ns}description")
            name = name_elem.text.strip() if name_elem is not None and name_elem.text else f"feature_{feature_index}"
            desc = desc_elem.text.strip() if desc_elem is not None and desc_elem.text else ""

            props = {"name": name}
            if desc:
                props["description"] = desc

            ext_data = placemark.find(f"{ns}ExtendedData")
            if ext_data is not None:
                for data in ext_data.iter(f"{ns}Data"):
                    data_name = data.get("name")
                    val_elem = data.find(f"{ns}value")
                    if data_name and val_elem is not None and val_elem.text:
                        props[data_name] = val_elem.text.strip()

            geom = None
            geom_type = "None"

            poly_elem = placemark.find(f".//{ns}Polygon")
            if poly_elem is not None:
                coords_elem = poly_elem.find(f".//{ns}coordinates")
                if coords_elem is not None and coords_elem.text:
                    coord_tuples = cls._parse_coords_str(coords_elem.text)
                    if len(coord_tuples) >= 3:
                        geom = Polygon(coord_tuples)
                        geom_type = "Polygon"

            if geom is None:
                line_elem = placemark.find(f".//{ns}LineString")
                if line_elem is not None:
                    coords_elem = line_elem.find(f".//{ns}coordinates")
                    if coords_elem is not None and coords_elem.text:
                        coord_tuples = cls._parse_coords_str(coords_elem.text)
                        if len(coord_tuples) >= 2:
                            geom = LineString(coord_tuples)
                            geom_type = "LineString"

            if geom is None:
                pt_elem = placemark.find(f".//{ns}Point")
                if pt_elem is not None:
                    coords_elem = pt_elem.find(f".//{ns}coordinates")
                    if coords_elem is not None and coords_elem.text:
                        coord_tuples = cls._parse_coords_str(coords_elem.text)
                        if coord_tuples:
                            geom = Point(coord_tuples[0])
                            geom_type = "Point"

            if geom is not None:
                features.append(
                    FeatureData(
                        index=feature_index,
                        geometry=geom,
                        geometry_type=geom_type,
                        properties=props,
                        crs="EPSG:4326",
                        identifier=name
                    )
                )
                feature_index += 1

        return features

    @staticmethod
    def _parse_coords_str(coords_str: str) -> List[Tuple[float, float]]:
        coords = []
        raw_parts = coords_str.strip().split()
        for part in raw_parts:
            part = part.strip()
            if not part:
                continue
            subparts = part.split(",")
            if len(subparts) >= 2:
                try:
                    lon = float(subparts[0])
                    lat = float(subparts[1])
                    coords.append((lon, lat))
                except ValueError:
                    continue
        return coords
