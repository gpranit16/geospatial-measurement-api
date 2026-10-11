import os
from app.services.parser_service import ParserService

def test_parse_kml_file():
    kml_path = "sample_data/sample_parcels.kml"
    assert os.path.exists(kml_path), "Sample KML should exist"

    file_type, crs, features = ParserService.parse_file(kml_path, "sample_parcels.kml")

    assert file_type == "KML"
    assert "4326" in crs
    assert len(features) >= 4

    geom_types = [f.geometry_type for f in features]
    assert "Polygon" in geom_types
    assert "LineString" in geom_types
    assert "Point" in geom_types

def test_parse_shapefile_zip():
    zip_path = "sample_data/sample_shapefile.zip"
    assert os.path.exists(zip_path), "Sample shapefile zip should exist"

    file_type, crs, features = ParserService.parse_file(zip_path, "sample_shapefile.zip")

    assert file_type == "SHAPEFILE_ZIP"
    assert "4326" in crs
    assert len(features) == 2
    assert features[0].geometry_type == "Polygon"
    assert "name" in features[0].properties or "category" in features[0].properties

def test_unsupported_file_extension():
    import pytest
    with pytest.raises(ValueError, match="Unsupported file extension"):
        ParserService.parse_file("test.geojson", "test.geojson")
