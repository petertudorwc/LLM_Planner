import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './LayersPanel.css';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

function LayersPanel() {
  const [layers, setLayers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [editingLayer, setEditingLayer] = useState(null);
  const [editForm, setEditForm] = useState({
    name: '',
    style: {}
  });

  const fetchLayers = async () => {
    try {
      setLoading(true);
      const token = localStorage.getItem('token');
      const response = await axios.get(`${API_URL}/api/mapping/layers`, {
        headers: {
          Authorization: `Bearer ${token}`
        }
      });
      setLayers(response.data.layers || []);
      setError(null);
    } catch (err) {
      console.error('Error fetching layers:', err);
      setError('Failed to load layers');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLayers();
    // Refresh every 5 seconds
    const interval = setInterval(fetchLayers, 5000);
    return () => clearInterval(interval);
  }, []);

  const handleDelete = async (layerId) => {
    if (!window.confirm(`Are you sure you want to delete layer "${layerId}"?`)) {
      return;
    }

    try {
      const token = localStorage.getItem('token');
      await axios.delete(`${API_URL}/api/mapping/layers/${layerId}`, {
        headers: {
          Authorization: `Bearer ${token}`
        }
      });
      fetchLayers(); // Refresh the list
    } catch (err) {
      console.error('Error deleting layer:', err);
      alert('Failed to delete layer');
    }
  };

  const handleEdit = (layer) => {
    setEditingLayer(layer.id);
    setEditForm({
      name: layer.name,
      style: layer.style || {}
    });
  };

  const handleCancelEdit = () => {
    setEditingLayer(null);
    setEditForm({ name: '', style: {} });
  };

  const handleSaveEdit = async (layerId) => {
    try {
      const token = localStorage.getItem('token');
      await axios.patch(
        `${API_URL}/api/mapping/layers/${layerId}`,
        {
          name: editForm.name,
          style: editForm.style
        },
        {
          headers: {
            Authorization: `Bearer ${token}`
          }
        }
      );
      setEditingLayer(null);
      fetchLayers(); // Refresh the list
    } catch (err) {
      console.error('Error updating layer:', err);
      alert('Failed to update layer');
    }
  };

  const getLayerTypeIcon = (type) => {
    switch (type) {
      case 'point':
        return '📍';
      case 'polygon':
        return '⬡';
      case 'line':
        return '📏';
      default:
        return '🗺️';
    }
  };

  const getGeometryInfo = (data) => {
    if (!data) return 'Unknown';
    
    if (data.type === 'Point') {
      return `Point (${data.coordinates[1].toFixed(4)}°, ${data.coordinates[0].toFixed(4)}°)`;
    } else if (data.type === 'Polygon') {
      const coords = data.coordinates[0];
      return `Polygon (${coords.length} vertices)`;
    } else if (data.type === 'FeatureCollection') {
      return `Collection (${data.features?.length || 0} features)`;
    }
    return data.type || 'Unknown';
  };

  if (loading && layers.length === 0) {
    return (
      <div className="layers-panel">
        <div className="loading">Loading layers...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="layers-panel">
        <div className="error">{error}</div>
        <button onClick={fetchLayers}>Retry</button>
      </div>
    );
  }

  return (
    <div className="layers-panel">
      <div className="layers-header">
        <h2>Map Layers ({layers.length})</h2>
        <button className="refresh-btn" onClick={fetchLayers}>
          🔄 Refresh
        </button>
      </div>

      {layers.length === 0 ? (
        <div className="empty-state">
          <p>No layers on the map yet.</p>
          <p>Use the chat to add points, polygons, or boundaries!</p>
        </div>
      ) : (
        <div className="layers-list">
          {layers.map((layer) => (
            <div key={layer.id} className="layer-card">
              {editingLayer === layer.id ? (
                // Edit mode
                <div className="layer-edit">
                  <div className="edit-field">
                    <label>Name:</label>
                    <input
                      type="text"
                      value={editForm.name}
                      onChange={(e) => setEditForm({ ...editForm, name: e.target.value })}
                    />
                  </div>
                  <div className="edit-field">
                    <label>Color:</label>
                    <input
                      type="color"
                      value={editForm.style.color || '#3388ff'}
                      onChange={(e) =>
                        setEditForm({
                          ...editForm,
                          style: { ...editForm.style, color: e.target.value }
                        })
                      }
                    />
                  </div>
                  <div className="edit-field">
                    <label>Opacity:</label>
                    <input
                      type="range"
                      min="0"
                      max="1"
                      step="0.1"
                      value={editForm.style.fillOpacity || 0.5}
                      onChange={(e) =>
                        setEditForm({
                          ...editForm,
                          style: { ...editForm.style, fillOpacity: parseFloat(e.target.value) }
                        })
                      }
                    />
                    <span>{(editForm.style.fillOpacity || 0.5) * 100}%</span>
                  </div>
                  <div className="edit-actions">
                    <button className="save-btn" onClick={() => handleSaveEdit(layer.id)}>
                      ✓ Save
                    </button>
                    <button className="cancel-btn" onClick={handleCancelEdit}>
                      ✕ Cancel
                    </button>
                  </div>
                </div>
              ) : (
                // View mode
                <>
                  <div className="layer-header">
                    <span className="layer-icon">{getLayerTypeIcon(layer.type)}</span>
                    <div className="layer-info">
                      <h3>{layer.name}</h3>
                      <p className="layer-type">{layer.type}</p>
                    </div>
                  </div>

                  <div className="layer-details">
                    <div className="detail-row">
                      <span className="label">ID:</span>
                      <span className="value">{layer.id}</span>
                    </div>
                    <div className="detail-row">
                      <span className="label">Geometry:</span>
                      <span className="value">{getGeometryInfo(layer.data)}</span>
                    </div>
                    {layer.style && (
                      <div className="detail-row">
                        <span className="label">Style:</span>
                        <div className="style-preview">
                          {layer.style.color && (
                            <span
                              className="color-swatch"
                              style={{ backgroundColor: layer.style.color }}
                            />
                          )}
                          {layer.style.fillOpacity !== undefined && (
                            <span>{(layer.style.fillOpacity * 100).toFixed(0)}% opacity</span>
                          )}
                        </div>
                      </div>
                    )}
                  </div>

                  <div className="layer-actions">
                    <button className="edit-btn" onClick={() => handleEdit(layer)}>
                      ✏️ Edit
                    </button>
                    <button className="delete-btn" onClick={() => handleDelete(layer.id)}>
                      🗑️ Delete
                    </button>
                  </div>
                </>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default LayersPanel;
