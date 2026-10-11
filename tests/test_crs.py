import pyproj
from shapely.geometry import Polygon, LineString, Point
from app.services.crs_service import CRSService

def test_utm_zone_calculation_northern_hemisphere():
    # New Delhi, India: ~77.2 deg Lon, ~28.6 deg Lat -> UTM Zone 43N (EPSG:32643)
    epsg, name = CRSService.get_utm_epsg_for_coordinates(77.2, 28.6)
    assert epsg == 32643
    assert "UTM zone 43N" in name

def test_utm_zone_calculation_southern_hemisphere():
    # Sydney, Australia: ~151.2 deg Lon, -33.8 deg Lat -> UTM Zone 56S (EPSG:32756)
    epsg, name = CRSService.get_utm_epsg_for_coordinates(151.2, -33.8)
    assert epsg == 32756
    assert "UTM zone 56S" in name

def test_utm_zone_calculation_western_hemisphere():
    # New York, USA: ~ -74.0 deg Lon, 40.7 deg Lat -> UTM Zone 18N (EPSG:32618)
    epsg, name = CRSService.get_utm_epsg_for_coordinates(-74.0, 40.7)
    assert epsg == 32618
    assert "UTM zone 18N" in name

def test_polar_regions_fallback():
    # North Pole (>84 lat)
    epsg, name = CRSService.get_utm_epsg_for_coordinates(0.0, 85.0)
    assert epsg == 32661
    # South Pole (<-80 lat)
    epsg, name = CRSService.get_utm_epsg_for_coordinates(0.0, -85.0)
    assert epsg == 32761

def test_normalize_crs():
    crs_4326 = CRSService.normalize_crs("EPSG:4326")
    assert crs_4326.to_epsg() == 4326

    crs_none = CRSService.normalize_crs(None)
    assert crs_none.to_epsg() == 4326

    crs_invalid = CRSService.normalize_crs("NON_EXISTENT_CRS")
    assert crs_invalid.to_epsg() == 4326

def test_reprojection_accuracy():
    # A small 0.001 x 0.001 degree square near Equator (0,0)
    poly = Polygon([(0.0, 0.0), (0.001, 0.0), (0.001, 0.001), (0.0, 0.001), (0.0, 0.0)])
    proj_geom, target_crs, desc = CRSService.transform_geometry_to_projected(poly, "EPSG:4326")
    
    assert target_crs.is_projected
    # 0.001 deg at equator is approx 111.3 meters. Square area approx 111.3 * 111.3 = ~12,390 m^2
    assert 12000 < proj_geom.area < 13000
