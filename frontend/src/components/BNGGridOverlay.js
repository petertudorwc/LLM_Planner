import { useEffect } from 'react';
import { useMap } from 'react-leaflet';
import L from 'leaflet';

const BNGGridOverlay = ({ visible = true, gridSize = 1000, coordSystem = 'latlon' }) => {
  const map = useMap();

  useEffect(() => {
    if (!visible) {
      // Remove existing grid layers
      map.eachLayer((layer) => {
        if (layer.options && layer.options.gridLayer) {
          map.removeLayer(layer);
        }
      });
      return;
    }

    // Function to convert lat/lon to approximate BNG (simplified)
    const latLonToBNG = (lat, lon) => {
      const a = 6377563.396;
      const F0 = 0.9996012717;
      const lat0 = 49 * Math.PI / 180;
      const lon0 = -2 * Math.PI / 180;
      const N0 = -100000;
      const E0 = 400000;
      
      const φ = lat * Math.PI / 180;
      const λ = lon * Math.PI / 180;
      
      const easting = E0 + ((λ - lon0) * a * F0 * Math.cos(lat0) * 57295.78);
      const northing = N0 + ((φ - lat0) * a * F0 * 57295.78);
      
      return { easting: Math.round(easting), northing: Math.round(northing) };
    };

    const bngToLatLon = (easting, northing) => {
      const a = 6377563.396;
      const F0 = 0.9996012717;
      const lat0 = 49;
      const lon0 = -2;
      const N0 = -100000;
      const E0 = 400000;
      
      const lat = lat0 + ((northing - N0) / (a * F0 * 57295.78));
      const lon = lon0 + ((easting - E0) / (a * F0 * Math.cos(lat0 * Math.PI / 180) * 57295.78));
      
      return [lat, lon];
    };

    // Function to draw grid
    const drawGrid = () => {
      // Remove existing grid layers
      map.eachLayer((layer) => {
        if (layer.options && layer.options.gridLayer) {
          map.removeLayer(layer);
        }
      });

      const bounds = map.getBounds();
      const sw = bounds.getSouthWest();
      const ne = bounds.getNorthEast();

      // Convert corners to BNG
      const swBNG = latLonToBNG(sw.lat, sw.lng);
      const neBNG = latLonToBNG(ne.lat, ne.lng);

      // Round to nearest grid lines
      const minEasting = Math.floor(swBNG.easting / gridSize) * gridSize;
      const maxEasting = Math.ceil(neBNG.easting / gridSize) * gridSize;
      const minNorthing = Math.floor(swBNG.northing / gridSize) * gridSize;
      const maxNorthing = Math.ceil(neBNG.northing / gridSize) * gridSize;

      // Draw vertical lines (eastings)
      for (let easting = minEasting; easting <= maxEasting; easting += gridSize) {
        const points = [];
        for (let northing = minNorthing; northing <= maxNorthing; northing += gridSize / 10) {
          points.push(bngToLatLon(easting, northing));
        }
        
        const polyline = L.polyline(points, {
          color: '#FF0000',
          weight: 1,
          opacity: 0.5,
          gridLayer: true,
        }).addTo(map);

        // Add label at top of line
        const topPoint = bngToLatLon(easting, maxNorthing);
        const label = L.marker(topPoint, {
          icon: L.divIcon({
            className: 'grid-label',
            html: `<div style="background: rgba(255,255,255,0.7); padding: 2px 4px; font-size: 10px; font-weight: bold; border: 1px solid #FF0000;">${(easting / 1000).toFixed(0)}</div>`,
            iconSize: [40, 20],
          }),
          gridLayer: true,
        }).addTo(map);
      }

      // Draw horizontal lines (northings)
      for (let northing = minNorthing; northing <= maxNorthing; northing += gridSize) {
        const points = [];
        for (let easting = minEasting; easting <= maxEasting; easting += gridSize / 10) {
          points.push(bngToLatLon(easting, northing));
        }
        
        const polyline = L.polyline(points, {
          color: '#FF0000',
          weight: 1,
          opacity: 0.5,
          gridLayer: true,
        }).addTo(map);

        // Add label at left of line
        const leftPoint = bngToLatLon(minEasting, northing);
        const label = L.marker(leftPoint, {
          icon: L.divIcon({
            className: 'grid-label',
            html: `<div style="background: rgba(255,255,255,0.7); padding: 2px 4px; font-size: 10px; font-weight: bold; border: 1px solid #FF0000;">${(northing / 1000).toFixed(0)}</div>`,
            iconSize: [40, 20],
          }),
          gridLayer: true,
        }).addTo(map);
      }
    };

    // Draw initial grid
    drawGrid();

    // Redraw on zoom/move
    map.on('moveend', drawGrid);
    map.on('zoomend', drawGrid);

    return () => {
      map.off('moveend', drawGrid);
      map.off('zoomend', drawGrid);
      
      // Clean up grid layers
      map.eachLayer((layer) => {
        if (layer.options && layer.options.gridLayer) {
          map.removeLayer(layer);
        }
      });
    };
  }, [map, visible, gridSize, coordSystem]);

  return null;
};

export default BNGGridOverlay;
