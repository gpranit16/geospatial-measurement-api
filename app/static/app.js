// Initialize Leaflet Map
const map = L.map('map', {
  zoomControl: false
}).setView([20.0, 77.0], 4);

L.control.zoom({ position: 'topright' }).addTo(map);

// Add Dark Theme CartoDB Tiles
L.tileLayer('https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png', {
  attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
  subdomains: 'abcd',
  maxZoom: 20
}).addTo(map);

let currentGeoJsonLayer = null;
let currentFeatureLayers = {};

// DOM Elements
const dropZone = document.getElementById('dropZone');
const fileInput = document.getElementById('fileInput');
const uploadLoader = document.getElementById('uploadLoader');
const uploadStatusText = document.getElementById('uploadStatusText');

const fileInfoCard = document.getElementById('fileInfoCard');
const metricSummaryCard = document.getElementById('metricSummaryCard');
const featuresListCard = document.getElementById('featuresListCard');

const metaFileId = document.getElementById('metaFileId');
const metaFeatureCount = document.getElementById('metaFeatureCount');
const metaSourceCrs = document.getElementById('metaSourceCrs');
const metaProjectedInfo = document.getElementById('metaProjectedInfo');
const currentFilename = document.getElementById('currentFilename');

const summaryTotalArea = document.getElementById('summaryTotalArea');
const summaryAreaSub = document.getElementById('summaryAreaSub');
const summaryTotalLength = document.getElementById('summaryTotalLength');
const summaryLengthSub = document.getElementById('summaryLengthSub');
const geometryBreakdown = document.getElementById('geometryBreakdown');
const featuresContainer = document.getElementById('featuresContainer');
const featuresCountBadge = document.getElementById('featuresCountBadge');

// Setup Drag & Drop
dropZone.addEventListener('click', () => fileInput.click());

['dragenter', 'dragover'].forEach(name => {
  dropZone.addEventListener(name, (e) => {
    e.preventDefault();
    dropZone.classList.add('dragover');
  });
});

['dragleave', 'drop'].forEach(name => {
  dropZone.addEventListener(name, (e) => {
    e.preventDefault();
    dropZone.classList.remove('dragover');
  });
});

dropZone.addEventListener('drop', (e) => {
  const files = e.dataTransfer.files;
  if (files.length > 0) {
    uploadFile(files[0]);
  }
});

fileInput.addEventListener('change', () => {
  if (fileInput.files.length > 0) {
    uploadFile(fileInput.files[0]);
  }
});

