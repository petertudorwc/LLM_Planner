import React, { useEffect, useState } from 'react';
import { MapContainer, TileLayer, GeoJSON, useMap as useLeafletMap, Marker, Popup } from 'react-leaflet';
import { Box } from '@mui/material';
import L from 'leaflet';
import { mappingAPI } from '../services/api';
import { useMap } from '../contexts/MapContext';

// Fix for default marker icons in React-Leaflet
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: require('leaflet/dist/images/marker-icon-2x.png'),
  iconUrl: require('leaflet/dist/images/marker-icon.png'),
  shadowUrl: require('leaflet/dist/images/marker-shadow.png'),
});

// London coordinates
const DEFAULT_CENTER = [51.5074, -0.1278];
const DEFAULT_ZOOM = 11;

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

function MapView() {
  const [layers, setLayers] = useState([]);
  const [markers, setMarkers] = useState([]);
  const { mapUpdates } = useMap();

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
    <Box sx={{ height: '100%', width: '100%' }}>
      <MapContainer
        center={DEFAULT_CENTER}
        zoom={DEFAULT_ZOOM}
        style={{ height: '100%', width: '100%' }}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />

        {layers.map((layer) =>
          layer.data ? (
            <GeoJSON
              key={layer.id}
              data={layer.data}
              style={layer.style || { color: '#3388ff' }}
            />
          ) : null
        )}
        
        {/* Render markers from chat function calls */}
        {markers.map((marker, index) => (
          <Marker key={`chat-marker-${index}`} position={[marker.lat, marker.lon]}>
            <Popup>{marker.label || 'Point'}</Popup>
          </Marker>
        ))}

        <MapUpdater layers={layers} />
      </MapContainer>
    </Box>
  );
}

export default MapView;
