import React, { useState, useEffect } from 'react';
import { configAPI } from '../services/api';
import { useAuth } from '../context/AuthContext';

export default function SystemSettings() {
    const { isAdmin } = useAuth();
    const [stopLineY, setStopLineY] = useState(468);
    const [confThreshold, setConfThreshold] = useState(0.22);
    const [yoloModel, setYoloModel] = useState('yolo11n.pt');
    const [cameraLocation, setCameraLocation] = useState('Ngã Tư Hòa Khánh, Q. Liên Chiểu, TP. Đà Nẵng');
    const [saving, setSaving] = useState(false);
    const [saveResult, setSaveResult] = useState(null); // 'ok' | 'error'
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        // Load from DB
        configAPI.getConfig()
            .then(res => {
                if (res.data) {
                    if (res.data.STOP_LINE_Y !== undefined) setStopLineY(Number(res.data.STOP_LINE_Y));
                    if (res.data.YOLO_CONF !== undefined) setConfThreshold(Number(res.data.YOLO_CONF));
                    if (res.data.YOLO_MODEL) setYoloModel(res.data.YOLO_MODEL);
                    if (res.data.CAMERA_LOCATION) setCameraLocation(res.data.CAMERA_LOCATION);
                }
            })
            .catch(() => {
                // Fallback to localStorage cache
                const cached = localStorage.getItem('PBL4_CONFIG');
                if (cached) try {
                    const p = JSON.parse(cached);
                    if (p.stopLineY) setStopLineY(Number(p.stopLineY));
                    if (p.confThreshold) setConfThreshold(Number(p.confThreshold));
                } catch {}
            })
            .finally(() => setLoading(false));
    }, []);

    async function handleSave(e) {
        e.preventDefault();
        setSaving(true);
        setSaveResult(null);
        try {
            await configAPI.saveConfig({
                STOP_LINE_Y: stopLineY,
                YOLO_CONF: confThreshold,
                YOLO_MODEL: yoloModel,
                CAMERA_LOCATION: cameraLocation,
            });
            // Also cache locally
            localStorage.setItem('PBL4_CONFIG', JSON.stringify({ stopLineY, confThreshold }));
            setSaveResult('ok');
        } catch {
            setSaveResult('error');
        } finally {
            setSaving(false);
            setTimeout(() => setSaveResult(null), 4000);
        }
    }

    return (
        <div style={{ padding: '24px', display: 'flex', flexDirection: 'column', gap: '20px', maxWidth: '900px' }}>

            {/* Page header */}
            <div>
                <h1 style={{ fontSize: '17px', fontWeight: 800, color: 'var(--t-primary)', margin: 0 }}>
                    Cấu Hình Tham Số Hệ Thống
                </h1>
                <div style={{ fontSize: '12.5px', color: 'var(--t-muted)', marginTop: '4px' }}>
                    Các tham số vận hành được đồng bộ vào cơ sở dữ liệu MySQL (bảng <code style={{ fontFamily: 'var(--mono)', fontSize: '11px', background: 'rgba(255,255,255,0.07)', padding: '1px 5px', borderRadius: '4px' }}>system_config</code>)
                </div>
            </div>

            {!isAdmin && (
                <div style={{
                    display: 'flex', alignItems: 'center', gap: '10px',
                    background: 'rgba(245,158,11,0.08)',
                    border: '1px solid rgba(245,158,11,0.2)',
                    borderRadius: '10px',
                    padding: '12px 16px',
                }}>
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#fcd34d" strokeWidth="2" style={{ flexShrink: 0 }}>
                        <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
                    </svg>
                    <span style={{ fontSize: '12.5px', color: '#fcd34d' }}>
                        Chỉ Quản Trị Viên (ADMIN) mới có quyền thay đổi cấu hình hệ thống.
                    </span>
                </div>
            )}

            <form onSubmit={handleSave} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>

                {/* AI parameters section */}
                <Section title="Tham Số Mô Hình AI" icon={
                    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="3"/><path d="M12 1v4M12 19v4M4.22 4.22l2.83 2.83M16.95 16.95l2.83 2.83M1 12h4M19 12h4M4.22 19.78l2.83-2.83M16.95 7.05l2.83-2.83"/></svg>
                }>
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
                        <FormField
                            label="Tọa Độ Vạch Dừng Ảo (Stop Line Y)"
                            description="Vị trí đường kẻ ngang vạch dừng trên khung hình video (pixel)"
                            hint="Mặc định: 468px — Camera ngã tư Hòa Khánh"
                        >
                            <input
                                className="input-field"
                                type="number"
                                value={stopLineY}
                                onChange={e => setStopLineY(Number(e.target.value))}
                                disabled={!isAdmin}
                                min={100} max={900}
                                style={{ fontFamily: 'var(--mono)', opacity: isAdmin ? 1 : 0.5 }}
                            />
                        </FormField>

                        <FormField
                            label="Ngưỡng Tin Cậy Tối Thiểu (Confidence)"
                            description="Ngưỡng lọc nhiễu phát hiện phương tiện của mô hình YOLO11"
                            hint="0.22 = bắt dính xe máy ở xa, 0.45+ = ít false-positive"
                        >
                            <input
                                className="input-field"
                                type="number"
                                step="0.01" min="0.1" max="0.9"
                                value={confThreshold}
                                onChange={e => setConfThreshold(Number(e.target.value))}
                                disabled={!isAdmin}
                                style={{ fontFamily: 'var(--mono)', opacity: isAdmin ? 1 : 0.5 }}
                            />
                        </FormField>

                        <FormField
                            label="Phiên Bản Mô Hình YOLO"
                            description="Tệp trọng số YOLO11 được nạp vào AI Engine"
                            hint="yolo11n.pt (Nano 30FPS) · yolo11s.pt · yolo11m.pt"
                        >
                            <select
                                className="input-field"
                                value={yoloModel}
                                onChange={e => setYoloModel(e.target.value)}
                                disabled={!isAdmin}
                                style={{ fontFamily: 'var(--mono)', opacity: isAdmin ? 1 : 0.5, cursor: isAdmin ? 'pointer' : 'not-allowed' }}
                            >
                                <option value="yolo11n.pt">yolo11n.pt — Nano (2.6M) · 30 FPS</option>
                                <option value="yolo11s.pt">yolo11s.pt — Small (9.4M)</option>
                                <option value="yolo11m.pt">yolo11m.pt — Medium (20M) · Cao nhất</option>
                            </select>
                        </FormField>

                        <FormField
                            label="Vị Trí Trạm Giám Sát"
                            description="Tên đường / Nút giao thông đặt camera"
                            hint="Hiển thị trong thẻ vi phạm và báo cáo xuất"
                        >
                            <input
                                className="input-field"
                                type="text"
                                value={cameraLocation}
                                onChange={e => setCameraLocation(e.target.value)}
                                disabled={!isAdmin}
                                style={{ opacity: isAdmin ? 1 : 0.5 }}
                            />
                        </FormField>
                    </div>
                </Section>

                {/* Save row */}
                {isAdmin && (
                    <div style={{ display: 'flex', justifyContent: 'flex-end', alignItems: 'center', gap: '14px' }}>
                        {saveResult === 'ok' && (
                            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: '#86efac', fontSize: '12.5px' }}>
                                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><polyline points="20 6 9 17 4 12"/></svg>
                                Đã lưu cấu hình vào MySQL thành công
                            </div>
                        )}
                        {saveResult === 'error' && (
                            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: '#fca5a5', fontSize: '12.5px' }}>
                                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>
                                Lỗi lưu cấu hình — backend chưa kết nối
                            </div>
                        )}
                        <button type="submit" className="btn btn-primary" disabled={saving}>
                            {saving ? <><div className="spinner" /><span>Đang lưu...</span></> : 'Lưu Cấu Hình'}
                        </button>
                    </div>
                )}
            </form>

            {/* System info section */}
            <Section title="Thông Tin Hệ Thống" icon={
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
            }>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '12px' }}>
                    <InfoCard label="Backend" value="Spring Boot 4.1 · JDK 21" sub="Port 8080 · MySQL 8.0" color="blue" />
                    <InfoCard label="AI Engine" value="YOLO11 + ViT 98.92%" sub="ByteTrack · Python 3.10" color="purple" />
                    <InfoCard label="Hardware" value="ESP32 DevKit V1" sub="MQTT · OLED SSD1306" color="amber" />
                    <InfoCard label="Cloud" value="Cloudinary CDN" sub="Lưu ảnh bằng chứng vi phạm" color="green" />
                    <InfoCard label="Real-time" value="WebSocket STOMP" sub="Topic: /topic/violations" color="blue" />
                    <InfoCard label="Pháp Lý" value="Nghị Định 168/2024/NĐ-CP" sub="Bộ luật xử phạt vi phạm" color="red" />
                </div>
            </Section>
        </div>
    );
}

