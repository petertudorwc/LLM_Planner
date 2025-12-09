import React, { createContext, useContext, useState } from 'react';

const MapContext = createContext();

export function MapProvider({ children }) {
  const [mapUpdates, setMapUpdates] = useState([]);
  const [center, setCenter] = useState([51.6707, -1.2879]); // Default to Abingdon
  const [zoom, setZoom] = useState(13);
  const [bounds, setBounds] = useState(null);
  
  const addMapUpdate = (update) => {
    setMapUpdates(prev => [...prev, update]);
  };
  
  const clearMapUpdates = () => {
    setMapUpdates([]);
  };
  
  const updateMapPosition = (newCenter, newZoom, newBounds) => {
    if (newCenter) setCenter(newCenter);
    if (newZoom !== undefined) setZoom(newZoom);
    if (newBounds) setBounds(newBounds);
  };

  return (
    <MapContext.Provider value={{ 
      mapUpdates, 
      addMapUpdate, 
      clearMapUpdates,
      center,
      zoom,
      bounds,
      updateMapPosition,
    }}>
      {children}
    </MapContext.Provider>
  );
}

export function useMap() {
  const context = useContext(MapContext);
  if (!context) {
    throw new Error('useMap must be used within MapProvider');
  }
  return context;
}
