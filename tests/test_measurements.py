import pytest
from shapely.geometry import Polygon, MultiPolygon, LineString, MultiLineString, Point, GeometryCollection
from app.services.measurement_service import MeasurementService

def test_polygon_measurement():
    # Polygon near Delhi (Zone 43N)
    poly = Polygon([
        (77.100, 28.600),
        (77.105, 28.600),
        (77.105, 28.605),
        (77.100, 28.605),
        (77.100, 28.600)
    ])
    res = MeasurementService.calculate_measurements(poly, "EPSG:4326")
    
    assert res["status"] == "CALCULATED"
    assert res["geometry_type"] == "Polygon"
    assert res["area_sq_meters"] is not None and res["area_sq_meters"] > 0
    assert res["area_hectares"] is not None and res["area_hectares"] > 0
    assert res["area_sq_km"] is not None and res["area_sq_km"] > 0
    assert res["length_meters"] is not None and res["length_meters"] > 0
    assert "EPSG:32643" in res["projected_crs"] or "UTM" in res["projected_crs"]

def test_linestring_measurement():
    # LineString near Mumbai
    line = LineString([
        (72.850, 19.050),
        (72.860, 19.060),
        (72.870, 19.070)
    ])
    res = MeasurementService.calculate_measurements(line, "EPSG:4326")

    assert res["status"] == "CALCULATED"
    assert res["geometry_type"] == "LineString"
    assert res["area_sq_meters"] is None
    assert res["length_meters"] is not None and res["length_meters"] > 0
    assert res["length_km"] is not None and res["length_km"] > 0

def test_point_handling_no_measurement():
    pt = Point(77.100, 28.600)
    res = MeasurementService.calculate_measurements(pt, "EPSG:4326")

    assert res["status"] == "NOT_APPLICABLE"
    assert res["geometry_type"] == "Point"
    assert res["area_sq_meters"] is None
    assert res["length_meters"] is None
    assert "zero-dimensional" in res["notes"]

def test_unsupported_geometry_graceful():
    gc = GeometryCollection()
    res = MeasurementService.calculate_measurements(gc, "EPSG:4326")
    assert res["status"] == "UNSUPPORTED"
    assert res["area_sq_meters"] is None
    assert res["length_meters"] is None

def test_none_geometry_graceful():
    res = MeasurementService.calculate_measurements(None, "EPSG:4326")
    assert res["status"] == "UNSUPPORTED"
    assert res["area_sq_meters"] is None