// Upload Function
async function uploadFile(file) {
  const formData = new FormData();
  formData.append('file', file);

  uploadLoader.classList.remove('hidden');
  uploadStatusText.textContent = `Uploading & Reprojecting ${file.name}...`;

  try {
    const res = await fetch('/api/files/', {
      method: 'POST',
      body: formData
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Upload failed');
    }

    const fileInfo = await res.json();
    uploadStatusText.textContent = 'Calculating measurements...';
    await loadFileData(fileInfo.id);

  } catch (err) {
    alert(`Error: ${err.message}`);
  } finally {
    uploadLoader.classList.add('hidden');
    fileInput.value = '';
  }
}

// Fetch and display measurements & GeoJSON
async function loadFileData(fileId) {
  try {
    const [infoRes, measRes, featRes] = await Promise.all([
      fetch(`/api/files/${fileId}/`),
      fetch(`/api/files/${fileId}/measurements/`),
      fetch(`/api/files/${fileId}/features/`)
    ]);

    const info = await infoRes.json();
    const measurements = await measRes.json();
    const geojsonData = await featRes.json();

    displayFileInfo(info);
    displayMeasurements(measurements);
    renderGeoJsonOnMap(geojsonData);
  } catch (err) {
    console.error('Failed to load file data:', err);
    alert('Failed to load file data: ' + err.message);
  }
}

function displayFileInfo(info) {
  fileInfoCard.classList.remove('hidden');
  currentFilename.textContent = info.filename;
  metaFileId.textContent = info.id;
  metaFeatureCount.textContent = info.feature_count;
  metaSourceCrs.textContent = info.crs || 'EPSG:4326';
}

function displayMeasurements(data) {
  metricSummaryCard.classList.remove('hidden');
  featuresListCard.classList.remove('hidden');

  const s = data.summary;
  summaryTotalArea.textContent = s.total_polygon_area_sq_meters > 0 ? `${s.total_polygon_area_sq_meters.toLocaleString()} m²` : '0 m²';
  summaryAreaSub.textContent = `${s.total_polygon_area_hectares.toFixed(4)} ha • ${s.total_polygon_area_sq_km.toFixed(6)} km²`;

  summaryTotalLength.textContent = s.total_linestring_length_meters > 0 ? `${s.total_linestring_length_meters.toLocaleString()} m` : '0 m';
  summaryLengthSub.textContent = `${s.total_linestring_length_km.toFixed(4)} km`;

  // Breakdown
  geometryBreakdown.innerHTML = '';
  for (const [geom, count] of Object.entries(s.geometry_type_breakdown)) {
    const chip = document.createElement('span');
    chip.className = 'breakdown-chip';
    chip.textContent = `${geom}: ${count}`;
    geometryBreakdown.appendChild(chip);
  }

  // Feature list
  featuresCountBadge.textContent = `${data.features.length} features`;
  featuresContainer.innerHTML = '';

  data.features.forEach(feat => {
    const item = document.createElement('div');
    item.className = 'feature-card';
    
    let measText = 'No measurement';
    if (feat.status === 'CALCULATED') {
      if (feat.measurements.area_sq_meters !== null) {
        measText = `Area: ${feat.measurements.area_sq_meters.toLocaleString()} m² (${feat.measurements.area_hectares} ha)`;
      } else if (feat.measurements.length_meters !== null) {
        measText = `Length: ${feat.measurements.length_meters.toLocaleString()} m (${feat.measurements.length_km} km)`;
      }
    } else if (feat.status === 'NOT_APPLICABLE') {
      measText = 'Point: Location only';
    } else {
      measText = feat.status;
    }

    const geomClass = feat.geometry_type.toLowerCase().includes('polygon') 
      ? 'tag-polygon' 
      : (feat.geometry_type.toLowerCase().includes('line') ? 'tag-linestring' : 'tag-point');

    item.innerHTML = `
      <div class="feature-card-header">
        <span class="feature-card-title">${feat.feature_identifier || `Feature #${feat.feature_index}`}</span>
        <span class="geom-type-tag ${geomClass}">${feat.geometry_type}</span>
      </div>
      <div class="feature-measurement-val">${measText}</div>
      <div class="feature-notes">${feat.projected_crs ? `Projected: ${feat.projected_crs}` : feat.source_crs}</div>
    `;

    item.addEventListener('click', () => {
      const layer = currentFeatureLayers[feat.feature_id];
      if (layer) {
        if (layer.getBounds) {
          map.fitBounds(layer.getBounds(), { padding: [50, 50], maxZoom: 16 });
        } else if (layer.getLatLng) {
          map.setView(layer.getLatLng(), 15);
        }
        layer.openPopup();
      }
    });

    featuresContainer.appendChild(item);
  });
}

function renderGeoJsonOnMap(geojson) {
  if (currentGeoJsonLayer) {
    map.removeLayer(currentGeoJsonLayer);
  }
  currentFeatureLayers = {};

  currentGeoJsonLayer = L.geoJSON(geojson, {
    style: (feature) => {
      const type = (feature.geometry.type || '').toLowerCase();
      if (type.includes('polygon')) {
        return {
          color: '#06b6d4',
          weight: 2,
          opacity: 0.9,
          fillColor: '#06b6d4',
          fillOpacity: 0.35
        };
      } else {
        return {
          color: '#8b5cf6',
          weight: 4,
          opacity: 0.9
        };
      }
    },
    pointToLayer: (feature, latlng) => {
      return L.circleMarker(latlng, {
        radius: 7,
        fillColor: '#f59e0b',
        color: '#ffffff',
        weight: 2,
        opacity: 1,
        fillOpacity: 0.9
      });
    },
    onEachFeature: (feature, layer) => {
      currentFeatureLayers[feature.id] = layer;

      const m = feature.properties._measurement || {};
      let statHtml = '';
      if (m.area_sq_meters !== undefined && m.area_sq_meters !== null) {
        statHtml = `<div class="popup-stat">Area: ${m.area_sq_meters.toLocaleString()} m²</div>
                    <div>${m.area_hectares} ha &bull; ${m.length_meters ? `${m.length_meters}m perimeter` : ''}</div>`;
      } else if (m.length_meters !== undefined && m.length_meters !== null) {
        statHtml = `<div class="popup-stat">Length: ${m.length_meters.toLocaleString()} m</div>
                    <div>${m.length_km} km</div>`;
      } else {
        statHtml = `<div>${m.notes || 'No measurement calculated'}</div>`;
      }

      const title = feature.properties.name || feature.properties.Name || `Feature #${feature.id}`;
      const proj = m.projected_crs ? `Projected CRS: ${m.projected_crs}` : '';

      layer.bindPopup(`
        <div class="popup-title">${title} (${m.geometry_type || feature.geometry.type})</div>
        ${statHtml}
        <div class="popup-proj" style="margin-top:6px;">${proj}</div>
      `);
    }
  }).addTo(map);

  if (currentGeoJsonLayer.getBounds().isValid()) {
    map.fitBounds(currentGeoJsonLayer.getBounds(), { padding: [40, 40] });
  }
}

// Sample buttons
document.getElementById('loadSampleKmlBtn')?.addEventListener('click', async () => {
  uploadLoader.classList.remove('hidden');
  uploadStatusText.textContent = 'Loading sample KML file...';
  try {
    const res = await fetch('/static/sample_data/sample_parcels.kml');
    const blob = await res.blob();
    const file = new File([blob], 'sample_parcels.kml');
    await uploadFile(file);
  } catch (e) {
    alert('Failed to load sample KML: ' + e.message);
  } finally {
    uploadLoader.classList.add('hidden');
  }
});

document.getElementById('loadSampleShpBtn')?.addEventListener('click', async () => {
  uploadLoader.classList.remove('hidden');
  uploadStatusText.textContent = 'Loading sample Shapefile...';
  try {
    const res = await fetch('/static/sample_data/sample_shapefile.zip');
    const blob = await res.blob();
    const file = new File([blob], 'sample_shapefile.zip');
    await uploadFile(file);
  } catch (e) {
    alert('Failed to load sample Shapefile: ' + e.message);
  } finally {
    uploadLoader.classList.add('hidden');
  }
});
