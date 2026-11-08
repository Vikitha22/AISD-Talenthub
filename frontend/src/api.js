import axios from 'axios';

// Vite dev server and FastAPI are separate processes. Keep the API origin explicit,
// but allow an environment override for deployments and alternate local ports.
const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000',
  timeout: 15000,
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('talenthub_token');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

export function getApiError(error) {
  if (error?.response) {
    const detail = error.response.data?.detail;
    return typeof detail === 'string' ? detail : detail?.message || `Request failed (${error.response.status})`;
  }
  if (error?.code === 'ECONNABORTED') return 'The backend did not respond in time. Check that it is running on port 8000.';
  return 'Cannot reach the backend at http://127.0.0.1:8000. Start the backend terminal and keep it running.';
}

export default api;
