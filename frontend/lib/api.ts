import axios from 'axios';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_URL,
  timeout: 15000, // 15 seconds as per requirements
  headers: {
    'Content-Type': 'application/json',
  },
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export const authAPI = {
  signup: (data: { email: string; username: string; password: string; full_name?: string }) =>
    api.post('/api/v1/auth/signup', data),
  login: (data: { email: string; password: string }) =>
    api.post('/api/v1/auth/login', data),
  me: () => api.get('/api/v1/auth/me'),
  logout: () => api.post('/api/v1/auth/logout'),
};

export const chatAPI = {
  sendMessage: (data: { user_input: string; session_id: string }) =>
    api.post('/api/v1/chat', data),
  getSessions: () => api.get('/api/v1/sessions'),
  getSessionHistory: (sessionId: string) =>
    api.get(`/api/v1/sessions/${sessionId}`),
  deleteSession: (sessionId: string) =>
    api.delete(`/api/v1/sessions/${sessionId}`),
  getProfile: () => api.get('/api/v1/profile'),
  updateProfile: (data: { key: string; value: string }) =>
    api.post('/api/v1/profile', data),
  getNotifications: () => api.get('/api/v1/notifications'),
  markNotificationRead: (id: string) =>
    api.post(`/api/v1/notifications/read/${id}`),
  deleteNotification: (id: string) =>
    api.delete(`/api/v1/notifications/${id}`),
};

export default api;
