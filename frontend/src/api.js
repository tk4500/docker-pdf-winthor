import axios from 'axios';

const api = axios.create({
  // No dev local usa o proxy do Vite. No Docker usa o proxy do Nginx.
  baseURL: '/api' 
});

// Interceptor para injetar o Token em todas as requisições automaticamente
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Interceptor para deslogar se o token expirar (Erro 401)
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response && error.response.status === 401) {
      localStorage.removeItem('token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export default api;