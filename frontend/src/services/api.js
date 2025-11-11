import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add auth token to requests
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Auth API
export const authAPI = {
  login: (username, password) =>
    api.post('/api/auth/login', { username, password }),
  logout: () => api.post('/api/auth/logout'),
  getCurrentUser: () => api.get('/api/auth/me'),
};

// Chat API
export const chatAPI = {
  sendMessage: (message, history) =>
    api.post('/api/chat/message', { message, conversation_history: history }),
  getHistory: () => api.get('/api/chat/history'),
};

// Mapping API
export const mappingAPI = {
  getLayers: () => api.get('/api/mapping/layers'),
  createLayer: (layer) => api.post('/api/mapping/layers', layer),
  deleteLayer: (layerId) => api.delete(`/api/mapping/layers/${layerId}`),
};

// Ingestion API
export const ingestionAPI = {
  uploadFiles: (formData) =>
    api.post('/api/ingest/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),
  getDocuments: () => api.get('/api/ingest/documents'),
};

// Speech API
export const speechAPI = {
  transcribe: (audioBlob) => {
    const formData = new FormData();
    formData.append('audio', audioBlob, 'recording.wav');
    return api.post('/api/speech/transcribe', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },
};

export default api;
