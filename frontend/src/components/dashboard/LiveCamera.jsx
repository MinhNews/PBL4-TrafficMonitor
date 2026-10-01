import React, { useState, useEffect, useRef, useCallback } from 'react';

const STREAM_URL = 'http://localhost:5000/video_feed';
const STATUS_URL = 'http://localhost:5000/status';
const LIGHT_URL = 'http://localhost:5000/light';
const CHECK_INTERVAL = 1000;

export default function LiveCamera() {
    const [streamStatus, setStreamStatus] = useState('connecting'); // connecting | live | offline
    const [metrics, setMetrics] = useState({ fps: 30, light: 'GREEN', vehiclesPassed: 0, violations: 0, width: 0, height: 0, orientation: 'PORTRAIT', esp32Online: false });
    const [retryCount, setRetryCount] = useState(0);
    const [viewMode, setViewMode] = useState('AUTO'); // 'AUTO' | 'PORTRAIT' | 'LANDSCAPE'
    const [videoDims, setVideoDims] = useState({ width: 0, height: 0 });

    const containerRef = useRef(null);
    const imgRef = useRef(null);
    const retryRef = useRef(null);

    const probe = useCallback(async () => {
        try {
            const controller = new AbortController();
            const timer = setTimeout(() => controller.abort(), 3500);
            const res = await fetch(STATUS_URL, { signal: controller.signal });
            clearTimeout(timer);
            if (res.ok) {
                const data = await res.json();
                setMetrics(data);
                if (data.width && data.height) {
                    setVideoDims(prev => (prev.width === data.width && prev.height === data.height) ? prev : { width: data.width, height: data.height });
                }
                setStreamStatus('live');
            } else {
                setStreamStatus('offline');
            }
        } catch {
            setStreamStatus('offline');
        }
    }, []);

    useEffect(() => {
        probe();
        retryRef.current = setInterval(() => {
            setRetryCount(c => c + 1);
            probe();
        }, CHECK_INTERVAL);

        return () => clearInterval(retryRef.current);
    }, [probe]);

    // Lắng nghe khi ảnh từ luồng camera load để tự đo kích thước thực tế (Double Guarantee)
    const handleImageLoad = (e) => {
        const nw = e.target.naturalWidth;
        const nh = e.target.naturalHeight;
        if (nw && nh && (nw !== videoDims.width || nh !== videoDims.height)) {
            setVideoDims({ width: nw, height: nh });
        }
    };

    async function toggleLight(targetLight) {
        if (targetLight !== 'AUTO') {
            setMetrics(prev => ({ ...prev, light: targetLight, mode: 'MANUAL' }));
        } else {
            setMetrics(prev => ({ ...prev, mode: 'AUTO_ESP32' }));
        }
        try {
            const res = await fetch(LIGHT_URL, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ light: targetLight })
            });
            if (res.ok) {
                const data = await res.json();
                setMetrics(prev => ({ ...prev, light: data.light || (targetLight === 'AUTO' ? prev.light : targetLight), mode: data.mode }));
            }
        } catch (e) {
            console.error('Error toggling light:', e);
        }
    }

    function toggleFullscreen() {
        if (!containerRef.current) return;
        if (!document.fullscreenElement) {
            containerRef.current.requestFullscreen().catch(() => {});
        } else {
            document.exitFullscreen().catch(() => {});
        }
    }

    // Tự động phân tích tỷ lệ khung hình
    const realW = videoDims.width || metrics.width || 405;
    const realH = videoDims.height || metrics.height || 720;
    const isActuallyPortrait = realH > realW;

    // Chế độ hiển thị hiệu lực: Nếu chọn AUTO thì theo tỷ lệ thật, nếu chọn thủ công thì theo người dùng
    const effectiveIsPortrait = viewMode === 'AUTO' 
        ? isActuallyPortrait 
        : viewMode === 'PORTRAIT';

    // Tỷ lệ khung hình hiển thị (tính theo format)
    const aspectRatioLabel = realW && realH 
        ? `${realW}×${realH} (${isActuallyPortrait ? 'Dọc ~9:16' : realW / realH > 1.6 ? 'Ngang 16:9' : 'Ngang 4:3'})`
        : 'Đang nhận diện...';

    // Chiều rộng động của cột video khi ở chế độ Dọc (tỷ lệ chuẩn)
    const portraitColWidth = Math.min(380, Math.max(280, Math.round(560 * (realW / realH))));

    return (
        <div ref={containerRef} style={{
            backgroundColor: '#ffffff',
            border: '1px solid var(--c-border)',
            borderRadius: 'var(--r-lg)',
            overflow: 'hidden',
            display: 'flex',
            flexDirection: 'column',
            boxShadow: '0 1px 3px 0 rgba(0, 0, 0, 0.05)',
        }}>
            {/* Header: Title, Aspect Ratio Selector & Live Status */}
            <div style={{
                padding: '10px 18px',
                backgroundColor: '#f8fafc',
                borderBottom: '1px solid var(--c-border)',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                flexWrap: 'wrap',
                gap: '10px',
            }}>
                {/* Left: Camera identification */}
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span style={{
                        width: '9px', height: '9px', borderRadius: '50%',
                        backgroundColor: streamStatus === 'live' ? '#16a34a' : streamStatus === 'connecting' ? '#d97706' : '#dc2626'
                    }} />
                    <span style={{ fontSize: '13.5px', fontWeight: 800, color: 'var(--t-primary)' }}>
                        Bàn Giám Sát Tuyến: CAM-HK-01
                    </span>
                    <span style={{
                        fontSize: '11px',
                        fontWeight: 700,
                        backgroundColor: '#e2e8f0',
                        color: '#334155',
                        padding: '2px 7px',
                        borderRadius: '4px'
                    }}>
                        Hòa Khánh
                    </span>
                    <span style={{
                        fontSize: '11px',
                        fontWeight: 600,
                        backgroundColor: '#eff6ff',
                        color: '#1d4ed8',
                        border: '1px solid #bfdbfe',
                        padding: '2px 7px',
                        borderRadius: '4px'
                    }}>
                        {aspectRatioLabel}
                    </span>
                </div>

                {/* Right: Adaptive View Mode Toggle & Live Badge */}
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
                    {/* View Mode Selector: Cho phép tự động hoặc ép kiểu */}
                    <div style={{
                        display: 'flex',
                        alignItems: 'center',
                        backgroundColor: '#e2e8f0',
                        borderRadius: '6px',
                        padding: '2px',
                        gap: '2px',
                        fontSize: '11px',
                        fontWeight: 600,
                    }}>
                        <button
                            onClick={() => setViewMode('AUTO')}
                            title="Tự động căn chỉnh kích thước theo video nguồn"
                            style={{
                                padding: '3px 8px',
                                borderRadius: '4px',
                                border: 'none',
                                cursor: 'pointer',
                                backgroundColor: viewMode === 'AUTO' ? '#ffffff' : 'transparent',
                                color: viewMode === 'AUTO' ? '#1d4ed8' : '#475569',
                                fontWeight: viewMode === 'AUTO' ? 700 : 500,
                                boxShadow: viewMode === 'AUTO' ? '0 1px 2px rgba(0,0,0,0.1)' : 'none',
                                transition: 'all 0.15s'
                            }}
                        >
                            ⚡ Tự Động
                        </button>
                        <button
                            onClick={() => setViewMode('PORTRAIT')}
                            title="Ép chế độ màn hình dọc (Corridor View 9:16)"
                            style={{
                                padding: '3px 8px',
                                borderRadius: '4px',
                                border: 'none',
                                cursor: 'pointer',
                                backgroundColor: viewMode === 'PORTRAIT' ? '#ffffff' : 'transparent',
                                color: viewMode === 'PORTRAIT' ? '#1d4ed8' : '#475569',
                                fontWeight: viewMode === 'PORTRAIT' ? 700 : 500,
                                boxShadow: viewMode === 'PORTRAIT' ? '0 1px 2px rgba(0,0,0,0.1)' : 'none',
                                transition: 'all 0.15s'
                            }}
                        >
                            📱 Khung Dọc
                        </button>
                        <button
                            onClick={() => setViewMode('LANDSCAPE')}
                            title="Ép chế độ màn hình ngang (Toàn Cảnh 16:9)"
                            style={{
                                padding: '3px 8px',
                                borderRadius: '4px',
                                border: 'none',
                                cursor: 'pointer',
                                backgroundColor: viewMode === 'LANDSCAPE' ? '#ffffff' : 'transparent',
                                color: viewMode === 'LANDSCAPE' ? '#1d4ed8' : '#475569',
                                fontWeight: viewMode === 'LANDSCAPE' ? 700 : 500,
                                boxShadow: viewMode === 'LANDSCAPE' ? '0 1px 2px rgba(0,0,0,0.1)' : 'none',
                                transition: 'all 0.15s'
                            }}
                        >
                            🖥️ Khung Ngang
                        </button>
                    </div>

                    {/* Live Stream Status Badge */}
                    <div style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '6px',
                        backgroundColor: streamStatus === 'live' ? '#f0fdf4' : '#fef2f2',
                        border: streamStatus === 'live' ? '1px solid #bbf7d0' : '1px solid #fecaca',
                        color: streamStatus === 'live' ? '#15803d' : '#b91c1c',
                        borderRadius: '4px',
                        padding: '4px 9px',
                        fontSize: '11px',
                        fontWeight: 700
                    }}>
                        <span style={{
                            width: 6, height: 6, borderRadius: '50%',
                            backgroundColor: streamStatus === 'live' ? '#16a34a' : '#dc2626'
                        }} />
                        {streamStatus === 'live' ? `TRỰC TIẾP (${metrics.fps || 30} FPS)` : 'MẤT KẾT NỐI'}
                    </div>

                    <button
                        onClick={toggleFullscreen}
                        title="Xem toàn màn hình"
                        style={{
                            padding: '5px 8px',
                            color: '#475569',
                            backgroundColor: '#ffffff',
                            border: '1px solid var(--c-border)',
                            borderRadius: '4px',
                            cursor: 'pointer',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '4px',
                            fontSize: '11px',
                            fontWeight: 600,
                        }}
                    >
                        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <path d="M8 3H5a2 2 0 00-2 2v3m18 0V5a2 2 0 00-2-2h-3m0 18h3a2 2 0 002-2v-3M3 16v3a2 2 0 002 2h3"/>
                        </svg>
                        Toàn Màn Hình
                    </button>
                </div>
            </div>

            {/* ADAPTIVE WORKSTATION BODY: TỰ ĐỘNG CHUYỂN BỐ CỤC THEO VIDEO */}
            {effectiveIsPortrait ? (
                /* =========================================================================
                   BỐ CỤC DỌC (PORTRAIT LAYOUT): Video cột trái, Bảng điều khiển cột phải
                   ========================================================================= */
                <div style={{
                    display: 'flex',
                    flexDirection: 'row',
                    backgroundColor: '#ffffff',
                    minHeight: '560px',
                }}>
                    {/* Video Monitor Dọc: Chiều rộng tính động theo tỷ lệ thực tế, đảm bảo không bao giờ bị cắt */}
                    <div style={{
                        width: `${portraitColWidth}px`,
                        minWidth: `${portraitColWidth}px`,
                        height: '560px',
                        backgroundColor: '#090d16',
                        position: 'relative',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        overflow: 'hidden',
                        borderRight: '1px solid var(--c-border)',
                    }}>
                        {streamStatus === 'live' ? (
                            <img
                                ref={imgRef}
                                src={STREAM_URL}
                                alt="Luồng Camera AI Trực Tiếp Tuyến Đường"
                                onLoad={handleImageLoad}
                                style={{
                                    width: '100%',
                                    height: '100%',
                                    objectFit: 'contain', // Luôn hiển thị trọn vẹn 100% video
                                    display: 'block',
                                    margin: 'auto'
                                }}
                                onError={() => setStreamStatus('offline')}
                            />
                        ) : (
                            <OfflinePlaceholder status={streamStatus} retryCount={retryCount} />
                        )}

                        <MonitorHUD streamStatus={streamStatus} code="CAM-HK-01" label={aspectRatioLabel} />
                    </div>

                    {/* Cột Phải: Bảng Điều Hành Tín Hiệu & Đo Lường Trực Tuyến */}
                    <div style={{
                        flex: 1,
                        padding: '18px 20px',
                        display: 'flex',
                        flexDirection: 'column',
                        gap: '16px',
                        backgroundColor: '#ffffff',
                        overflowY: 'auto',
                    }}>
                        <TrafficLightControlSection metrics={metrics} toggleLight={toggleLight} />
                        <RealtimeMetricsSection metrics={metrics} />
                        <TechnicalSpecSection isPortrait={true} realW={realW} realH={realH} />
                    </div>
                </div>
            ) : (
                /* =========================================================================
                   BỐ CỤC NGANG (LANDSCAPE LAYOUT): Video Widescreen phía trên, Bảng điều khiển phía dưới
                   ========================================================================= */
                <div style={{
                    display: 'flex',
                    flexDirection: 'column',
                    backgroundColor: '#ffffff',
                }}>
                    {/* Video Monitor Toàn Cảnh Ngang (16:9 / 4:3) */}
                    <div style={{
                        width: '100%',
                        height: '380px',
                        backgroundColor: '#090d16',
                        position: 'relative',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        overflow: 'hidden',
                        borderBottom: '1px solid var(--c-border)',
                    }}>
                        {streamStatus === 'live' ? (
                            <img
                                ref={imgRef}
                                src={STREAM_URL}
                                alt="Luồng Camera AI Trực Tiếp Toàn Cảnh"
                                onLoad={handleImageLoad}
                                style={{
                                    maxWidth: '100%',
                                    maxHeight: '100%',
                                    objectFit: 'contain', // Luôn giữ tỷ lệ chuẩn 16:9, không bị méo/cắt
                                    display: 'block',
                                    margin: 'auto'
                                }}
                                onError={() => setStreamStatus('offline')}
                            />
                        ) : (
                            <OfflinePlaceholder status={streamStatus} retryCount={retryCount} />
                        )}

                        <MonitorHUD streamStatus={streamStatus} code="CAM-HK-01" label={aspectRatioLabel} />
                    </div>

                    {/* Bảng Điều Hành & Telemetry Trải Ngang Dưới Video */}
                    <div style={{
                        padding: '16px 20px',
                        display: 'grid',
                        gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
                        gap: '16px',
                        backgroundColor: '#ffffff',
                    }}>
                        <TrafficLightControlSection metrics={metrics} toggleLight={toggleLight} compact={true} />
                        <RealtimeMetricsSection metrics={metrics} compact={true} />
                        <TechnicalSpecSection isPortrait={false} realW={realW} realH={realH} />
                    </div>
                </div>
            )}

            {/* Bottom Enterprise Metadata Bar */}
            <div style={{
                padding: '8px 18px',
                backgroundColor: '#f8fafc',
                borderTop: '1px solid var(--c-border)',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                fontSize: '11px',
                color: '#64748b',
                flexWrap: 'wrap',
                gap: '8px',
            }}>
                <div>Đơn Vị Quản Lý: <strong style={{ color: '#1e293b' }}>Phòng CSGT — Công An TP. Đà Nẵng</strong></div>
                <div>Khung Hình: <strong style={{ color: '#1d4ed8' }}>{aspectRatioLabel}</strong> ({viewMode === 'AUTO' ? 'Tự thích ứng thông minh' : `Cố định ${viewMode}`})</div>
                <div style={{ fontFamily: 'var(--mono)' }}>
                    Cổng Kết Nối: http://localhost:5000/video_feed
                </div>
            </div>
        </div>
    );
}

