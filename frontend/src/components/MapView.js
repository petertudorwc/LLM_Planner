import React, { useEffect, useState } from 'react';
import { MapContainer, TileLayer, GeoJSON, useMap as useLeafletMap, Marker, Popup, LayersControl, ImageOverlay } from 'react-leaflet';
import { Box, ToggleButton, ToggleButtonGroup, Paper, Typography, Button } from '@mui/material';
import { Add as AddIcon, Download as DownloadIcon } from '@mui/icons-material';
import L from 'leaflet';
import { mappingAPI } from '../services/api';
import { useMap } from '../contexts/MapContext';
import BNGGridOverlay from './BNGGridOverlay';
import CustomImageUpload from './CustomImageUpload';
import MapInfoDisplay from './MapInfoDisplay';
import { getMarkerIcon } from '../utils/markerIcons';

// Fix for default marker icons in React-Leaflet
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: require('leaflet/dist/images/marker-icon-2x.png'),
  iconUrl: require('leaflet/dist/images/marker-icon.png'),
  shadowUrl: require('leaflet/dist/images/marker-shadow.png'),
});

// Abingdon coordinates (more relevant for UK disaster relief)
const DEFAULT_CENTER = [51.6707, -1.2879]; // Abingdon - downloading tiles
const DEFAULT_ZOOM = 13;

// Coordinate conversion utilities
const BNG = {
  // Convert lat/lon to British National Grid (OSGB36)
  latLonToBNG: (lat, lon) => {
    // This is a simplified conversion - for production use a proper library like proj4js
    // For now, this is a placeholder that returns approximate values
    const a = 6377563.396; // Semi-major axis
    const b = 6356256.909; // Semi-minor axis
    const F0 = 0.9996012717; // Scale factor on central meridian
    const lat0 = 49 * Math.PI / 180; // Latitude of true origin
    const lon0 = -2 * Math.PI / 180; // Longitude of true origin
    const N0 = -100000; // Northing of true origin
    const E0 = 400000; // Easting of true origin
    
    // Convert to radians
    const φ = lat * Math.PI / 180;
    const λ = lon * Math.PI / 180;
    
    // Rough approximation (replace with proper proj4js library for accuracy)
    const easting = E0 + ((λ - lon0) * a * F0 * Math.cos(lat0) * 57295.78);
    const northing = N0 + ((φ - lat0) * a * F0 * 57295.78);
    
    return { easting: Math.round(easting), northing: Math.round(northing) };
  },
  
  // Convert BNG to lat/lon
  bngToLatLon: (easting, northing) => {
    // Simplified inverse - use proj4js for production
    const a = 6377563.396;
    const F0 = 0.9996012717;
    const lat0 = 49;
    const lon0 = -2;
    const N0 = -100000;
    const E0 = 400000;
    
    const lat = lat0 + ((northing - N0) / (a * F0 * 57295.78));
    const lon = lon0 + ((easting - E0) / (a * F0 * Math.cos(lat0 * Math.PI / 180) * 57295.78));
    
    return { lat, lon };
  },
  
  // Get grid reference from easting/northing
  toGridRef: (easting, northing, digits = 6) => {
    // 100km grid squares
    const letters = [
      ['SV', 'SW', 'SX', 'SY', 'SZ', 'TV', 'TW'],
      ['SQ', 'SR', 'SS', 'ST', 'SU', 'TQ', 'TR'],
      ['SL', 'SM', 'SN', 'SO', 'SP', 'TL', 'TM'],
      ['SF', 'SG', 'SH', 'SJ', 'SK', 'TF', 'TG'],
      ['SA', 'SB', 'SC', 'SD', 'SE', 'TA', 'TB'],
      ['NV', 'NW', 'NX', 'NY', 'NZ', 'OV', 'OW'],
      ['NQ', 'NR', 'NS', 'NT', 'NU', 'OQ', 'OR'],
      ['NL', 'NM', 'NN', 'NO', 'NP', 'OL', 'OM'],
      ['NF', 'NG', 'NH', 'NJ', 'NK', 'OF', 'OG'],
      ['NA', 'NB', 'NC', 'ND', 'NE', 'OA', 'OB'],
      ['HV', 'HW', 'HX', 'HY', 'HZ', 'JV', 'JW'],
      ['HQ', 'HR', 'HS', 'HT', 'HU', 'JQ', 'JR'],
      ['HL', 'HM', 'HN', 'HO', 'HP', 'JL', 'JM']
    ];
    
    const e100km = Math.floor(easting / 100000);
    const n100km = Math.floor(northing / 100000);
    
    if (e100km < 0 || e100km > 6 || n100km < 0 || n100km > 12) {
      return 'OUT OF RANGE';
    }
    
    const gridSquare = letters[12 - n100km][e100km];
    
    // Get easting and northing within the 100km square
    const e = Math.floor((easting % 100000) / Math.pow(10, 5 - digits / 2));
    const n = Math.floor((northing % 100000) / Math.pow(10, 5 - digits / 2));
    
    const eStr = e.toString().padStart(digits / 2, '0');
    const nStr = n.toString().padStart(digits / 2, '0');
    
    return `${gridSquare} ${eStr} ${nStr}`;
  }
};

