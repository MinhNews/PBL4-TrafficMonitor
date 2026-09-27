import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { authAPI } from '../services/api';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
    const [user, setUser] = useState(null);
    const [loading, setLoading] = useState(true); // true while validating stored token

    // On app start — try to restore session from localStorage
    useEffect(() => {
        const token = localStorage.getItem('jwt_token');
        const stored = localStorage.getItem('user_info');
        if (token && stored) {
            try {
                const parsed = JSON.parse(stored);
                setUser(parsed); // Optimistically set user
                // Validate token with backend
                authAPI.me()
                    .then(res => setUser(res.data))
                    .catch(() => logout()) // Invalid → force logout
                    .finally(() => setLoading(false));
            } catch {
                logout();
                setLoading(false);
            }
        } else {
            setLoading(false);
        }
    }, []);

    // Listen for 401 auto-logout events from API interceptor
    useEffect(() => {
        const handle = () => { setUser(null); };
        window.addEventListener('auth:logout', handle);
        return () => window.removeEventListener('auth:logout', handle);
    }, []);

    const login = useCallback(async (username, password) => {
        const res = await authAPI.login(username, password);
        const data = res.data;
        localStorage.setItem('jwt_token', data.token);
        localStorage.setItem('user_info', JSON.stringify({
            username: data.username,
            fullName: data.fullName,
            role: data.role,
            email: data.email,
            lastLogin: data.lastLogin,
        }));
        setUser({
            username: data.username,
            fullName: data.fullName,
            role: data.role,
            email: data.email,
            lastLogin: data.lastLogin,
        });
        return data;
    }, []);

    const logout = useCallback(() => {
        localStorage.removeItem('jwt_token');
        localStorage.removeItem('user_info');
        setUser(null);
        authAPI.logout().catch(() => {});
    }, []);

    const isAdmin = user?.role === 'ADMIN';
    const isAuthenticated = !!user;

    return (
        <AuthContext.Provider value={{ user, login, logout, loading, isAdmin, isAuthenticated }}>
            {children}
        </AuthContext.Provider>
    );
}

export function useAuth() {
    const ctx = useContext(AuthContext);
    if (!ctx) throw new Error('useAuth must be used within AuthProvider');
    return ctx;
}
