import React, { useState, useEffect } from 'react';
import { useAuth } from '../../context/AuthContext';

export default function Navbar({ violationCount = 0 }) {
    const { user } = useAuth();
    const [timeStr, setTimeStr] = useState('');

    useEffect(() => {
        function tick() {
            const now = new Date();
            const t = now.toLocaleTimeString('vi-VN', { hour12: false });
            const d = now.toLocaleDateString('vi-VN', { day: '2-digit', month: '2-digit', year: 'numeric' });
            setTimeStr(`${t} — ${d}`);
        }
        tick();
        const id = setInterval(tick, 1000);
        return () => clearInterval(id);
    }, []);

    return (
        <header style={{
            height: '60px',
            backgroundColor: '#ffffff',
            borderBottom: '1px solid var(--c-border)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '0 24px',
            position: 'sticky',
            top: 0,
            zIndex: 40,
            flexShrink: 0,
            boxShadow: '0 1px 2px 0 rgba(0, 0, 0, 0.03)',
        }}>
            {/* Left: Official Government & Police Identity */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                <div style={{
                    width: '32px', height: '32px',
                    borderRadius: '6px',
                    backgroundColor: '#1d4ed8',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    color: '#ffffff',
                    flexShrink: 0,
                }}>
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
                    </svg>
                </div>
                <div>
                    <div style={{
                        fontSize: '10px',
                        fontWeight: 800,
                        color: '#1d4ed8',
                        letterSpacing: '0.8px',
                        textTransform: 'uppercase',
                        lineHeight: 1.1
                    }}>
                        Cục Cảnh Sát Giao Thông — Bộ Công An
                    </div>
                    <div style={{
                        fontSize: '13.5px',
                        fontWeight: 800,
                        color: 'var(--t-primary)',
                        lineHeight: 1.3
                    }}>
                        Trung Tâm Giám Sát &amp; Xử Phạt Giao Thông Thông Minh (ITS Đà Nẵng)
                    </div>
                </div>
            </div>

            {/* Right: Operational Status, Violation Counter, Clock, Officer Profile */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
                {/* Clean Status Indicator */}
                <div style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px',
                    backgroundColor: '#f0fdf4',
                    border: '1px solid #bbf7d0',
                    borderRadius: '4px',
                    padding: '4px 10px',
                    fontSize: '11.5px',
                    fontWeight: 700,
                    color: '#15803d'
                }}>
                    <span style={{ width: 6, height: 6, borderRadius: '50%', backgroundColor: '#16a34a' }} />
                    Hạ Tầng Trực Tuyến
                </div>

                {/* Violation Count Badge */}
                {violationCount > 0 && (
                    <div style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '6px',
                        backgroundColor: '#fef2f2',
                        border: '1px solid #fecaca',
                        borderRadius: '4px',
                        padding: '4px 10px',
                        fontSize: '11.5px',
                        fontWeight: 700,
                        color: '#991b1b'
                    }}>
                        <span style={{ width: 6, height: 6, borderRadius: '50%', backgroundColor: '#dc2626' }} />
                        {violationCount} Vi Phạm Hôm Nay
                    </div>
                )}

                {/* Official System Clock */}
                <div style={{
                    fontFamily: 'var(--mono)',
                    fontSize: '12px',
                    fontWeight: 600,
                    color: '#334155',
                    backgroundColor: '#f8fafc',
                    border: '1px solid var(--c-border)',
                    borderRadius: '4px',
                    padding: '4px 10px',
                }}>
                    {timeStr}
                </div>

                {/* Current Officer Profile */}
                <div style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px',
                    paddingLeft: '12px',
                    borderLeft: '1px solid var(--c-border)'
                }}>
                    <div style={{
                        width: '30px', height: '30px',
                        borderRadius: '50%',
                        backgroundColor: '#1d4ed8',
                        color: '#ffffff',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        fontWeight: 800,
                        fontSize: '12px'
                    }}>
                        {user?.fullName?.charAt(0) || user?.username?.charAt(0)?.toUpperCase() || 'C'}
                    </div>
                    <div style={{ display: 'flex', flexDirection: 'column' }}>
                        <span style={{ fontSize: '12.5px', fontWeight: 700, color: 'var(--t-primary)', lineHeight: 1.2 }}>
                            {user?.fullName || user?.username || 'Cán Bộ Trực Ban'}
                        </span>
                        <span style={{ fontSize: '10.5px', color: '#64748b' }}>
                            {user?.role === 'ADMIN' ? 'Chỉ Huy Trực Ban' : 'Cán Bộ Giám Sát'}
                        </span>
                    </div>
                </div>
            </div>
        </header>
    );
}