function MapUpdater({ layers }) {
  const map = useLeafletMap();

  useEffect(() => {
    // Update map when layers change
    if (layers.length > 0) {
      const bounds = [];
      layers.forEach((layer) => {
        if (layer.data && layer.data.features) {
          layer.data.features.forEach((feature) => {
            if (feature.geometry.type === 'Point') {
              bounds.push(feature.geometry.coordinates.reverse());
            }
          });
        }
      });
      if (bounds.length > 0) {
        map.fitBounds(bounds);
      }
    }
  }, [layers, map]);

  return null;
}

// Track map position and update context
function MapPositionTracker() {
  const map = useLeafletMap();
  const { updateMapPosition } = useMap();

  useEffect(() => {
    const updatePosition = () => {
      const center = map.getCenter();
      const zoom = map.getZoom();
      const bounds = map.getBounds();
      
      updateMapPosition(
        [center.lat, center.lng],
        zoom,
        {
          north: bounds.getNorth(),
          south: bounds.getSouth(),
          east: bounds.getEast(),
          west: bounds.getWest(),
        }
      );
    };

    // Initial update
    updatePosition();

    // Listen to map events
    map.on('moveend', updatePosition);
    map.on('zoomend', updatePosition);

    return () => {
      map.off('moveend', updatePosition);
      map.off('zoomend', updatePosition);
    };
  }, [map, updateMapPosition]);

  return null;
}

