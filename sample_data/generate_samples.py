import os
import shutil
import zipfile
import geopandas as gpd
from shapely.geometry import Polygon, LineString, Point

os.makedirs("sample_data", exist_ok=True)
os.makedirs("app/static/sample_data", exist_ok=True)

# 1. Generate KML Sample
kml_content = """<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <name>Sample Geospatial Survey Survey</name>
    <description>Parcels, Transmission Lines, and Survey Waypoints</description>
    
    <!-- Polygon 1: Solar Park Parcel -->
    <Placemark>
      <name>Solar Park Boundary A</name>
      <description>Phase 1 Solar Array Parcel</description>
      <ExtendedData>
        <Data name="land_use"><value>Renewable Energy</value></Data>
        <Data name="surveyor"><value>Antigravity Geo</value></Data>
      </ExtendedData>
      <Polygon>
        <extrude>1</extrude>
        <altitudeMode>relativeToGround</altitudeMode>
        <outerBoundaryIs>
          <LinearRing>
            <coordinates>
              77.100,28.600,0
              77.105,28.600,0
              77.105,28.605,0
              77.100,28.605,0
              77.100,28.600,0
            </coordinates>
          </LinearRing>
        </outerBoundaryIs>
      </Polygon>
    </Placemark>

    <!-- Polygon 2: Agricultural Field -->
    <Placemark>
      <name>Agricultural Field B</name>
      <description>Paddy Field Zone</description>
      <ExtendedData>
        <Data name="crop"><value>Wheat</value></Data>
      </ExtendedData>
      <Polygon>
        <outerBoundaryIs>
          <LinearRing>
            <coordinates>
              77.110,28.610,0
              77.118,28.610,0
              77.115,28.618,0
              77.110,28.615,0
              77.110,28.610,0
            </coordinates>
          </LinearRing>
        </outerBoundaryIs>
      </Polygon>
    </Placemark>

    <!-- LineString 1: Transmission Line -->
    <Placemark>
      <name>High Voltage Line 400kV</name>
      <description>Main Transmission Corridor</description>
      <ExtendedData>
        <Data name="voltage_kv"><value>400</value></Data>
      </ExtendedData>
      <LineString>
        <coordinates>
          77.100,28.600,0
          77.108,28.607,0
          77.115,28.612,0
          77.125,28.620,0
        </coordinates>
      </LineString>
    </Placemark>

    <!-- LineString 2: Access Road -->
    <Placemark>
      <name>Site Access Road</name>
      <description>Asphalt 2-lane road</description>
      <LineString>
        <coordinates>
          77.095,28.595,0
          77.100,28.600,0
          77.110,28.602,0
        </coordinates>
      </LineString>
    </Placemark>

    <!-- Point 1: Geodetic Benchmark -->
    <Placemark>
      <name>Geodetic Control Point 01</name>
      <description>GPS Reference Benchmark</description>
      <Point>
        <coordinates>77.100,28.600,0</coordinates>
      </Point>
    </Placemark>

    <!-- Point 2: Substation Center -->
    <Placemark>
      <name>Substation Landmark</name>
      <Point>
        <coordinates>77.105,28.605,0</coordinates>
      </Point>
    </Placemark>

  </Document>
</kml>
"""

with open("sample_data/sample_parcels.kml", "w", encoding="utf-8") as f:
    f.write(kml_content)

with open("app/static/sample_data/sample_parcels.kml", "w", encoding="utf-8") as f:
    f.write(kml_content)

print("KML sample generated.")

# 2. Generate Shapefile Sample
records = [
    {
        "id": "POLY_001",
        "name": "Industrial Park Zone A",
        "category": "Industrial",
        "geometry": Polygon([
            (72.850, 19.050),
            (72.860, 19.050),
            (72.860, 19.060),
            (72.850, 19.060),
            (72.850, 19.050)
        ])
    },
    {
        "id": "POLY_002",
        "name": "Commercial Tech Park",
        "category": "Commercial",
        "geometry": Polygon([
            (72.865, 19.055),
            (72.875, 19.055),
            (72.872, 19.065),
            (72.863, 19.062),
            (72.865, 19.055)
        ])
    },
    {
        "id": "LINE_001",
        "name": "Metro Transit Corridor",
        "category": "Transit",
        "geometry": LineString([
            (72.845, 19.040),
            (72.855, 19.052),
            (72.865, 19.060),
            (72.875, 19.070)
        ])
    },
    {
        "id": "PT_001",
        "name": "Central Transit Station",
        "category": "Infrastructure",
        "geometry": Point(72.855, 19.052)
    }
]

# Note: ESRI Shapefiles support single geometry type per file natively (or generic).
# For shapefile, let's create a polygon shapefile and a linestring shapefile in a zip!
poly_records = [
    {
        "id": "POLY_001",
        "name": "Industrial Park Zone A",
        "category": "Industrial",
        "geometry": Polygon([
            (72.850, 19.050),
            (72.860, 19.050),
            (72.860, 19.060),
            (72.850, 19.060),
            (72.850, 19.050)
        ])
    },
    {
        "id": "POLY_002",
        "name": "Commercial Tech Park",
        "category": "Commercial",
        "geometry": Polygon([
            (72.865, 19.055),
            (72.875, 19.055),
            (72.872, 19.065),
            (72.863, 19.062),
            (72.865, 19.055)
        ])
    }
]

gdf_poly = gpd.GeoDataFrame(poly_records, crs="EPSG:4326")
shp_dir = "sample_data/temp_shp"
os.makedirs(shp_dir, exist_ok=True)
gdf_poly.to_file(os.path.join(shp_dir, "survey_parcels.shp"))

# Zip the shapefile
zip_path = "sample_data/sample_shapefile.zip"
with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
    for file in os.listdir(shp_dir):
        zipf.write(os.path.join(shp_dir, file), arcname=file)

# Copy to static for UI
shutil.copyfile(zip_path, "app/static/sample_data/sample_shapefile.zip")
shutil.rmtree(shp_dir, ignore_errors=True)

print("Shapefile sample generated successfully.")
