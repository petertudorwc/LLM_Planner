import React, { useState } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Box,
  Typography,
  TextField,
  Stepper,
  Step,
  StepLabel,
  Paper,
  List,
  ListItem,
  ListItemText,
} from '@mui/material';

/**
 * CustomImageUpload - Dialog for uploading and georeferencing custom map images
 * 
 * Process:
 * 1. Upload image file
 * 2. Click on 3+ control points on the image
 * 3. Enter known coordinates (lat/lon or BNG) for each control point
 * 4. Calculate image bounds and add to map
 */
function CustomImageUpload({ open, onClose, onImageAdded }) {
  const [activeStep, setActiveStep] = useState(0);
  const [imageFile, setImageFile] = useState(null);
  const [imageUrl, setImageUrl] = useState(null);
  const [imageName, setImageName] = useState('');
  const [controlPoints, setControlPoints] = useState([]);
  const [currentPointCoords, setCurrentPointCoords] = useState({ lat: '', lon: '' });

  const steps = ['Upload Image', 'Mark Control Points', 'Enter Coordinates', 'Confirm'];

  const handleImageUpload = (event) => {
    const file = event.target.files[0];
    if (file) {
      setImageFile(file);
      setImageName(file.name);
      const url = URL.createObjectURL(file);
      setImageUrl(url);
    }
  };

  const handleImageClick = (event) => {
    if (activeStep !== 1) return;

    const rect = event.target.getBoundingClientRect();
    const x = event.clientX - rect.left;
    const y = event.clientY - rect.top;
    
    // Convert to normalized coordinates (0-1)
    const normX = x / rect.width;
    const normY = y / rect.height;

    setControlPoints([...controlPoints, { x: normX, y: normY, lat: null, lon: null }]);
  };

  const handleAddCoordinates = () => {
    if (!currentPointCoords.lat || !currentPointCoords.lon) return;

    const pointIndex = controlPoints.findIndex(p => p.lat === null);
    if (pointIndex === -1) return;

    const updatedPoints = [...controlPoints];
    updatedPoints[pointIndex] = {
      ...updatedPoints[pointIndex],
      lat: parseFloat(currentPointCoords.lat),
      lon: parseFloat(currentPointCoords.lon),
    };

    setControlPoints(updatedPoints);
    setCurrentPointCoords({ lat: '', lon: '' });
  };

  const handleConfirm = () => {
    if (controlPoints.length < 3) {
      alert('Need at least 3 control points');
      return;
    }

    // Simple 3-point georeferencing (for production, use more sophisticated transformation)
    // Calculate bounds from control points
    const lats = controlPoints.map(p => p.lat);
    const lons = controlPoints.map(p => p.lon);

    const bounds = [
      [Math.min(...lats), Math.min(...lons)], // Southwest
      [Math.max(...lats), Math.max(...lons)], // Northeast
    ];

    onImageAdded({
      url: imageUrl,
      bounds: bounds,
      name: imageName,
      controlPoints: controlPoints,
    });

    handleClose();
  };

  const handleClose = () => {
    setActiveStep(0);
    setImageFile(null);
    setImageUrl(null);
    setImageName('');
    setControlPoints([]);
    setCurrentPointCoords({ lat: '', lon: '' });
    onClose();
  };

  const nextDisabled = () => {
    if (activeStep === 0) return !imageFile;
    if (activeStep === 1) return controlPoints.length < 3;
    if (activeStep === 2) return controlPoints.some(p => p.lat === null);
    return false;
  };

  return (
    <Dialog open={open} onClose={handleClose} maxWidth="lg" fullWidth>
      <DialogTitle>Upload Custom Map Image</DialogTitle>
      <DialogContent>
        <Stepper activeStep={activeStep} sx={{ mb: 3 }}>
          {steps.map((label) => (
            <Step key={label}>
              <StepLabel>{label}</StepLabel>
            </Step>
          ))}
        </Stepper>

        {/* Step 0: Upload Image */}
        {activeStep === 0 && (
          <Box sx={{ textAlign: 'center', p: 3 }}>
            <Typography variant="body1" sx={{ mb: 2 }}>
              Select a map image to upload (PNG, JPG, or GeoTIFF)
            </Typography>
            <Button variant="contained" component="label">
              Choose Image
              <input type="file" hidden accept="image/*" onChange={handleImageUpload} />
            </Button>
            {imageName && (
              <Typography variant="body2" sx={{ mt: 2 }}>
                Selected: {imageName}
              </Typography>
            )}
          </Box>
        )}

        {/* Step 1: Mark Control Points */}
        {activeStep === 1 && imageUrl && (
          <Box>
            <Typography variant="body1" sx={{ mb: 2 }}>
              Click on at least 3 identifiable points on the image (e.g., road intersections, buildings)
            </Typography>
            <Paper sx={{ p: 2, position: 'relative', display: 'inline-block', maxWidth: '100%' }}>
              <img
                src={imageUrl}
                alt="Map to georeference"
                style={{ maxWidth: '100%', cursor: 'crosshair' }}
                onClick={handleImageClick}
              />
              {/* Draw markers on control points */}
              {controlPoints.map((point, idx) => (
                <div
                  key={idx}
                  style={{
                    position: 'absolute',
                    left: `${point.x * 100}%`,
                    top: `${point.y * 100}%`,
                    width: '20px',
                    height: '20px',
                    backgroundColor: 'red',
                    borderRadius: '50%',
                    border: '2px solid white',
                    transform: 'translate(-50%, -50%)',
                    pointerEvents: 'none',
                  }}
                >
                  <Typography
                    variant="caption"
                    sx={{
                      position: 'absolute',
                      top: -20,
                      left: '50%',
                      transform: 'translateX(-50%)',
                      backgroundColor: 'rgba(255,255,255,0.9)',
                      padding: '2px 4px',
                      borderRadius: '4px',
                      fontWeight: 'bold',
                    }}
                  >
                    {idx + 1}
                  </Typography>
                </div>
              ))}
            </Paper>
            <Typography variant="body2" sx={{ mt: 2 }}>
              Control points marked: {controlPoints.length} / 3 minimum
            </Typography>
          </Box>
        )}

        {/* Step 2: Enter Coordinates */}
        {activeStep === 2 && (
          <Box>
            <Typography variant="body1" sx={{ mb: 2 }}>
              Enter the known coordinates for each control point
            </Typography>
            <List>
              {controlPoints.map((point, idx) => (
                <ListItem key={idx}>
                  <ListItemText
                    primary={`Point ${idx + 1}`}
                    secondary={
                      point.lat
                        ? `Lat: ${point.lat.toFixed(6)}, Lon: ${point.lon.toFixed(6)}`
                        : 'Coordinates not set'
                    }
                  />
                </ListItem>
              ))}
            </List>
            {controlPoints.some(p => p.lat === null) && (
              <Box sx={{ display: 'flex', gap: 2, mt: 2 }}>
                <TextField
                  label="Latitude"
                  type="number"
                  value={currentPointCoords.lat}
                  onChange={(e) =>
                    setCurrentPointCoords({ ...currentPointCoords, lat: e.target.value })
                  }
                  fullWidth
                />
                <TextField
                  label="Longitude"
                  type="number"
                  value={currentPointCoords.lon}
                  onChange={(e) =>
                    setCurrentPointCoords({ ...currentPointCoords, lon: e.target.value })
                  }
                  fullWidth
                />
                <Button variant="contained" onClick={handleAddCoordinates}>
                  Add
                </Button>
              </Box>
            )}
          </Box>
        )}

        {/* Step 3: Confirm */}
        {activeStep === 3 && (
          <Box>
            <Typography variant="body1" sx={{ mb: 2 }}>
              Review your georeferenced image settings
            </Typography>
            <Typography variant="body2">Image: {imageName}</Typography>
            <Typography variant="body2">Control Points: {controlPoints.length}</Typography>
            <Typography variant="body2" sx={{ mt: 2 }}>
              Click "Add to Map" to complete the process.
            </Typography>
          </Box>
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={handleClose}>Cancel</Button>
        <Button disabled={activeStep === 0} onClick={() => setActiveStep(activeStep - 1)}>
          Back
        </Button>
        {activeStep < steps.length - 1 ? (
          <Button
            variant="contained"
            disabled={nextDisabled()}
            onClick={() => setActiveStep(activeStep + 1)}
          >
            Next
          </Button>
        ) : (
          <Button variant="contained" onClick={handleConfirm}>
            Add to Map
          </Button>
        )}
      </DialogActions>
    </Dialog>
  );
}

export default CustomImageUpload;