function MapView({ onNavigateToDownload, developerMode }) {
  const [layers, setLayers] = useState([]);
  const [markers, setMarkers] = useState([]);
  const [baseLayer, setBaseLayer] = useState('osm'); // 'osm', 'satellite', 'custom'
  const [coordSystem, setCoordSystem] = useState('latlon'); // 'latlon' or 'bng'
  const [showGrid, setShowGrid] = useState(true);
  const [customImages, setCustomImages] = useState([]); // Array of {url, bounds, name}
  const [uploadDialogOpen, setUploadDialogOpen] = useState(false);
  const { mapUpdates } = useMap();

  const handleImageAdded = (imageData) => {
    setCustomImages([...customImages, imageData]);
    setBaseLayer('custom'); // Switch to custom layer
  };

  useEffect(() => {
    // Load initial layers
    loadLayers();

    // Poll for updates every 5 seconds
    const interval = setInterval(loadLayers, 5000);
    return () => clearInterval(interval);
  }, []);
  
  // Handle map updates from chat
  useEffect(() => {
    if (mapUpdates.length > 0) {
      const latestUpdate = mapUpdates[mapUpdates.length - 1];
      console.log('Received map update:', latestUpdate);
      
      // Add markers from chat function calls
      if (latestUpdate.points) {
        setMarkers(prev => [...prev, ...latestUpdate.points]);
      }
    }
  }, [mapUpdates]);

  const loadLayers = async () => {
    try {
      const response = await mappingAPI.getLayers();
      setLayers(response.data.layers || []);
    } catch (error) {
      console.error('Error loading layers:', error);
    }
  };

  return (
    <Box sx={{ height: '100%', width: '100%', position: 'relative' }}>
      {/* Map Controls */}
      <Paper
        sx={{
          position: 'absolute',
          top: 10,
          right: 10,
          zIndex: 1000,
          p: 2,
          display: 'flex',
          flexDirection: 'column',
          gap: 2,
        }}
      >
        <Box>
          <Typography variant="caption" sx={{ mb: 1, display: 'block' }}>
            Base Layer
          </Typography>
          <ToggleButtonGroup
            value={baseLayer}
            exclusive
            onChange={(e, newValue) => newValue && setBaseLayer(newValue)}
            size="small"
            orientation="vertical"
          >
            <ToggleButton value="osm">Street Map</ToggleButton>
            <ToggleButton value="satellite">Satellite</ToggleButton>
            <ToggleButton value="custom" disabled={customImages.length === 0}>
              Custom ({customImages.length})
            </ToggleButton>
          </ToggleButtonGroup>
          {developerMode && (
            <Button
              startIcon={<DownloadIcon />}
              size="small"
              onClick={onNavigateToDownload}
              sx={{ mt: 1, width: '100%' }}
              variant="outlined"
            >
              Download Tiles
            </Button>
          )}
          <Button
            startIcon={<AddIcon />}
            size="small"
            onClick={() => setUploadDialogOpen(true)}
            sx={{ mt: 1, width: '100%' }}
          >
            Add Image
          </Button>
        </Box>
        
        <Box>
          <Typography variant="caption" sx={{ mb: 1, display: 'block' }}>
            Coordinates
          </Typography>
          <ToggleButtonGroup
            value={coordSystem}
            exclusive
            onChange={(e, newValue) => newValue && setCoordSystem(newValue)}
            size="small"
            orientation="vertical"
          >
            <ToggleButton value="latlon">Lat/Lon</ToggleButton>
            <ToggleButton value="bng">BNG Grid</ToggleButton>
          </ToggleButtonGroup>
        </Box>
        
        <Box>
          <Typography variant="caption" sx={{ mb: 1, display: 'block' }}>
            Grid Overlay
          </Typography>
          <ToggleButtonGroup
            value={showGrid}
            exclusive
            onChange={(e, newValue) => setShowGrid(newValue)}
            size="small"
            orientation="vertical"
          >
            <ToggleButton value={true}>Show</ToggleButton>
            <ToggleButton value={false}>Hide</ToggleButton>
          </ToggleButtonGroup>
        </Box>
      </Paper>

      <CustomImageUpload
        open={uploadDialogOpen}
        onClose={() => setUploadDialogOpen(false)}
        onImageAdded={handleImageAdded}
      />

      <MapContainer
        center={DEFAULT_CENTER}
        zoom={DEFAULT_ZOOM}
        style={{ height: '100%', width: '100%' }}
      >
        {/* Base Layers */}
        {baseLayer === 'osm' && (
          <TileLayer
            attribution='&copy; OpenStreetMap contributors (offline cache)'
            url="http://localhost:8000/api/mapping/tiles/osm/{z}/{x}/{y}.png"
          />
        )}
        
        {baseLayer === 'satellite' && (
          <TileLayer
            attribution='Imagery &copy; Esri (offline cache)'
            url="http://localhost:8000/api/mapping/tiles/satellite/{z}/{x}/{y}.png"
            maxZoom={19}
          />
        )}
        
        {/* Custom Image Overlays */}
        {baseLayer === 'custom' && customImages.map((img, idx) => (
          <ImageOverlay
            key={`custom-${idx}`}
            url={img.url}
            bounds={img.bounds}
            opacity={0.8}
          />
        ))}

        {layers.map((layer) =>
          layer.data ? (
            <GeoJSON
              key={layer.id}
              data={layer.data}
              style={layer.style || { color: '#3388ff' }}
              pointToLayer={(feature, latlng) => {
                // Use custom marker icons based on marker_type property
                const markerType = feature.properties?.marker_type || 'default';
                const icon = getMarkerIcon(markerType);
                return L.marker(latlng, { icon });
              }}
              onEachFeature={(feature, layer) => {
                // Add popup with feature properties
                if (feature.properties) {
                  const props = feature.properties;
                  let popupContent = '';
                  
                  if (props.label) {
                    popupContent += `<strong>${props.label}</strong><br/>`;
                  }
                  
                  // Add other relevant properties
                  Object.keys(props).forEach(key => {
                    if (key !== 'label' && key !== 'marker_type' && props[key]) {
                      popupContent += `${key}: ${props[key]}<br/>`;
                    }
                  });
                  
                  if (popupContent) {
                    layer.bindPopup(popupContent);
                  }
                }
              }}
            />
          ) : null
        )}
        
        {/* Render markers from chat function calls */}
        {markers.map((marker, index) => (
          <Marker key={`chat-marker-${index}`} position={[marker.lat, marker.lon]}>
            <Popup>{marker.label || 'Point'}</Popup>
          </Marker>
        ))}

        {/* BNG Grid Overlay */}
        {showGrid && coordSystem === 'bng' && (
          <BNGGridOverlay visible={showGrid} gridSize={1000} coordSystem={coordSystem} />
        )}

        {/* Map Info Display */}
        <MapInfoDisplay baseLayer={baseLayer} coordSystem={coordSystem} />

        <MapUpdater layers={layers} />
        <MapPositionTracker />
      </MapContainer>
    </Box>
  );
}

export default MapView;
