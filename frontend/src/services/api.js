import axios from 'axios';

const API = axios.create({
    baseURL: 'http://localhost:8080/api',
    timeout: 10000,
});

export const statsAPI = {
    getToday: () => API.get('/stats/today'),
    getHourly: (date) => API.get(`/stats/hourly?date=${date || ''}`),
};

export const violationAPI = {
    getAll: (params) => API.get('/violations', { params }),
    getById: (id) => API.get(`/violations/${id}`),
    confirm: (id, notes) => API.patch(`/violations/${id}/confirm`, { notes }),
    dismiss: (id, notes) => API.patch(`/violations/${id}/dismiss`, { notes }),
};

export const cameraAPI = {
    getAll: () => API.get('/cameras'),
};

export default API;