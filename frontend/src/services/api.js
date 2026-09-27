import axios from 'axios';

const API = axios.create({
    baseURL: 'http://localhost:8080/api',
    timeout: 12000,
});

// Attach JWT token to every request automatically
API.interceptors.request.use((config) => {
    const token = localStorage.getItem('jwt_token');
    if (token) {
        config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
});

// Handle 401 globally — force re-login
API.interceptors.response.use(
    (res) => res,
    (err) => {
        if (err.response?.status === 401) {
            localStorage.removeItem('jwt_token');
            localStorage.removeItem('user_info');
            window.dispatchEvent(new Event('auth:logout'));
        }
        return Promise.reject(err);
    }
);

export const authAPI = {
    login: (username, password) => API.post('/auth/login', { username, password }),
    me: () => API.get('/auth/me'),
    logout: () => API.post('/auth/logout'),
    validate: () => API.post('/auth/validate'),
};

export const statsAPI = {
    getToday: () => API.get('/stats/today'),
    getHourly: (date) => API.get(date ? `/stats/hourly?date=${date}` : '/stats/hourly'),
};

export const violationAPI = {
    getAll: (params) => API.get('/violations', { params }),
    getById: (id) => API.get(`/violations/${id}`),
    confirm: (id, notes) => API.patch(`/violations/${id}/confirm`, { notes }),
    dismiss: (id, notes) => API.patch(`/violations/${id}/dismiss`, { notes }),
    testAlert: () => API.post('/violations/test-alert'),
};

export const configAPI = {
    getConfig: () => API.get('/config'),
    saveConfig: (data) => API.post('/config', data),
};

export const cameraAPI = {
    getAll: () => API.get('/cameras'),
};

export default API;