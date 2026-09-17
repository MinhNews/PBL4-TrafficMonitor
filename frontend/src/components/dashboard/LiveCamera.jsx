import React, { useState } from 'react';

export default function LiveCamera() {
    const [streamError, setStreamError] = useState(false);

    return (
        <div style={{
            backgroundColor: '#ffffff',
            borderRadius: '16px',
            overflow: 'hidden',
            boxShadow: '0 4px 20px rgba(0, 0, 0, 0.05)'
        }}>
            <div style={{
                padding: '16px 20px',
                backgroundColor: '#0f172a',
                color: '#ffffff',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center'
            }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span style={{ width: '10px', height: '10px', borderRadius: '50%', backgroundColor: streamError ? '#ef4444' : '#22c55e' }}></span>
                    <span style={{ fontWeight: '700', fontSize: '14.5px' }}>Camera 01 - Ngã Tư Hòa Khánh</span>
                </div>
                <span style={{ fontSize: '12px', color: '#94a3b8' }}>MJPEG 640x480 (AI Stream)</span>
            </div>

            <div style={{ height: '360px', backgroundColor: '#020617', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                {!streamError ? (
                    <img
                        src="http://localhost:5000/video_feed"
                        alt="AI Video Stream"
                        style={{ width: '100%', height: '100%', objectFit: 'contain' }}
                        onError={() => setStreamError(true)}
                    />
                ) : (
                    <div style={{ textAlign: 'center', color: '#64748b' }}>
                        <p style={{ fontSize: '36px', margin: '0 0 10px 0' }}>📷</p>
                        <p style={{ margin: 0, fontWeight: '700', color: '#cbd5e1' }}>AI Service đang Offline</p>
                        <span style={{ fontSize: '12px', color: '#64748b' }}>Chạy main.py hoặc test_detector.py bên AI Service để xem luồng stream</span>
                    </div>
                )}
            </div>
        </div>
    );
}