function Section({ title, icon, children }) {
    return (
        <div style={{
            background: 'var(--c-surface)',
            border: '1px solid var(--c-border)',
            borderRadius: 'var(--r-xl)',
            overflow: 'hidden',
        }}>
            <div style={{
                padding: '12px 18px',
                borderBottom: '1px solid var(--c-border)',
                background: 'var(--c-bg-2)',
                display: 'flex', alignItems: 'center', gap: '8px',
            }}>
                <span style={{ color: 'var(--t-muted)' }}>{icon}</span>
                <span style={{ fontSize: '12.5px', fontWeight: 700, color: 'var(--t-secondary)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                    {title}
                </span>
            </div>
            <div style={{ padding: '18px' }}>{children}</div>
        </div>
    );
}

function FormField({ label, description, hint, children }) {
    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            <label style={{ fontSize: '12px', fontWeight: 700, color: 'var(--t-secondary)', letterSpacing: '0.3px' }}>
                {label}
            </label>
            {children}
            {hint && <div style={{ fontSize: '10.5px', color: 'var(--t-muted)', fontFamily: 'var(--mono)' }}>{hint}</div>}
        </div>
    );
}

function InfoCard({ label, value, sub, color }) {
    const colors = {
        blue:   { bg: '#eff6ff', border: '#bfdbfe', text: '#1e40af' },
        purple: { bg: '#f5f3ff', border: '#ddd6fe', text: '#5b21b6' },
        amber:  { bg: '#fffbeb', border: '#fde68a', text: '#92400e' },
        green:  { bg: '#f0fdf4', border: '#bbf7d0', text: '#166534' },
        red:    { bg: '#fef2f2', border: '#fecaca', text: '#991b1b' },
    };
    const c = colors[color] || colors.blue;
    return (
        <div style={{
            backgroundColor: c.bg,
            border: `1px solid ${c.border}`,
            borderRadius: '8px',
            padding: '12px 14px',
        }}>
            <div style={{ fontSize: '10.5px', fontWeight: 700, color: '#64748b', letterSpacing: '0.5px', textTransform: 'uppercase', marginBottom: '4px' }}>{label}</div>
            <div style={{ fontSize: '13px', fontWeight: 700, color: c.text, marginBottom: '2px' }}>{value}</div>
            <div style={{ fontSize: '11px', color: '#64748b' }}>{sub}</div>
        </div>
    );
}