/* =========================================================================
   SUB-COMPONENTS PHỤ TRỢ (TÁI SỬ DỤNG GỌN GÀNG CHO CẢ 2 BỐ CỤC)
   ========================================================================= */

function OfflinePlaceholder({ status, retryCount }) {
    return (
        <div style={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '10px',
            color: '#94a3b8',
            padding: '20px',
            textAlign: 'center',
        }}>
            <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                <path d="M23 7l-7 5 7 5V7z"/><rect x="1" y="5" width="15" height="14" rx="2" ry="2"/>
            </svg>
            <div style={{ fontSize: '13px', fontWeight: 600, color: '#f8fafc' }}>
                {status === 'connecting' ? 'Đang kết nối camera AI...' : 'Mất tín hiệu camera'}
            </div>
            <div style={{ fontSize: '11px', color: '#64748b' }}>
                Đang tự động thử lại (Lần {retryCount})...
            </div>
        </div>
    );
}

function MonitorHUD({ streamStatus, code, label }) {
    if (streamStatus !== 'live') return null;
    return (
        <>
            <div style={{
                position: 'absolute',
                top: 10, left: 10,
                backgroundColor: 'rgba(15, 23, 42, 0.85)',
                padding: '3px 8px',
                borderRadius: '4px',
                fontSize: '10.5px',
                color: '#f8fafc',
                fontFamily: 'var(--mono)',
                display: 'flex',
                gap: '6px',
                alignItems: 'center',
                border: '1px solid rgba(255, 255, 255, 0.15)',
                zIndex: 2,
            }}>
                <span style={{ width: 6, height: 6, borderRadius: '50%', backgroundColor: '#16a34a' }} />
                <span>{code} · LIVE</span>
            </div>

            <div style={{
                position: 'absolute',
                bottom: 10, left: 10,
                backgroundColor: 'rgba(15, 23, 42, 0.85)',
                padding: '3px 8px',
                borderRadius: '4px',
                fontSize: '10px',
                color: '#cbd5e1',
                fontFamily: 'var(--mono)',
                border: '1px solid rgba(255, 255, 255, 0.1)',
                zIndex: 2,
            }}>
                VẠCH DỪNG: Y=468
            </div>
        </>
    );
}

