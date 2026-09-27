import React from 'react';
import { useAuth } from '../../context/AuthContext';

const NAV_ITEMS = [
    {
        id: 'dashboard',
        label: 'Trung Tâm Giám Sát',
        sublabel: 'Giám sát trực tiếp AI',
        icon: (
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <rect x="2" y="3" width="8" height="9" rx="1.5"/>
                <rect x="14" y="3" width="8" height="5" rx="1.5"/>
                <rect x="14" y="12" width="8" height="9" rx="1.5"/>
                <rect x="2" y="16" width="8" height="5" rx="1.5"/>
            </svg>
        ),
        roles: ['ADMIN', 'OFFICER'],
    },
    {
        id: 'violations',
        label: 'Hồ Sơ Vi Phạm',
        sublabel: 'Biên bản & xử phạt',
        icon: (
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/>
                <polyline points="14 2 14 8 20 8"/>
                <line x1="16" y1="13" x2="8" y2="13"/>
                <line x1="16" y1="17" x2="8" y2="17"/>
            </svg>
        ),
        roles: ['ADMIN', 'OFFICER'],
    },
    {
        id: 'cameras',
        label: 'Mạng Lưới Camera',
        sublabel: 'Hạ tầng & bản đồ GIS',
        icon: (
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M23 7l-7 5 7 5V7z"/>
                <rect x="1" y="5" width="15" height="14" rx="2" ry="2"/>
            </svg>
        ),
        roles: ['ADMIN', 'OFFICER'],
    },
    {
        id: 'settings',
        label: 'Cấu Hình Hệ Thống',
        sublabel: 'Tham số & vạch dừng',
        icon: (
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="12" cy="12" r="3"/>
                <path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83 2 2 0 01-2.83 0l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-4 0v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83-2.83l.06-.06A1.65 1.65 0 004.68 15a1.65 1.65 0 00-1.51-1H3a2 2 0 010-4h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 012.83-2.83l.06.06A1.65 1.65 0 009 4.68a1.65 1.65 0 001-1.51V3a2 2 0 014 0v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 2.83l-.06.06A1.65 1.65 0 0019.4 9a1.65 1.65 0 001.51 1H21a2 2 0 010 4h-.09a1.65 1.65 0 00-1.51 1z"/>
            </svg>
        ),
        adminOnly: true,
        roles: ['ADMIN'],
    },
];

export default function Sidebar({ currentTab, setTab }) {
    const { user, logout, isAdmin } = useAuth();

    const visibleItems = NAV_ITEMS.filter(item =>
        !item.adminOnly || isAdmin
    );

    return (
        <aside style={{
            width: 'var(--sidebar-w)',
            minWidth: 'var(--sidebar-w)',
            backgroundColor: '#0f172a',
            borderRight: '1px solid #1e293b',
            display: 'flex',
            flexDirection: 'column',
            height: '100vh',
            position: 'sticky',
            top: 0,
            zIndex: 50,
            userSelect: 'none',
        }}>
            {/* National / Police Department Brand */}
            <div style={{
                padding: '20px 18px',
                borderBottom: '1px solid #1e293b',
                display: 'flex',
                alignItems: 'center',
                gap: '12px',
            }}>
                <div style={{
                    width: '38px', height: '38px', flexShrink: 0,
                    backgroundColor: '#1d4ed8',
                    borderRadius: '8px',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    boxShadow: '0 2px 8px rgba(0,0,0,0.3)',
                }}>
                    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#ffffff" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
                    </svg>
                </div>
                <div style={{ minWidth: 0 }}>
                    <div style={{ fontSize: '13px', fontWeight: 800, color: '#ffffff', letterSpacing: '0.3px', textTransform: 'uppercase' }}>
                        CSGT · ITS ĐÀ NẴNG
                    </div>
                    <div style={{ fontSize: '10.5px', color: '#94a3b8' }}>
                        Giám Sát Giao Thông
                    </div>
                </div>
            </div>

            {/* Navigation links */}
            <nav style={{ flex: 1, padding: '16px 10px', display: 'flex', flexDirection: 'column', gap: '4px', overflowY: 'auto' }}>
                <div style={{ padding: '4px 10px 8px', fontSize: '10.5px', fontWeight: 700, letterSpacing: '0.8px', color: '#64748b', textTransform: 'uppercase' }}>
                    Phân Hệ Vận Hành
                </div>

                {visibleItems.map(item => {
                    const active = currentTab === item.id;
                    return (
                        <button
                            key={item.id}
                            onClick={() => setTab(item.id)}
                            style={{
                                display: 'flex',
                                alignItems: 'center',
                                gap: '12px',
                                width: '100%',
                                padding: '10px 12px',
                                borderRadius: '6px',
                                border: 'none',
                                backgroundColor: active ? '#1d4ed8' : 'transparent',
                                color: active ? '#ffffff' : '#94a3b8',
                                cursor: 'pointer',
                                textAlign: 'left',
                                transition: 'all 0.15s ease',
                            }}
                        >
                            <span style={{ color: active ? '#ffffff' : '#64748b', display: 'flex', flexShrink: 0 }}>
                                {item.icon}
                            </span>
                            <div style={{ minWidth: 0, flex: 1 }}>
                                <div style={{ fontSize: '12.5px', fontWeight: active ? 700 : 500, color: active ? '#ffffff' : '#e2e8f0', lineHeight: 1.3 }}>
                                    {item.label}
                                </div>
                                <div style={{ fontSize: '10px', color: active ? 'rgba(255,255,255,0.7)' : '#64748b', marginTop: '1px' }}>
                                    {item.sublabel}
                                </div>
                            </div>
                        </button>
                    );
                })}
            </nav>

            {/* Officer footer info & Logout */}
            <div style={{
                padding: '14px 16px',
                borderTop: '1px solid #1e293b',
                backgroundColor: '#0a0f1d',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
            }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px', minWidth: 0 }}>
                    <div style={{
                        width: '32px', height: '32px', borderRadius: '50%',
                        backgroundColor: '#1e293b',
                        border: '1px solid #334155',
                        display: 'flex', alignItems: 'center', justifyContent: 'center',
                        color: '#94a3b8', fontSize: '12px', fontWeight: 700,
                        flexShrink: 0
                    }}>
                        {user?.username?.slice(0, 2).toUpperCase() || 'AD'}
                    </div>
                    <div style={{ minWidth: 0 }}>
                        <div style={{ fontSize: '12px', fontWeight: 700, color: '#f1f5f9', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                            {user?.username || 'admin'}
                        </div>
                        <div style={{ fontSize: '10px', color: '#64748b' }}>
                            {user?.role === 'ADMIN' ? 'Quản Trị Viên' : 'Cán Bộ Trực Ban'}
                        </div>
                    </div>
                </div>

                <button
                    onClick={logout}
                    title="Đăng xuất khỏi phiên làm việc"
                    style={{
                        padding: '6px',
                        borderRadius: '6px',
                        backgroundColor: 'transparent',
                        color: '#64748b',
                        border: 'none',
                        cursor: 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                    }}
                >
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4M16 17l5-5-5-5M21 12H9"/>
                    </svg>
                </button>
            </div>
        </aside>
    );
}
