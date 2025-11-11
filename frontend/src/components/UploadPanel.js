import React, { useState } from 'react';
import {
  Box,
  Paper,
  Typography,
  Button,
  List,
  ListItem,
  ListItemText,
  Alert,
  CircularProgress,
} from '@mui/material';
import { CloudUpload as UploadIcon } from '@mui/icons-material';
import { ingestionAPI } from '../services/api';

function UploadPanel() {
  const [files, setFiles] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');

  const handleFileSelect = (event) => {
    const selectedFiles = Array.from(event.target.files);
    setFiles(selectedFiles);
    setResult(null);
    setError('');
  };

  const handleUpload = async () => {
    if (files.length === 0) return;

    setUploading(true);
    setError('');
    setResult(null);

    try {
      const formData = new FormData();
      files.forEach((file) => {
        formData.append('files', file);
      });

      const response = await ingestionAPI.uploadFiles(formData);
      setResult(response.data);
      setFiles([]);
    } catch (err) {
      console.error('Upload error:', err);
      setError(err.response?.data?.detail || 'Upload failed');
    } finally {
      setUploading(false);
    }
  };

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" gutterBottom>
        Upload Documents
      </Typography>
      <Typography variant="body1" color="text.secondary" paragraph>
        Upload PDF, Word, Excel, CSV, or geospatial files to add them to the knowledge base.
      </Typography>

      <Paper sx={{ p: 3, mt: 3 }}>
        <input
          accept=".pdf,.docx,.doc,.xlsx,.xls,.csv,.geojson,.kml"
          style={{ display: 'none' }}
          id="file-upload"
          multiple
          type="file"
          onChange={handleFileSelect}
        />
        <label htmlFor="file-upload">
          <Button
            variant="contained"
            component="span"
            startIcon={<UploadIcon />}
            fullWidth
            size="large"
          >
            Select Files
          </Button>
        </label>

        {files.length > 0 && (
          <Box sx={{ mt: 3 }}>
            <Typography variant="h6" gutterBottom>
              Selected Files ({files.length})
            </Typography>
            <List>
              {files.map((file, index) => (
                <ListItem key={index}>
                  <ListItemText
                    primary={file.name}
                    secondary={`${(file.size / 1024).toFixed(2)} KB`}
                  />
                </ListItem>
              ))}
            </List>
            <Button
              variant="contained"
              color="primary"
              onClick={handleUpload}
              disabled={uploading}
              fullWidth
              sx={{ mt: 2 }}
            >
              {uploading ? <CircularProgress size={24} /> : 'Upload and Process'}
            </Button>
          </Box>
        )}

        {error && (
          <Alert severity="error" sx={{ mt: 2 }}>
            {error}
          </Alert>
        )}

        {result && (
          <Alert severity="success" sx={{ mt: 2 }}>
            Successfully processed {result.processed_files} files with {result.chunks_created} chunks.
            {result.errors.length > 0 && (
              <Box sx={{ mt: 1 }}>
                <Typography variant="body2">Errors:</Typography>
                <ul>
                  {result.errors.map((err, idx) => (
                    <li key={idx}>{err}</li>
                  ))}
                </ul>
              </Box>
            )}
          </Alert>
        )}
      </Paper>
    </Box>
  );
}

export default UploadPanel;
