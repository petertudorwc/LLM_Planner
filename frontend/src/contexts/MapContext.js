import React, { createContext, useContext, useState } from 'react';

const MapContext = createContext();

export function MapProvider({ children }) {
  const [mapUpdates, setMapUpdates] = useState([]);
  
  const addMapUpdate = (update) => {
    setMapUpdates(prev => [...prev, update]);
  };
  
  const clearMapUpdates = () => {
    setMapUpdates([]);
  };

  return (
    <MapContext.Provider value={{ mapUpdates, addMapUpdate, clearMapUpdates }}>
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
