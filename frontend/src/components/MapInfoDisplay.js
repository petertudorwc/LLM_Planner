import React, { useState, useEffect } from 'react';
import { useMap } from 'react-leaflet';
import L from 'leaflet';
import './MapInfoDisplay.css';

const LAYER_NAMES = {
  'osm': 'OpenStreetMap',
  'satellite': 'Satellite Imagery',
  'custom': 'Custom Image'
};

function MapInfoDisplay({ baseLayer, coordSystem }) {
  const map = useMap();
  const [mousePos, setMousePos] = useState(null);
  const [center, setCenter] = useState(null);
  const [zoom, setZoom] = useState(null);
  const [bounds, setBounds] = useState(null);

  useEffect(() => {
    if (!map) return;

    // Create custom control
    const InfoControl = L.Control.extend({
      onAdd: function() {
        const div = L.DomUtil.create('div', 'map-info-display');
        div.id = 'map-info-display';
        return div;
      }
    });

    const infoControl = new InfoControl({ position: 'bottomleft' });
    map.addControl(infoControl);

    // Initialize values
    setCenter(map.getCenter());
    setZoom(map.getZoom());
    setBounds(map.getBounds());

    // Set up event listeners
    const onMouseMove = (e) => {
      setMousePos(e.latlng);
    };

    const onMoveEnd = () => {
      setCenter(map.getCenter());
      setBounds(map.getBounds());
    };

    const onZoomEnd = () => {
      setZoom(map.getZoom());
      setBounds(map.getBounds());
    };

    map.on('mousemove', onMouseMove);
    map.on('moveend', onMoveEnd);
    map.on('zoomend', onZoomEnd);

    return () => {
      map.off('mousemove', onMouseMove);
      map.off('moveend', onMoveEnd);
      map.off('zoomend', onZoomEnd);
      map.removeControl(infoControl);
    };
  }, [map]);

  const formatCoordinate = (lat, lon) => {
    if (coordSystem === 'bng') {
      // Simplified BNG conversion (use proper library for production)
      const a = 6377563.396;
      const F0 = 0.9996012717;
      const lat0 = 49;
      const lon0 = -2;
      const N0 = -100000;
      const E0 = 400000;
      
      const φ = lat * Math.PI / 180;
      const λ = lon * Math.PI / 180;
      const lat0Rad = lat0 * Math.PI / 180;
      const lon0Rad = lon0 * Math.PI / 180;
      
      const easting = Math.round(E0 + ((λ - lon0Rad) * a * F0 * Math.cos(lat0Rad) * 57295.78));
      const northing = Math.round(N0 + ((φ - lat0Rad) * a * F0 * 57295.78));
      
      return `E: ${easting.toLocaleString()}, N: ${northing.toLocaleString()}`;
    } else {
      return `${lat.toFixed(6)}°, ${lon.toFixed(6)}°`;
    }
  };

  // Update the DOM directly
  useEffect(() => {
    const div = document.getElementById('map-info-display');
    if (!div) return;

    div.innerHTML = `
      <div class="info-section">
        <span class="info-label">Active Layer:</span>
        <span class="info-value">${LAYER_NAMES[baseLayer] || baseLayer}</span>
      </div>
      <hr class="info-divider" />
      <div class="info-section">
        <span class="info-label">Zoom Level:</span>
        <span class="info-value">${zoom !== null ? zoom : '-'}</span>
      </div>
      <hr class="info-divider" />
      <div class="info-section">
        <span class="info-label">Map Center:</span>
        <span class="info-value">${center ? formatCoordinate(center.lat, center.lng) : '-'}</span>
      </div>
      <hr class="info-divider" />
      <div class="info-section">
        <span class="info-label">Cursor Position:</span>
        <span class="info-value">${mousePos ? formatCoordinate(mousePos.lat, mousePos.lng) : '-'}</span>
      </div>
      <hr class="info-divider" />
      <div class="info-section">
        <div class="info-label" style="display: block; margin-bottom: 4px;">Visible Bounds:</div>
        ${bounds ? `
          <div class="info-value" style="font-size: 11px;">
            North: ${bounds.getNorth().toFixed(6)}°<br/>
            South: ${bounds.getSouth().toFixed(6)}°<br/>
            East: ${bounds.getEast().toFixed(6)}°<br/>
            West: ${bounds.getWest().toFixed(6)}°
          </div>
        ` : '<span class="info-value">-</span>'}
      </div>
    `;
  }, [baseLayer, center, zoom, mousePos, bounds, coordSystem]);

  return null;
}

export default MapInfoDisplay;