function TrafficLightControlSection({ metrics, toggleLight, compact = false }) {
    const currentLight = (metrics?.light || 'GREEN').toUpperCase();

    // Định nghĩa màu sắc và trạng thái cho từng đèn
    const isRed = currentLight === 'RED';
    const isYellow = currentLight === 'YELLOW';
    const isGreen = currentLight === 'GREEN';

    return (
        <div style={{
            backgroundColor: '#f8fafc',
            border: '1px solid var(--c-border)',
            borderRadius: 'var(--r-md)',
            padding: compact ? '12px 14px' : '14px 16px',
            display: 'flex',
            flexDirection: 'column',
            gap: '12px'
        }}>
            {/* Header: Tiêu đề và Trạng thái đèn hiện tại */}
            <div style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                flexWrap: 'wrap',
                gap: '8px',
            }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <span style={{ fontSize: '11.5px', fontWeight: 800, color: 'var(--t-primary)', textTransform: 'uppercase', letterSpacing: '0.4px' }}>
                        Tín Hiệu Đèn Giao Thông
                    </span>
                    <span style={{
                        fontSize: '9.5px',
                        fontWeight: 700,
                        padding: '1px 6px',
                        borderRadius: '3px',
                        backgroundColor: metrics?.esp32Online ? '#dcfce7' : '#f1f5f9',
                        color: metrics?.esp32Online ? '#166534' : '#64748b',
                        border: metrics?.esp32Online ? '1px solid #86efac' : '1px solid #cbd5e1',
                    }}>
                        {metrics?.esp32Online ? '● ESP32 Online' : '○ Giả lập'}
                    </span>
                </div>

                {/* Badge trạng thái chữ */}
                <span style={{
                    fontSize: '11px',
                    fontWeight: 700,
                    padding: '3px 8px',
                    borderRadius: '4px',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '5px',
                    backgroundColor: isRed ? '#fee2e2' : isYellow ? '#fef9c3' : '#dcfce7',
                    color: isRed ? '#991b1b' : isYellow ? '#854d0e' : '#166534',
                    border: isRed ? '1px solid #fca5a5' : isYellow ? '1px solid #fde047' : '1px solid #86efac',
                }}>
                    <span style={{
                        width: 7, height: 7, borderRadius: '50%',
                        backgroundColor: isRed ? '#dc2626' : isYellow ? '#eab308' : '#16a34a',
                        boxShadow: isRed ? '0 0 6px #dc2626' : isYellow ? '0 0 6px #eab308' : '0 0 6px #16a34a'
                    }} />
                    {isRed ? 'PHA ĐÈN ĐỎ' : isYellow ? 'PHA ĐÈN VÀNG' : 'PHA ĐÈN XANH'}
                    {metrics?.remainingSeconds != null && (
                        <span style={{ fontWeight: 800, marginLeft: 2, fontFamily: 'var(--mono)' }}>
                            ({metrics.remainingSeconds}s)
                        </span>
                    )}
                </span>
            </div>

            {/* Mô hình Cột Đèn Giao Thông 3 Đèn Thực Tế (Physical Traffic Light Simulator) */}
            <div style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '8px 14px',
                backgroundColor: '#0f172a',
                borderRadius: '8px',
                border: '1px solid #334155',
                gap: '12px'
            }}>
                {/* Vỏ đèn giao thông 3 bóng ngang */}
                <div style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '10px',
                    backgroundColor: '#1e293b',
                    padding: '6px 12px',
                    borderRadius: '20px',
                    border: '1px solid #475569',
                    boxShadow: 'inset 0 2px 4px rgba(0,0,0,0.5)'
                }}>
                    {/* 🔴 Đèn Đỏ */}
                    <div
                        title="Đèn Đỏ"
                        style={{
                            width: 18,
                            height: 18,
                            borderRadius: '50%',
                            backgroundColor: isRed ? '#ef4444' : '#450a0a',
                            border: isRed ? '2px solid #fecaca' : '1px solid #374151',
                            boxShadow: isRed ? '0 0 12px #ef4444, 0 0 4px #f87171' : 'none',
                            transition: 'all 0.2s ease',
                        }}
                    />
                    {/* 🟡 Đèn Vàng */}
                    <div
                        title="Đèn Vàng"
                        style={{
                            width: 18,
                            height: 18,
                            borderRadius: '50%',
                            backgroundColor: isYellow ? '#facc15' : '#422006',
                            border: isYellow ? '2px solid #fef08a' : '1px solid #374151',
                            boxShadow: isYellow ? '0 0 12px #facc15, 0 0 4px #fde047' : 'none',
                            transition: 'all 0.2s ease',
                        }}
                    />
                    {/* 🟢 Đèn Xanh */}
                    <div
                        title="Đèn Xanh"
                        style={{
                            width: 18,
                            height: 18,
                            borderRadius: '50%',
                            backgroundColor: isGreen ? '#22c55e' : '#052e16',
                            border: isGreen ? '2px solid #bbf7d0' : '1px solid #374151',
                            boxShadow: isGreen ? '0 0 12px #22c55e, 0 0 4px #4ade80' : 'none',
                            transition: 'all 0.2s ease',
                        }}
                    />
                </div>

                {/* Mô tả trạng thái chi tiết */}
                <div style={{ flex: 1, minWidth: 0, textAlign: 'right' }}>
                    <div style={{ fontSize: '11px', fontWeight: 700, color: '#f8fafc', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                        {isRed ? 'BẮT PHẠT XE VƯỢT VẠCH DỪNG' : isYellow ? 'GIẢM TỐC ĐỘ / CHUẨN BỊ DỪNG' : 'PHƯƠNG TIỆN LƯU THÔNG BÌNH THƯỜNG'}
                    </div>
                    <div style={{ fontSize: '10px', color: '#94a3b8' }}>
                        MQTT: <span style={{ fontFamily: 'var(--mono)', color: '#38bdf8' }}>pbl4/nhom3/traffic/light</span>
                    </div>
                </div>
            </div>

            {/* Các Nút Bấm Điều Khiển (Tự ẩn khi có bo ESP32 kết nối) */}
            {!metrics?.esp32Online && (
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '6px' }}>
                    {/* Nút Đèn Đỏ */}
                    <button
                        onClick={() => toggleLight('RED')}
                        style={{
                            padding: '7px 4px',
                            borderRadius: '5px',
                            fontSize: '11px',
                            fontWeight: 700,
                            border: isRed ? '1px solid #dc2626' : '1px solid var(--c-border)',
                            backgroundColor: isRed ? '#dc2626' : '#ffffff',
                            color: isRed ? '#ffffff' : '#334155',
                            cursor: 'pointer',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            gap: '4px',
                            transition: 'all 0.15s ease',
                        }}
                    >
                        <span style={{ width: 6, height: 6, borderRadius: '50%', backgroundColor: isRed ? '#ffffff' : '#dc2626' }} />
                        ĐÈN ĐỎ
                    </button>

                    {/* Nút Đèn Vàng */}
                    <button
                        onClick={() => toggleLight('YELLOW')}
                        style={{
                            padding: '7px 4px',
                            borderRadius: '5px',
                            fontSize: '11px',
                            fontWeight: 700,
                            border: isYellow ? '1px solid #ca8a04' : '1px solid var(--c-border)',
                            backgroundColor: isYellow ? '#eab308' : '#ffffff',
                            color: isYellow ? '#713f12' : '#334155',
                            cursor: 'pointer',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            gap: '4px',
                            transition: 'all 0.15s ease',
                        }}
                    >
                        <span style={{ width: 6, height: 6, borderRadius: '50%', backgroundColor: isYellow ? '#713f12' : '#eab308' }} />
                        ĐÈN VÀNG
                    </button>

                    {/* Nút Đèn Xanh */}
                    <button
                        onClick={() => toggleLight('GREEN')}
                        style={{
                            padding: '7px 4px',
                            borderRadius: '5px',
                            fontSize: '11px',
                            fontWeight: 700,
                            border: isGreen ? '1px solid #16a34a' : '1px solid var(--c-border)',
                            backgroundColor: isGreen ? '#16a34a' : '#ffffff',
                            color: isGreen ? '#ffffff' : '#334155',
                            cursor: 'pointer',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            gap: '4px',
                            transition: 'all 0.15s ease',
                        }}
                    >
                        <span style={{ width: 6, height: 6, borderRadius: '50%', backgroundColor: isGreen ? '#ffffff' : '#16a34a' }} />
                        ĐÈN XANH
                    </button>
                </div>
            )}
        </div>
    );
}

