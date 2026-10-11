import os
from fastapi.testclient import TestClient

def test_health_check(client: TestClient):
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "Shapefile" in str(data["supported_formats"])

def test_upload_and_measure_kml(client: TestClient):
    kml_path = "sample_data/sample_parcels.kml"
    with open(kml_path, "rb") as f:
        response = client.post(
            "/api/files/",
            files={"file": ("sample_parcels.kml", f, "application/vnd.google-earth.kml+xml")}
        )
    
    assert response.status_code == 201
    file_info = response.json()
    file_id = file_info["id"]
    assert file_info["filename"] == "sample_parcels.kml"
    assert file_info["status"] == "COMPLETED"
    assert file_info["feature_count"] >= 4
    assert "4326" in file_info["crs"]

    # 1. Test GET /api/files/{id}/
    info_res = client.get(f"/api/files/{file_id}/")
    assert info_res.status_code == 200
    assert info_res.json()["id"] == file_id
    assert info_res.json()["status"] == "COMPLETED"

    # 2. Test GET /api/files/{id}/measurements/
    meas_res = client.get(f"/api/files/{file_id}/measurements/")
    assert meas_res.status_code == 200
    meas_data = meas_res.json()
    
    assert meas_data["file_id"] == file_id
    assert "summary" in meas_data
    summary = meas_data["summary"]
    assert summary["features_measured"] >= 2
    assert summary["total_polygon_area_sq_meters"] > 0
    assert summary["total_linestring_length_meters"] > 0
    assert "Polygon" in summary["geometry_type_breakdown"]

    # Features list assertions
    features = meas_data["features"]
    assert len(features) >= 4
    
    # Polygon feature check
    polys = [f for f in features if f["geometry_type"] == "Polygon"]
    assert len(polys) > 0
    assert polys[0]["status"] == "CALCULATED"
    assert polys[0]["measurements"]["area_sq_meters"] > 0
    assert polys[0]["projected_crs"] is not None

    # LineString feature check
    lines = [f for f in features if f["geometry_type"] == "LineString"]
    assert len(lines) > 0
    assert lines[0]["status"] == "CALCULATED"
    assert lines[0]["measurements"]["length_meters"] > 0
    assert lines[0]["measurements"]["area_sq_meters"] is None

    # Point feature check
    points = [f for f in features if f["geometry_type"] == "Point"]
    assert len(points) > 0
    assert points[0]["status"] == "NOT_APPLICABLE"
    assert points[0]["measurements"]["area_sq_meters"] is None

    # 3. Test GET /api/files/{id}/features/ (GeoJSON)
    feat_res = client.get(f"/api/files/{file_id}/features/")
    assert feat_res.status_code == 200
    geojson_data = feat_res.json()
    assert geojson_data["type"] == "FeatureCollection"
    assert len(geojson_data["features"]) >= 4

    # 4. Test GET /api/files/
    list_res = client.get("/api/files/")
    assert list_res.status_code == 200
    files_list = list_res.json()
    assert any(f["id"] == file_id for f in files_list)

    # 5. Test DELETE /api/files/{id}/
    del_res = client.delete(f"/api/files/{file_id}/")
    assert del_res.status_code == 200

    # Verify deleted
    not_found = client.get(f"/api/files/{file_id}/")
    assert not_found.status_code == 404

def test_upload_and_measure_shapefile_zip(client: TestClient):
    zip_path = "sample_data/sample_shapefile.zip"
    with open(zip_path, "rb") as f:
        response = client.post(
            "/api/files/",
            files={"file": ("sample_shapefile.zip", f, "application/zip")}
        )
    
    assert response.status_code == 201
    file_info = response.json()
    file_id = file_info["id"]
    assert file_info["status"] == "COMPLETED"
    assert file_info["feature_count"] == 2

    # Verify measurements
    meas_res = client.get(f"/api/files/{file_id}/measurements/")
    assert meas_res.status_code == 200
    meas_data = meas_res.json()
    assert meas_data["summary"]["total_polygon_area_sq_meters"] > 0

def test_invalid_extension_rejected(client: TestClient):
    response = client.post(
        "/api/files/",
        files={"file": ("test.txt", b"plain text", "text/plain")}
    )
    assert response.status_code == 400
    assert "Invalid file extension" in response.json()["detail"]

def test_nonexistent_file_returns_404(client: TestClient):
    res = client.get("/api/files/nonexistent_123/")
    assert res.status_code == 404
