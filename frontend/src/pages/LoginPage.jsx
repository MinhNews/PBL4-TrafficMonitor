import React, { useState, useRef, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';

export default function LoginPage() {
    const { login } = useAuth();
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);
    const [showPass, setShowPass] = useState(false);
    const usernameRef = useRef();

    useEffect(() => { usernameRef.current?.focus(); }, []);

    async function handleSubmit(e) {
        e.preventDefault();
        if (!username.trim() || !password) {
            setError('Vui lòng nhập đầy đủ tên đăng nhập và mật khẩu.');
            return;
        }
        setLoading(true);
        setError('');
        try {
            await login(username.trim(), password);
        } catch (err) {
            const msg = err.response?.data?.error || 'Tên đăng nhập hoặc mật khẩu không chính xác.';
            setError(msg);
        } finally {
            setLoading(false);
        }
    }

    function quickFill(u, p) {
        setUsername(u);
        setPassword(p);
        setError('');
    }

    return (
        <div style={{
            minHeight: '100vh',
            backgroundColor: '#f1f5f9',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            fontFamily: 'var(--font)',
            padding: '24px',
        }}>
            {/* Top Brand Banner */}
            <div style={{ textAlign: 'center', marginBottom: '24px' }}>
                <div style={{
                    width: '54px', height: '54px',
                    borderRadius: '12px',
                    backgroundColor: '#1d4ed8',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    margin: '0 auto 14px',
                    boxShadow: '0 4px 12px rgba(29, 78, 216, 0.25)',
                }}>
                    <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#ffffff" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
                    </svg>
                </div>
                <h1 style={{ fontSize: '20px', fontWeight: 800, color: '#0f172a', margin: '0 0 4px 0', textTransform: 'uppercase', letterSpacing: '0.4px' }}>
                    Hệ Thống Giám Sát Giao Thông &amp; Phát Hiện Vi Phạm
                </h1>
                <p style={{ fontSize: '13px', color: '#64748b', margin: 0, fontWeight: 500 }}>
                    Trung Tâm Điều Hành Giao Thông Thông Minh ITS — Cổng Xác Thực Cán Bộ
                </p>
            </div>

            {/* Login Card */}
            <div style={{
                backgroundColor: '#ffffff',
                border: '1px solid #cbd5e1',
                borderRadius: '12px',
                width: '100%',
                maxWidth: '440px',
                padding: '32px',
                boxShadow: '0 10px 25px -5px rgba(0, 0, 0, 0.05), 0 8px 10px -6px rgba(0, 0, 0, 0.03)',
            }}>
                <div style={{ marginBottom: '22px', borderBottom: '1px solid #f1f5f9', paddingBottom: '16px' }}>
                    <h2 style={{ fontSize: '16px', fontWeight: 700, color: '#0f172a', margin: '0 0 4px 0' }}>
                        Đăng Nhập Hệ Thống
                    </h2>
                    <p style={{ fontSize: '12px', color: '#64748b', margin: 0 }}>
                        Nhập thông tin định danh để truy cập bảng điều khiển giám sát
                    </p>
                </div>

                {error && (
                    <div style={{
                        backgroundColor: '#fef2f2',
                        border: '1px solid #fecaca',
                        borderRadius: '6px',
                        padding: '10px 14px',
                        fontSize: '12.5px',
                        color: '#991b1b',
                        marginBottom: '18px',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '8px',
                    }}>
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#dc2626" strokeWidth="2" style={{ flexShrink: 0 }}>
                            <circle cx="12" cy="12" r="10" /><line x1="12" y1="8" x2="12" y2="12" /><line x1="12" y1="16" x2="12.01" y2="16" />
                        </svg>
                        <span>{error}</span>
                    </div>
                )}

                <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                    <div>
                        <label style={{ display: 'block', fontSize: '12.5px', fontWeight: 600, color: '#334155', marginBottom: '6px' }}>
                            Tên Đăng Nhập
                        </label>
                        <input
                            ref={usernameRef}
                            type="text"
                            value={username}
                            onChange={e => setUsername(e.target.value)}
                            placeholder="Nhập tên đăng nhập (admin / officer)..."
                            className="input-field"
                            disabled={loading}
                        />
                    </div>

                    <div>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                            <label style={{ fontSize: '12.5px', fontWeight: 600, color: '#334155' }}>
                                Mật Khẩu
                            </label>
                            <button
                                type="button"
                                onClick={() => setShowPass(!showPass)}
                                style={{ fontSize: '11px', color: '#1d4ed8', fontWeight: 600, background: 'none', border: 'none', cursor: 'pointer' }}
                            >
                                {showPass ? 'Ẩn mật khẩu' : 'Hiện mật khẩu'}
                            </button>
                        </div>
                        <input
                            type={showPass ? 'text' : 'password'}
                            value={password}
                            onChange={e => setPassword(e.target.value)}
                            placeholder="Nhập mật khẩu xác thực..."
                            className="input-field"
                            disabled={loading}
                        />
                    </div>

                    <button
                        type="submit"
                        disabled={loading}
                        className="btn btn-primary"
                        style={{
                            width: '100%',
                            padding: '10px',
                            fontSize: '13.5px',
                            fontWeight: 700,
                            marginTop: '6px',
                        }}
                    >
                        {loading ? 'Đang Xác Thực Phiên Làm Việc...' : 'Đăng Nhập Vào Hệ Thống'}
                    </button>
                </form>

                {/* Quick Credentials Helper */}
                <div style={{
                    marginTop: '24px',
                    paddingTop: '18px',
                    borderTop: '1px solid #f1f5f9',
                }}>
                    <span style={{ fontSize: '11px', fontWeight: 700, color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.4px', display: 'block', marginBottom: '8px' }}>
                        Tài Khoản Kiểm Thử Nhanh:
                    </span>
                    <div style={{ display: 'flex', gap: '8px' }}>
                        <button
                            type="button"
                            onClick={() => quickFill('admin', 'admin@2026')}
                            style={{
                                flex: 1,
                                padding: '8px 10px',
                                borderRadius: '6px',
                                backgroundColor: '#f8fafc',
                                border: '1px solid #e2e8f0',
                                textAlign: 'left',
                                cursor: 'pointer',
                            }}
                        >
                            <div style={{ fontSize: '12px', fontWeight: 700, color: '#1d4ed8' }}>Quản Trị Viên</div>
                            <div style={{ fontSize: '11px', color: '#64748b' }}>admin / admin@2026</div>
                        </button>

                        <button
                            type="button"
                            onClick={() => quickFill('officer', 'csgt@2026')}
                            style={{
                                flex: 1,
                                padding: '8px 10px',
                                borderRadius: '6px',
                                backgroundColor: '#f8fafc',
                                border: '1px solid #e2e8f0',
                                textAlign: 'left',
                                cursor: 'pointer',
                            }}
                        >
                            <div style={{ fontSize: '12px', fontWeight: 700, color: '#16a34a' }}>Cán Bộ Trực Ban</div>
                            <div style={{ fontSize: '11px', color: '#64748b' }}>officer / csgt@2026</div>
                        </button>
                    </div>
                </div>
            </div>

            {/* Footer Legal */}
            <div style={{ marginTop: '24px', textAlign: 'center', fontSize: '11.5px', color: '#94a3b8' }}>
                Hệ Thống Giám Sát Xử Phạt Vi Phạm Giao Thông — Phiên Bản 2026
            </div>
        </div>
    );
}
