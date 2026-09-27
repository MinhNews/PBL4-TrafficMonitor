import React, { useState, useEffect } from 'react';
import { AuthProvider, useAuth } from './context/AuthContext';
import LoginPage from './pages/LoginPage';
import Sidebar from './components/layout/Sidebar';
import Navbar from './components/layout/Navbar';
import Dashboard from './pages/Dashboard';
import ViolationsManager from './pages/ViolationsManager';
import CamerasMap from './pages/CamerasMap';
import SystemSettings from './pages/SystemSettings';
import ViolationModal from './components/violations/ViolationModal';

function AppShell() {
    const { isAuthenticated, loading } = useAuth();
    const [currentTab, setTab] = useState('dashboard');
    const [selectedViolation, setSelectedViolation] = useState(null);
    const [violationCount, setViolationCount] = useState(0);

    // Show loading screen while restoring session
    if (loading) {
        return (
            <div style={{
                minHeight: '100vh',
                background: 'var(--c-bg)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                flexDirection: 'column',
                gap: '16px',
            }}>
                <div className="spinner" style={{ width: '28px', height: '28px', borderWidth: '3px' }} />
                <div style={{ fontSize: '12px', color: 'var(--t-muted)', letterSpacing: '0.5px' }}>
                    Đang khôi phục phiên làm việc...
                </div>
            </div>
        );
    }

    if (!isAuthenticated) {
        return <LoginPage />;
    }

    return (
        <div style={{ display: 'flex', width: '100%', height: '100vh', overflow: 'hidden', background: 'var(--c-bg)' }}>
            <Sidebar currentTab={currentTab} setTab={setTab} />

            <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0, overflow: 'hidden' }}>
                <Navbar violationCount={violationCount} />

                <main style={{ flex: 1, overflowY: 'auto', overflowX: 'hidden' }}>
                    {currentTab === 'dashboard' && (
                        <Dashboard
                            onOpenModal={v => setSelectedViolation(v)}
                            onViolationCountChange={setViolationCount}
                        />
                    )}
                    {currentTab === 'violations' && (
                        <ViolationsManager onOpenModal={v => setSelectedViolation(v)} />
                    )}
                    {currentTab === 'cameras' && <CamerasMap />}
                    {currentTab === 'settings' && <SystemSettings />}
                </main>
            </div>

            {selectedViolation && (
                <ViolationModal
                    violation={selectedViolation}
                    onClose={() => setSelectedViolation(null)}
                    onConfirm={() => setSelectedViolation(null)}
                    onDismiss={() => setSelectedViolation(null)}
                />
            )}
        </div>
    );
}

export default function App() {
    return (
        <AuthProvider>
            <AppShell />
        </AuthProvider>
    );
}