function RealtimeMetricsSection({ metrics, compact = false }) {
    return (
        <div>
            <div style={{ fontSize: '11.5px', fontWeight: 800, color: 'var(--t-primary)', textTransform: 'uppercase', letterSpacing: '0.4px', marginBottom: '8px' }}>
                Chỉ Số Hoạt Động Thời Gian Thực
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '8px' }}>
                <div style={{
                    padding: compact ? '8px 10px' : '10px 12px',
                    backgroundColor: '#ffffff',
                    border: '1px solid var(--c-border)',
                    borderRadius: '6px',
                    borderLeft: '3px solid #1d4ed8'
                }}>
                    <div style={{ fontSize: '10.5px', color: '#64748b', fontWeight: 600 }}>LƯU LƯỢNG XE QUA VẠCH</div>
                    <div style={{ fontSize: '20px', fontWeight: 800, color: '#0f172a', margin: '2px 0' }}>
                        {metrics.vehiclesPassed != null ? metrics.vehiclesPassed.toLocaleString() : '0'} <span style={{ fontSize: '11px', fontWeight: 500, color: '#64748b' }}>xe</span>
                    </div>
                    <div style={{ fontSize: '10px', color: '#16a34a', fontWeight: 600 }}>● ByteTrack tự động</div>
                </div>

                <div style={{
                    padding: compact ? '8px 10px' : '10px 12px',
                    backgroundColor: '#ffffff',
                    border: '1px solid var(--c-border)',
                    borderRadius: '6px',
                    borderLeft: '3px solid #dc2626'
                }}>
                    <div style={{ fontSize: '10.5px', color: '#64748b', fontWeight: 600 }}>VI PHẠM TẠI CHỐT</div>
                    <div style={{ fontSize: '20px', fontWeight: 800, color: '#dc2626', margin: '2px 0' }}>
                        {metrics.violations != null ? metrics.violations.toLocaleString() : '0'} <span style={{ fontSize: '11px', fontWeight: 500, color: '#64748b' }}>vụ</span>
                    </div>
                    <div style={{ fontSize: '10px', color: '#dc2626', fontWeight: 600 }}>● Đã lập hồ sơ</div>
                </div>

                <div style={{
                    padding: compact ? '8px 10px' : '10px 12px',
                    backgroundColor: '#ffffff',
                    border: '1px solid var(--c-border)',
                    borderRadius: '6px',
                    borderLeft: '3px solid #16a34a'
                }}>
                    <div style={{ fontSize: '10.5px', color: '#64748b', fontWeight: 600 }}>TỐC ĐỘ AI</div>
                    <div style={{ fontSize: '20px', fontWeight: 800, color: '#16a34a', margin: '2px 0' }}>
                        {metrics.fps || 30} <span style={{ fontSize: '11px', fontWeight: 500, color: '#64748b' }}>FPS</span>
                    </div>
                    <div style={{ fontSize: '10px', color: '#64748b' }}>YOLO11n + ByteTrack</div>
                </div>

                <div style={{
                    padding: compact ? '8px 10px' : '10px 12px',
                    backgroundColor: '#ffffff',
                    border: '1px solid var(--c-border)',
                    borderRadius: '6px',
                    borderLeft: '3px solid #64748b'
                }}>
                    <div style={{ fontSize: '10.5px', color: '#64748b', fontWeight: 600 }}>ĐỘ TRỄ MẠNG</div>
                    <div style={{ fontSize: '20px', fontWeight: 800, color: '#334155', margin: '2px 0' }}>
                        &lt; 40 <span style={{ fontSize: '11px', fontWeight: 500, color: '#64748b' }}>ms</span>
                    </div>
                    <div style={{ fontSize: '10px', color: '#64748b' }}>Cổng MJPEG :5000</div>
                </div>
            </div>
        </div>
    );
}

function TechnicalSpecSection({ isPortrait, realW, realH }) {
    return (
        <div style={{
            backgroundColor: '#f8fafc',
            border: '1px solid var(--c-border)',
            borderRadius: 'var(--r-md)',
            padding: '12px 14px',
            fontSize: '11.5px',
        }}>
            <div style={{ fontWeight: 800, color: 'var(--t-primary)', textTransform: 'uppercase', letterSpacing: '0.4px', marginBottom: '8px' }}>
                Thông Số Kỹ Thuật Điểm Giám Sát
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: isPortrait ? '1fr 1fr' : '1fr', gap: '6px', color: '#334155' }}>
                <div><strong>Vị trí:</strong> Ngã tư Hòa Khánh (Km 928+500 QL1A)</div>
                <div><strong>Tọa độ:</strong> 16.0594° N, 108.1481° E</div>
                <div><strong>Độ phân giải:</strong> {realW} × {realH} px</div>
                <div><strong>Định dạng:</strong> {isPortrait ? 'Khung Dọc (Corridor 9:16)' : 'Toàn Cảnh (Widescreen 16:9)'}</div>
            </div>
        </div>
    );
}