import React, { useState, useEffect, useRef } from 'react';
import {
  Box,
  Paper,
  Typography,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  FormGroup,
  FormControlLabel,
  Checkbox,
  Button,
  Grid,
  Slider,
  Alert,
  LinearProgress,
  Chip,
  Divider,
} from '@mui/material';
import {
  Download as DownloadIcon,
  Stop as StopIcon,
  Refresh as RefreshIcon,
} from '@mui/icons-material';
import { useMap } from '../contexts/MapContext';

function TileDownloadPanel() {
  const { center, zoom, bounds } = useMap();
  
  // Form state
  const [centerLat, setCenterLat] = useState(center[0] || 51.6707);
  const [centerLon, setCenterLon] = useState(center[1] || -1.2879);
  const [layers, setLayers] = useState({ osm: true, satellite: true });
  const [zoomRange, setZoomRange] = useState([13, 19]);
  const [radiusMiles, setRadiusMiles] = useState(5);
  
  // Download state
  const [isDownloading, setIsDownloading] = useState(false);
  const [downloadStats, setDownloadStats] = useState({
    currentLayer: '',
    currentZoom: 0,
    totalTiles: 0,
    completed: 0,
    successful: 0,
    skipped: 0,
    blocked: 0,
    failed: 0,
  });
  const [downloadLogs, setDownloadLogs] = useState([]);
  const [gridProgress, setGridProgress] = useState({});
  
  // Refs
  const logContainerRef = useRef(null);
  
  // Update center coordinates when map center changes
  useEffect(() => {
    if (center && center[0] && center[1]) {
      setCenterLat(center[0]);
      setCenterLon(center[1]);
    }
  }, [center]);
  
  // Auto-scroll logs to bottom
  useEffect(() => {
    if (logContainerRef.current) {
      logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight;
    }
  }, [downloadLogs]);
  
  // Calculate estimated tile count and download size
  const calculateEstimates = () => {
    const layerCount = (layers.osm ? 1 : 0) + (layers.satellite ? 1 : 0);
    
    // Approximate tiles per zoom level in a circular area
    // tiles = 4^zoom * (π * r^2) where r is in tile units
    let totalTiles = 0;
    for (let z = zoomRange[0]; z <= zoomRange[1]; z++) {
      // Convert radius from miles to degrees (1 mile ≈ 1/69 degrees)
      const radiusDegrees = radiusMiles / 69;
      // Tiles per degree at this zoom level
      const tilesPerDegree = Math.pow(2, z) / 360;
      // Approximate tile count in circular area
      const tilesAtZoom = Math.PI * Math.pow(radiusDegrees * tilesPerDegree, 2);
      totalTiles += tilesAtZoom * layerCount;
    }
    
    // Estimate size (average 15KB per tile)
    const estimatedSizeMB = (totalTiles * 15) / 1024;
    
    return {
      tileCount: Math.round(totalTiles),
      sizeMB: estimatedSizeMB.toFixed(1),
      timeMinutes: Math.round((totalTiles * 1.5) / 60), // 1.5 seconds per tile (average of 1-2 second range)
    };
  };
  
  const estimates = calculateEstimates();
  
  const handleLayerChange = (layer) => {
    setLayers({ ...layers, [layer]: !layers[layer] });
  };
  
  const handleZoomRangeChange = (event, newValue) => {
    setZoomRange(newValue);
  };
  
  const addLog = (message, type = 'info') => {
    const timestamp = new Date().toLocaleTimeString();
    setDownloadLogs(prev => [...prev, { timestamp, message, type }]);
  };
  
  const startDownload = async () => {
    if (!layers.osm && !layers.satellite) {
      addLog('Please select at least one layer to download', 'error');
      return;
    }
    
    setIsDownloading(true);
    setDownloadLogs([]);
    setDownloadStats({
      currentLayer: '',
      currentZoom: 0,
      totalTiles: 0,
      completed: 0,
      successful: 0,
      skipped: 0,
      blocked: 0,
      failed: 0,
    });
    setGridProgress({});
    
    addLog('Starting tile download...', 'info');
    addLog(`Center: ${centerLat.toFixed(6)}°, ${centerLon.toFixed(6)}°`, 'info');
    addLog(`Radius: ${radiusMiles} miles`, 'info');
    addLog(`Zoom levels: ${zoomRange[0]} to ${zoomRange[1]}`, 'info');
    addLog(`Layers: ${[layers.osm && 'OSM', layers.satellite && 'Satellite'].filter(Boolean).join(', ')}`, 'info');
    
    try {
      // Create SSE connection to backend
      const selectedLayers = [];
      if (layers.osm) selectedLayers.push('osm');
      if (layers.satellite) selectedLayers.push('satellite');
      
      const url = new URL(`${process.env.REACT_APP_API_URL}/api/mapping/tiles/download`);
      url.searchParams.append('lat', centerLat);
      url.searchParams.append('lon', centerLon);
      url.searchParams.append('radius_miles', radiusMiles);
      url.searchParams.append('min_zoom', zoomRange[0]);
      url.searchParams.append('max_zoom', zoomRange[1]);
      url.searchParams.append('layers', selectedLayers.join(','));
      
      console.log('Connecting to:', url.toString());
      addLog(`Connecting to: ${url.toString()}`, 'info');
      
      // Get auth token
      const token = localStorage.getItem('token');
      
      if (!token) {
        addLog('No authentication token found. Please log in.', 'error');
        setIsDownloading(false);
        return;
      }
      
      console.log('Token exists:', !!token, 'Length:', token?.length);
      
      // Use fetch with streaming instead of EventSource (to support auth headers)
      const response = await fetch(url.toString(), {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Accept': 'text/event-stream',
        },
      });
      
      console.log('Response status:', response.status);
      
      if (!response.ok) {
        const errorText = await response.text();
        console.error('Error response:', errorText);
        addLog(`HTTP Error: ${response.status} ${response.statusText}`, 'error');
        if (response.status === 401) {
          addLog('Authentication failed. Please log in again.', 'error');
        }
        setIsDownloading(false);
        return;
      }
      
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      
      // Read stream
      const readStream = async () => {
        try {
          while (true) {
            const { done, value } = await reader.read();
            
            if (done) {
              addLog('Stream closed', 'info');
              setIsDownloading(false);
              break;
            }
            
            // Decode chunk and add to buffer
            buffer += decoder.decode(value, { stream: true });
            
            // Process complete SSE messages
            const lines = buffer.split('\n\n');
            buffer = lines.pop() || ''; // Keep incomplete message in buffer
            
            for (const line of lines) {
              if (line.startsWith('data: ')) {
                const dataStr = line.substring(6);
                try {
                  const data = JSON.parse(dataStr);
                  
                  if (data.type === 'progress') {
                    // Update stats
                    setDownloadStats(prev => ({
                      ...prev,
                      currentLayer: data.layer,
                      currentZoom: data.zoom,
                      totalTiles: data.total_tiles,
                      completed: data.completed,
                      successful: data.successful,
                      skipped: data.skipped,
                      blocked: data.blocked,
                      failed: data.failed,
                    }));
                    
                    // Update grid progress
                    if (data.tile_x !== undefined && data.tile_y !== undefined) {
                      setGridProgress(prev => ({
                        ...prev,
                        [`${data.layer}_${data.zoom}_${data.tile_x}_${data.tile_y}`]: data.status,
                      }));
                    }
                    
                    // Add log entry
                    const logMessage = `[${data.layer}/${data.zoom}/${data.tile_x}/${data.tile_y}] ${data.status.toUpperCase()}${data.size ? ` (${data.size} bytes)` : ''}`;
                    const logType = data.status === 'success' ? 'success' : data.status === 'blocked' ? 'warning' : data.status === 'failed' ? 'error' : 'info';
                    addLog(logMessage, logType);
                  } else if (data.type === 'layer_complete') {
                    addLog(`✅ Completed ${data.layer} layer at zoom ${data.zoom}`, 'success');
                    // Clear grid for next layer
                    setGridProgress({});
                  } else if (data.type === 'complete') {
                    addLog('🎉 Download complete!', 'success');
                    setIsDownloading(false);
                    break;
                  } else if (data.type === 'error') {
                    addLog(`❌ Error: ${data.message}`, 'error');
                    setIsDownloading(false);
                    break;
                  }
                } catch (parseError) {
                  console.error('Error parsing SSE data:', parseError, dataStr);
                }
              }
            }
          }
        } catch (error) {
          console.error('Stream reading error:', error);
          addLog(`Stream error: ${error.message}`, 'error');
          setIsDownloading(false);
        }
      };
      
      readStream();
      
    } catch (error) {
      console.error('Download error:', error);
      addLog(`Error: ${error.message}`, 'error');
      setIsDownloading(false);
    }
  };
  
  const stopDownload = () => {
    setIsDownloading(false);
    addLog('Download stopped by user', 'warning');
    // Note: Reader will be automatically closed when component unmounts or state changes
  };
  
  const useCurrentMapCenter = () => {
    if (center && center[0] && center[1]) {
      setCenterLat(center[0]);
      setCenterLon(center[1]);
      addLog(`Updated to current map center: ${center[0].toFixed(6)}°, ${center[1].toFixed(6)}°`, 'info');
    }
  };
  
  const getLogColor = (type) => {
    switch (type) {
      case 'success': return '#4caf50';
      case 'warning': return '#ff9800';
      case 'error': return '#f44336';
      default: return '#90caf9';
    }
  };
  
  const progressPercentage = downloadStats.totalTiles > 0 
    ? (downloadStats.completed / downloadStats.totalTiles) * 100 
    : 0;
  
  return (
    <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column', p: 3, overflow: 'auto' }}>
      <Typography variant="h4" gutterBottom>
        Download Map Tiles
      </Typography>
      
      <Grid container spacing={3}>
        {/* Left Column - Configuration */}
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 3, mb: 3 }}>
            <Typography variant="h6" gutterBottom>
              Download Configuration
            </Typography>
            
            {/* Center Coordinates */}
            <Box sx={{ mb: 3 }}>
              <Typography variant="subtitle2" gutterBottom>
                Center Coordinates
              </Typography>
              <Grid container spacing={2}>
                <Grid item xs={5}>
                  <TextField
                    fullWidth
                    label="Latitude"
                    type="number"
                    value={centerLat}
                    onChange={(e) => setCenterLat(parseFloat(e.target.value))}
                    disabled={isDownloading}
                    size="small"
                  />
                </Grid>
                <Grid item xs={5}>
                  <TextField
                    fullWidth
                    label="Longitude"
                    type="number"
                    value={centerLon}
                    onChange={(e) => setCenterLon(parseFloat(e.target.value))}
                    disabled={isDownloading}
                    size="small"
                  />
                </Grid>
                <Grid item xs={2}>
                  <Button
                    fullWidth
                    variant="outlined"
                    onClick={useCurrentMapCenter}
                    disabled={isDownloading}
                    size="small"
                    sx={{ height: '40px' }}
                  >
                    <RefreshIcon />
                  </Button>
                </Grid>
              </Grid>
            </Box>
            
            {/* Radius */}
            <Box sx={{ mb: 3 }}>
              <Typography variant="subtitle2" gutterBottom>
                Radius: {radiusMiles} miles
              </Typography>
              <Slider
                value={radiusMiles}
                onChange={(e, value) => setRadiusMiles(value)}
                min={1}
                max={50}
                step={1}
                marks={[
                  { value: 1, label: '1' },
                  { value: 10, label: '10' },
                  { value: 25, label: '25' },
                  { value: 50, label: '50' },
                ]}
                disabled={isDownloading}
              />
            </Box>
            
            {/* Layers */}
            <Box sx={{ mb: 3 }}>
              <Typography variant="subtitle2" gutterBottom>
                Layers to Download
              </Typography>
              <FormGroup>
                <FormControlLabel
                  control={
                    <Checkbox
                      checked={layers.osm}
                      onChange={() => handleLayerChange('osm')}
                      disabled={isDownloading}
                    />
                  }
                  label="OpenStreetMap"
                />
                <FormControlLabel
                  control={
                    <Checkbox
                      checked={layers.satellite}
                      onChange={() => handleLayerChange('satellite')}
                      disabled={isDownloading}
                    />
                  }
                  label="Satellite Imagery"
                />
              </FormGroup>
            </Box>
            
            {/* Zoom Range */}
            <Box sx={{ mb: 3 }}>
              <Typography variant="subtitle2" gutterBottom>
                Zoom Levels: {zoomRange[0]} to {zoomRange[1]}
              </Typography>
              <Slider
                value={zoomRange}
                onChange={handleZoomRangeChange}
                min={8}
                max={19}
                step={1}
                marks={[
                  { value: 8, label: '8' },
                  { value: 11, label: '11' },
                  { value: 14, label: '14' },
                  { value: 17, label: '17' },
                  { value: 19, label: '19' },
                ]}
                valueLabelDisplay="auto"
                disabled={isDownloading}
              />
            </Box>
            
            <Divider sx={{ my: 2 }} />
            
            {/* Estimates */}
            <Box sx={{ mb: 3 }}>
              <Typography variant="subtitle2" gutterBottom>
                Estimated Download
              </Typography>
              <Grid container spacing={2}>
                <Grid item xs={4}>
                  <Chip label={`${estimates.tileCount.toLocaleString()} tiles`} color="primary" />
                </Grid>
                <Grid item xs={4}>
                  <Chip label={`~${estimates.sizeMB} MB`} color="secondary" />
                </Grid>
                <Grid item xs={4}>
                  <Chip label={`~${estimates.timeMinutes} min`} color="info" />
                </Grid>
              </Grid>
            </Box>
            
            {/* Action Buttons */}
            <Box sx={{ display: 'flex', gap: 2 }}>
              {!isDownloading ? (
                <Button
                  fullWidth
                  variant="contained"
                  color="primary"
                  startIcon={<DownloadIcon />}
                  onClick={startDownload}
                >
                  Start Download
                </Button>
              ) : (
                <Button
                  fullWidth
                  variant="contained"
                  color="error"
                  startIcon={<StopIcon />}
                  onClick={stopDownload}
                >
                  Stop Download
                </Button>
              )}
            </Box>
          </Paper>
        </Grid>
        
        {/* Right Column - Progress & Logs */}
        <Grid item xs={12} md={6}>
          {/* Progress Stats */}
          {isDownloading && (
            <Paper sx={{ p: 3, mb: 3 }}>
              <Typography variant="h6" gutterBottom>
                Download Progress
              </Typography>
              
              <Box sx={{ mb: 2 }}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                  <Typography variant="body2">
                    {downloadStats.currentLayer} - Zoom {downloadStats.currentZoom}
                  </Typography>
                  <Typography variant="body2">
                    {downloadStats.completed} / {downloadStats.totalTiles}
                  </Typography>
                </Box>
                <LinearProgress variant="determinate" value={progressPercentage} />
                <Typography variant="caption" color="text.secondary">
                  {progressPercentage.toFixed(1)}% complete
                </Typography>
              </Box>
              
              <Grid container spacing={2}>
                <Grid item xs={6}>
                  <Typography variant="body2" color="success.main">
                    ✅ Success: {downloadStats.successful}
                  </Typography>
                </Grid>
                <Grid item xs={6}>
                  <Typography variant="body2" color="info.main">
                    ✓ Skipped: {downloadStats.skipped}
                  </Typography>
                </Grid>
                <Grid item xs={6}>
                  <Typography variant="body2" color="warning.main">
                    🚫 Blocked: {downloadStats.blocked}
                  </Typography>
                </Grid>
                <Grid item xs={6}>
                  <Typography variant="body2" color="error.main">
                    ❌ Failed: {downloadStats.failed}
                  </Typography>
                </Grid>
              </Grid>
            </Paper>
          )}
          
          {/* Download Logs */}
          <Paper sx={{ p: 3, height: isDownloading ? '400px' : '600px', display: 'flex', flexDirection: 'column' }}>
            <Typography variant="h6" gutterBottom>
              Download Log
            </Typography>
            
            <Box
              ref={logContainerRef}
              sx={{
                flexGrow: 1,
                overflow: 'auto',
                bgcolor: '#1e1e1e',
                p: 2,
                borderRadius: 1,
                fontFamily: 'monospace',
                fontSize: '12px',
              }}
            >
              {downloadLogs.length === 0 ? (
                <Typography variant="body2" color="text.secondary">
                  No logs yet. Start a download to see progress.
                </Typography>
              ) : (
                downloadLogs.map((log, index) => (
                  <Box key={index} sx={{ mb: 0.5, color: getLogColor(log.type) }}>
                    [{log.timestamp}] {log.message}
                  </Box>
                ))
              )}
            </Box>
          </Paper>
        </Grid>
      </Grid>
      
      {/* Grid Visualization (Placeholder - will be enhanced) */}
      {isDownloading && (
        <Paper sx={{ p: 3, mt: 3 }}>
          <Typography variant="h6" gutterBottom>
            Visual Progress ({downloadStats.currentLayer} - Zoom {downloadStats.currentZoom})
          </Typography>
          <Box
            sx={{
              width: '100%',
              height: '300px',
              bgcolor: '#2e2e2e',
              borderRadius: 1,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <Typography variant="body2" color="text.secondary">
              Grid visualization coming soon...
            </Typography>
          </Box>
        </Paper>
      )}
    </Box>
  );
}

export default TileDownloadPanel;
