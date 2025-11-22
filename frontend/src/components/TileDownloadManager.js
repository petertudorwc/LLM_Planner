import React, { useState, useEffect } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Box,
  Typography,
  TextField,
  LinearProgress,
  Alert,
  Chip,
  Stack,
  FormGroup,
  FormControlLabel,
  Checkbox,
} from '@mui/material';
import { Download as DownloadIcon } from '@mui/icons-material';
import { mappingAPI } from '../services/api';

function TileDownloadManager({ open, onClose }) {
  const [areaName, setAreaName] = useState('abingdon');
  const [bounds, setBounds] = useState({
    lat_min: 51.63,
    lon_min: -1.35,
    lat_max: 51.71,
    lon_max: -1.22,
  });
  const [zoomLevels, setZoomLevels] = useState([12, 13, 14, 15, 16]);
  const [layers, setLayers] = useState({ osm: true, satellite: true });
  const [downloading, setDownloading] = useState(false);
  const [status, setStatus] = useState(null);
  const [tileStats, setTileStats] = useState(null);

  useEffect(() => {
    if (open) {
      loadTileStats();
    }
  }, [open]);

  const loadTileStats = async () => {
    try {
      const response = await mappingAPI.getTileStatus();
      setTileStats(response.data);
    } catch (error) {
      console.error('Error loading tile stats:', error);
    }
  };

  const handleDownload = async () => {
    setDownloading(true);
    setStatus(null);

    try {
      const response = await mappingAPI.downloadTiles({
        area_name: areaName,
        lat_min: parseFloat(bounds.lat_min),
        lon_min: parseFloat(bounds.lon_min),
        lat_max: parseFloat(bounds.lat_max),
        lon_max: parseFloat(bounds.lon_max),
        zoom_levels: zoomLevels,
        layers: Object.keys(layers).filter(k => layers[k]),
      });

      setStatus({ type: 'success', message: response.data.message });
      
      // Reload stats after a delay
      setTimeout(loadTileStats, 5000);
    } catch (error) {
      setStatus({ type: 'error', message: `Error: ${error.message}` });
    } finally {
      setDownloading(false);
    }
  };

  const estimateTileCount = () => {
    // Rough estimate: tiles per zoom level
    const latDiff = Math.abs(bounds.lat_max - bounds.lat_min);
    const lonDiff = Math.abs(bounds.lon_max - bounds.lon_min);
    
    let total = 0;
    zoomLevels.forEach(z => {
      const tilesX = Math.ceil((lonDiff / 360) * Math.pow(2, z));
      const tilesY = Math.ceil((latDiff / 180) * Math.pow(2, z));
      total += tilesX * tilesY;
    });
    
    const layerCount = Object.values(layers).filter(v => v).length;
    return total * layerCount;
  };

  const estimateSize = () => {
    const tileCount = estimateTileCount();
    const avgTileSize = 25; // KB
    const totalMB = (tileCount * avgTileSize) / 1024;
    return totalMB.toFixed(1);
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle>Download Offline Map Tiles</DialogTitle>
      <DialogContent>
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3, pt: 2 }}>
          {/* Current Tile Stats */}
          {tileStats && (
            <Alert severity="info">
              <Typography variant="subtitle2" sx={{ mb: 1 }}>
                Current Cache:
              </Typography>
              <Stack direction="row" spacing={2}>
                <Chip label={`OSM: ${tileStats.osm?.tiles || 0} tiles`} size="small" />
                <Chip label={`Satellite: ${tileStats.satellite?.tiles || 0} tiles`} size="small" />
              </Stack>
            </Alert>
          )}

          {/* Area Name */}
          <TextField
            label="Area Name"
            value={areaName}
            onChange={(e) => setAreaName(e.target.value)}
            fullWidth
            helperText="Descriptive name for this area (e.g., 'abingdon', 'oxford')"
          />

          {/* Bounds */}
          <Box>
            <Typography variant="subtitle2" sx={{ mb: 1 }}>
              Geographic Bounds
            </Typography>
            <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 2 }}>
              <TextField
                label="Min Latitude"
                type="number"
                value={bounds.lat_min}
                onChange={(e) => setBounds({ ...bounds, lat_min: e.target.value })}
                inputProps={{ step: 0.01 }}
              />
              <TextField
                label="Max Latitude"
                type="number"
                value={bounds.lat_max}
                onChange={(e) => setBounds({ ...bounds, lat_max: e.target.value })}
                inputProps={{ step: 0.01 }}
              />
              <TextField
                label="Min Longitude"
                type="number"
                value={bounds.lon_min}
                onChange={(e) => setBounds({ ...bounds, lon_min: e.target.value })}
                inputProps={{ step: 0.01 }}
              />
              <TextField
                label="Max Longitude"
                type="number"
                value={bounds.lon_max}
                onChange={(e) => setBounds({ ...bounds, lon_max: e.target.value })}
                inputProps={{ step: 0.01 }}
              />
            </Box>
          </Box>

          {/* Zoom Levels */}
          <Box>
            <Typography variant="subtitle2" sx={{ mb: 1 }}>
              Zoom Levels (12-16 recommended for local area)
            </Typography>
            <Stack direction="row" spacing={1} flexWrap="wrap">
              {[10, 11, 12, 13, 14, 15, 16, 17, 18].map(z => (
                <Chip
                  key={z}
                  label={z}
                  onClick={() => {
                    if (zoomLevels.includes(z)) {
                      setZoomLevels(zoomLevels.filter(level => level !== z));
                    } else {
                      setZoomLevels([...zoomLevels, z].sort());
                    }
                  }}
                  color={zoomLevels.includes(z) ? 'primary' : 'default'}
                  variant={zoomLevels.includes(z) ? 'filled' : 'outlined'}
                />
              ))}
            </Stack>
          </Box>

          {/* Layer Selection */}
          <Box>
            <Typography variant="subtitle2" sx={{ mb: 1 }}>
              Map Layers
            </Typography>
            <FormGroup>
              <FormControlLabel
                control={
                  <Checkbox
                    checked={layers.osm}
                    onChange={(e) => setLayers({ ...layers, osm: e.target.checked })}
                  />
                }
                label="OpenStreetMap (street view)"
              />
              <FormControlLabel
                control={
                  <Checkbox
                    checked={layers.satellite}
                    onChange={(e) => setLayers({ ...layers, satellite: e.target.checked })}
                  />
                }
                label="Satellite Imagery"
              />
            </FormGroup>
          </Box>

          {/* Estimate */}
          <Alert severity="warning">
            <Typography variant="body2">
              <strong>Estimated:</strong> ~{estimateTileCount()} tiles (~{estimateSize()} MB)
            </Typography>
            <Typography variant="caption" display="block" sx={{ mt: 1 }}>
              Downloads run in the background. This may take several minutes depending on the area size.
            </Typography>
          </Alert>

          {/* Status */}
          {status && (
            <Alert severity={status.type}>
              {status.message}
            </Alert>
          )}

          {downloading && <LinearProgress />}
        </Box>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Close</Button>
        <Button
          variant="contained"
          startIcon={<DownloadIcon />}
          onClick={handleDownload}
          disabled={downloading || zoomLevels.length === 0}
        >
          Download Tiles
        </Button>
      </DialogActions>
    </Dialog>
  );
}

export default TileDownloadManager;
