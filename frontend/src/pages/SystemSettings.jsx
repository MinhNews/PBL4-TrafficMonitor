import React, { useState, useEffect } from 'react';
import { configAPI, aiAPI } from '../services/api';
import { useAuth } from '../context/AuthContext';

export default function SystemSettings() {
    const { isAdmin } = useAuth();

    // --- C2: cấu hình vạch dừng của AI (chỉnh trực tiếp trên AI đang chạy) ---
    const [stopLineRatio, setStopLineRatio] = useState(0.65);
    const [approachDirection, setApproachDirection] = useState('up');
    const [stopLineVisible, setStopLineVisible] = useState(true);
    const [aiDefaults, setAiDefaults] = useState({ stopLineRatio: 0.65, approachDirection: 'up', stopLineVisible: true });
    const [aiOnline, setAiOnline] = useState(null); // null = đang kiểm tra
    const [aiFrameHeight, setAiFrameHeight] = useState(720);
    const [aiSaving, setAiSaving] = useState(false);
    const [aiMessage, setAiMessage] = useState(null); // { type, text }

    // C2: đọc cấu hình thật từ AI Engine (nguồn chân lý) + kích thước khung hình
    useEffect(() => {
        let alive = true;
        Promise.allSettled([aiAPI.getConfig(), aiAPI.getStatus()])
            .then(([cfgRes, statusRes]) => {
                if (!alive) return;
                if (cfgRes.status === 'fulfilled') {
                    const cfg = cfgRes.value.data || {};
                    if (cfg.stopLineRatio != null) setStopLineRatio(Number(cfg.stopLineRatio));
                    if (cfg.approachDirection) setApproachDirection(String(cfg.approachDirection).toLowerCase());
                    if (typeof cfg.stopLineVisible === 'boolean') setStopLineVisible(cfg.stopLineVisible);
                    if (cfg.defaults) setAiDefaults({
                        stopLineRatio: Number(cfg.defaults.stopLineRatio),
                        approachDirection: String(cfg.defaults.approachDirection).toLowerCase(),
                        stopLineVisible: cfg.defaults.stopLineVisible !== false,
                    });
                }
                if (statusRes.status === 'fulfilled') {
                    setAiOnline(true);
                    const h = Number(statusRes.value.data?.height);
                    if (h > 0) setAiFrameHeight(h);
                } else {
                    setAiOnline(false);
                }
            });
        return () => { alive = false; };
    }, []);

    async function handleApplyAiConfig() {
        setAiSaving(true);
        setAiMessage(null);
        try {
            const res = await aiAPI.setConfig({ stopLineRatio, approachDirection, stopLineVisible });
            const applied = res.data?.settings || {};
            if (applied.stopLineRatio != null) setStopLineRatio(Number(applied.stopLineRatio));
            if (applied.approachDirection) setApproachDirection(String(applied.approachDirection).toLowerCase());
            if (typeof applied.stopLineVisible === 'boolean') setStopLineVisible(applied.stopLineVisible);
            setAiOnline(true);
            setAiMessage({
                type: 'ok',
                text: 'Đã áp dụng cho AI đang chạy. Vạch dừng mới có hiệu lực ngay, không cần restart.',
            });
            // Lưu bản sao vào MySQL chỉ để tra cứu (AI đọc cấu hình từ runtime_config.json)
            configAPI.saveConfig({
                STOP_LINE_RATIO: applied.stopLineRatio ?? stopLineRatio,
                APPROACH_DIRECTION: applied.approachDirection ?? approachDirection,
            }).catch(() => {});
        } catch (err) {
            setAiOnline(false);
            setAiMessage({
                type: 'error',
                text: err.response?.data?.message
                    || 'Không kết nối được AI Engine (localhost:5000). Hãy bật ai-service trước khi áp dụng.',
            });
        } finally {
            setAiSaving(false);
            setTimeout(() => setAiMessage(null), 7000);
        }
    }

    async function handleResetAiConfig() {
        setAiSaving(true);
        setAiMessage(null);
        try {
            const res = await aiAPI.resetConfig();
            const applied = res.data?.settings || aiDefaults;
            setStopLineRatio(Number(applied.stopLineRatio));
            setApproachDirection(String(applied.approachDirection).toLowerCase());
            if (typeof applied.stopLineVisible === 'boolean') setStopLineVisible(applied.stopLineVisible);
            setAiOnline(true);
            setAiMessage({ type: 'ok', text: 'Đã khôi phục vạch dừng mặc định trong config.py.' });
        } catch {
            setAiOnline(false);
            setAiMessage({ type: 'error', text: 'Không kết nối được AI Engine (localhost:5000).' });
        } finally {
            setAiSaving(false);
            setTimeout(() => setAiMessage(null), 7000);
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
                    Vạch dừng được áp dụng trực tiếp vào AI Engine (lưu tại{' '}
                    <code style={{ fontFamily: 'var(--mono)', fontSize: '11px', background: 'rgba(255,255,255,0.07)', padding: '1px 5px', borderRadius: '4px' }}>ai-service/runtime_config.json</code>).
                    Bảng <code style={{ fontFamily: 'var(--mono)', fontSize: '11px', background: 'rgba(255,255,255,0.07)', padding: '1px 5px', borderRadius: '4px' }}>system_config</code> chỉ giữ bản sao để tra cứu.
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

            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>

                {/* C2: Cấu hình vạch dừng áp dụng ngay cho AI đang chạy */}
                <Section title="Vạch Dừng AI (Áp Dụng Ngay)" icon={
                    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <line x1="3" y1="12" x2="21" y2="12"/><line x1="6" y1="7" x2="6" y2="17"/><line x1="12" y1="7" x2="12" y2="17"/><line x1="18" y1="7" x2="18" y2="17"/>
                    </svg>
                }>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '11.5px' }}>
                            <span style={{
                                width: '8px', height: '8px', borderRadius: '50%',
                                backgroundColor: aiOnline === null ? '#94a3b8' : aiOnline ? '#22c55e' : '#ef4444',
                                boxShadow: aiOnline === null ? 'none' : `0 0 6px ${aiOnline ? '#22c55e' : '#ef4444'}`,
                            }} />
                            <span style={{ color: 'var(--t-muted)' }}>
                                {aiOnline === null ? 'Đang kiểm tra AI Engine...'
                                    : aiOnline ? `AI Engine trực tuyến · khung ${aiFrameHeight}px`
                                    : 'AI Engine chưa chạy (port 5000) — bật ai-service để chỉnh trực tiếp'}
                            </span>
                        </div>

                        <div style={{ display: 'grid', gridTemplateColumns: '1.1fr 1fr', gap: '18px' }}>
                            <FormField
                                label={`Tỉ Lệ Vạch Dừng — ${stopLineRatio.toFixed(2)}`}
                                description="Vị trí vạch dừng tính theo chiều cao khung hình (0.05 – 0.95)"
                                hint={`Y ≈ ${Math.round(aiFrameHeight * stopLineRatio)} px · 0.65 = 65% chiều cao`}
                            >
                                <input
                                    type="range"
                                    min="0.30" max="0.90" step="0.01"
                                    value={stopLineRatio}
                                    onChange={e => setStopLineRatio(Number(e.target.value))}
                                    disabled={!isAdmin || aiOnline === false}
                                    style={{ width: '100%', accentColor: '#1d4ed8', opacity: isAdmin ? 1 : 0.5, cursor: isAdmin ? 'pointer' : 'not-allowed' }}
                                />
                                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '10px', color: 'var(--t-muted)', fontFamily: 'var(--mono)' }}>
                                    <span>0.30 (xa)</span>
                                    <span>0.65 mặc định</span>
                                    <span>0.90 (gần)</span>
                                </div>
                            </FormField>

                            <FormField
                                label="Chiều Xe Đi Qua Vạch"
                                description="Chỉ đếm xe cắt vạch theo đúng chiều này (chống đếm xe ngược chiều)"
                                hint="up: mép xe đi từ dưới lên (Y giảm) · down: đi từ trên xuống (Y tăng)"
                            >
                                <div style={{ display: 'flex', gap: '8px' }}>
                                    {[
                                        { value: 'up', label: '↑ Đi lên' },
                                        { value: 'down', label: '↓ Đi xuống' },
                                    ].map(opt => (
                                        <button
                                            key={opt.value}
                                            type="button"
                                            onClick={() => setApproachDirection(opt.value)}
                                            disabled={!isAdmin || aiOnline === false}
                                            style={{
                                                flex: 1, padding: '8px 10px', borderRadius: '6px', fontSize: '12.5px', fontWeight: 700,
                                                cursor: (!isAdmin || aiOnline === false) ? 'not-allowed' : 'pointer',
                                                border: approachDirection === opt.value ? '1.5px solid #1d4ed8' : '1px solid var(--c-border)',
                                                backgroundColor: approachDirection === opt.value ? 'rgba(29,78,216,0.12)' : 'transparent',
                                                color: approachDirection === opt.value ? '#60a5fa' : 'var(--t-secondary)',
                                            }}
                                        >
                                            {opt.label}
                                        </button>
                                    ))}
                                </div>
                            </FormField>
                        </div>

                        {/* C4: bật/tắt hiển thị vạch — chỉ đổi phần vẽ, không đổi logic vi phạm */}
                        <label style={{
                            display: 'flex', alignItems: 'center', gap: '9px',
                            fontSize: '12px', color: 'var(--t-secondary)',
                            cursor: (!isAdmin || aiOnline === false) ? 'not-allowed' : 'pointer',
                            opacity: (!isAdmin || aiOnline === false) ? 0.55 : 1,
                        }}>
                            <input
                                type="checkbox"
                                checked={stopLineVisible}
                                onChange={e => setStopLineVisible(e.target.checked)}
                                disabled={!isAdmin || aiOnline === false}
                                style={{ accentColor: '#1d4ed8', width: '15px', height: '15px' }}
                            />
                            <span>
                                <strong style={{ color: 'var(--t-primary)' }}>Hiện vạch dừng trên video</strong>
                                <span style={{ color: 'var(--t-muted)' }}> — chỉ ảnh hưởng hiển thị, AI vẫn tính vi phạm theo đúng vạch này</span>
                            </span>
                        </label>

                        <div style={{ fontSize: '11px', color: 'var(--t-muted)' }}>
                            Lưu ý: khi áp dụng vạch mới, AI sẽ làm mới bộ đếm của phiên (số “vi phạm phiên này” trên
                            Live Camera trở về 0) vì trạng thái xe so với vạch cũ không còn đúng. Bật/tắt hiển thị vạch
                            thì không làm mất bộ đếm.
                        </div>

                        {aiMessage && (
                            <div style={{
                                display: 'flex', alignItems: 'center', gap: '8px', fontSize: '12px',
                                padding: '9px 12px', borderRadius: '8px',
                                backgroundColor: aiMessage.type === 'ok' ? 'rgba(34,197,94,0.10)' : 'rgba(239,68,68,0.10)',
                                border: `1px solid ${aiMessage.type === 'ok' ? 'rgba(34,197,94,0.3)' : 'rgba(239,68,68,0.3)'}`,
                                color: aiMessage.type === 'ok' ? '#4ade80' : '#f87171',
                            }}>
                                <span>{aiMessage.type === 'ok' ? '✓' : '✕'}</span>
                                <span>{aiMessage.text}</span>
                            </div>
                        )}

                        {isAdmin && (
                            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
                                <button
                                    type="button"
                                    className="btn btn-secondary"
                                    onClick={handleResetAiConfig}
                                    disabled={aiSaving || aiOnline === false}
                                >
                                    Khôi Phục Mặc Định ({aiDefaults.stopLineRatio.toFixed(2)})
                                </button>
                                <button
                                    type="button"
                                    className="btn btn-primary"
                                    onClick={handleApplyAiConfig}
                                    disabled={aiSaving || aiOnline === false}
                                >
                                    {aiSaving ? <><div className="spinner" /><span>Đang áp dụng...</span></> : 'Áp Dụng Cho AI'}
                                </button>
                            </div>
                        )}
                    </div>
                </Section>

            </div>

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
            {description && <div style={{ fontSize: '10.5px', color: 'var(--t-muted)' }}>{description}</div>}
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
