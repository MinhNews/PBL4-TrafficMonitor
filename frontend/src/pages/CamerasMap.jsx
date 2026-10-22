import React, { useState, useEffect } from 'react';
import { cameraAPI } from '../services/api';

const AI_BASE = 'http://localhost:5000';
const STATUS_URL = `${AI_BASE}/status`;
const SWITCH_URL = `${AI_BASE}/camera/switch`;

const DEFAULT_CAMERA = {
  id: 1,
  code: 'CAM-01',
  name: 'Camera 01: Ngã Tư Hòa Khánh',
  regionName: 'Ngã tư Hòa Khánh',
  locationDescription: 'Góc Tây Bắc nút giao — Quận Liên Chiểu, TP. Đà Nẵng',
  streamUrl: `${AI_BASE}/video_feed`,
  aiModel: 'YOLO11s + ViT + ByteTrack',
  status: 'ONLINE',
};

async function fetchAiStatus() {
  const res = await fetch(STATUS_URL, { signal: AbortSignal.timeout(2000) });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export default function CamerasMap() {
  const [cameras, setCameras] = useState([DEFAULT_CAMERA]);
  const [selectedCamera, setSelectedCamera] = useState(null);
  const [liveMetrics, setLiveMetrics] = useState({ fps: 0, light: 'GREEN', vehiclesPassed: 0, violations: 0, activeCamera: null });
  const [aiOnline, setAiOnline] = useState(false);
  const [switchingId, setSwitchingId] = useState(null);

  // 1. Fetch active cameras from Backend API
  useEffect(() => {
    async function loadCameras() {
      try {
        const res = await cameraAPI.getAll();
        if (res.data && res.data.length > 0) {
          const mapped = res.data.map(c => ({
            id: c.id,
            code: `CAM-${String(c.id).padStart(2, '0')}`,
            name: c.name || `Camera ${c.id}`,
            regionName: c.regionName || 'Ngã tư Hòa Khánh',
            locationDescription: c.locationDescription || 'Nút giao giám sát',
            streamUrl: c.streamUrl || `${AI_BASE}/video_feed`,
            aiModel: 'YOLO11s + ViT + ByteTrack',
            status: c.isActive ? 'ONLINE' : 'OFFLINE',
          }));
          setCameras(mapped);
        }
      } catch (err) {
        console.warn('Không tải được danh sách camera từ backend, sử dụng camera mặc định', err);
      }
    }
    loadCameras();
  }, []);

  // 2. Poll live metrics + camera đang giám sát từ AI service
  useEffect(() => {
    let alive = true;
    async function poll() {
      try {
        const data = await fetchAiStatus();
        if (!alive) return;
        setLiveMetrics(data);
        setAiOnline(true);
      } catch {
        if (alive) setAiOnline(false);
      }
    }
    poll();
    const interval = setInterval(poll, 2500);
    return () => { alive = false; clearInterval(interval); };
  }, []);

  // 3. C4: chuyển camera AI đang giám sát (chỉ 1 luồng suy luận tại một thời điểm)
  async function switchTo(cameraId) {
    if (!cameraId || switchingId) return;
    setSwitchingId(cameraId);
    try {
      const res = await fetch(SWITCH_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ cameraId }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);

      for (let i = 0; i < 8; i += 1) {
        await new Promise(r => setTimeout(r, 500));
        const data = await fetchAiStatus();
        setLiveMetrics(data);
        setAiOnline(true);
        if (data?.activeCamera?.id === cameraId && !data?.activeCamera?.switching) break;
      }
    } catch (err) {
      console.warn('Không chuyển được camera:', err);
    } finally {
      setSwitchingId(null);
    }
  }

  const activeId = liveMetrics?.activeCamera?.id ?? null;
  const activeName = liveMetrics?.activeCamera?.name;
  const activeResolution = liveMetrics?.width && liveMetrics?.height
    ? `${liveMetrics.width}×${liveMetrics.height}`
    : null;
  const selectedIsActive = Boolean(selectedCamera) && aiOnline && activeId === selectedCamera.id;

  return (
    <div style={{ padding: '24px', display: 'flex', flexDirection: 'column', gap: '20px' }}>
      
      {/* Header bar */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '14px' }}>
        <div>
          <h1 style={{ fontSize: '18px', fontWeight: 800, color: 'var(--t-primary)', margin: 0 }}>
            Hạ Tầng Camera Giám Sát Nút Giao
          </h1>
          <div style={{ fontSize: '12px', color: 'var(--t-muted)', marginTop: '3px' }}>
            AI chỉ suy luận một camera tại một thời điểm — chọn camera để chuyển luồng phân tích, không cần restart
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <span style={{
            fontSize: '12px',
            fontWeight: 600,
            padding: '4px 10px',
            borderRadius: '4px',
            backgroundColor: aiOnline ? '#dcfce7' : '#f1f5f9',
            color: aiOnline ? '#15803d' : '#64748b',
            border: aiOnline ? '1px solid #bbf7d0' : '1px solid #cbd5e1',
            display: 'flex',
            alignItems: 'center',
            gap: '6px'
          }}>
            <span style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: aiOnline ? '#22c55e' : '#94a3b8' }} />
            {aiOnline
              ? `${cameras.length} camera đã cấu hình · đang giám sát: ${activeName || 'chưa chọn'}`
              : 'AI Engine ngoại tuyến — chưa giám sát camera nào'}
          </span>
        </div>
      </div>

      {/* Main Grid: Active Real Cameras */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fill, minmax(380px, 1fr))',
        gap: '20px'
      }}>
        {cameras.map((cam) => {
          const isActive = aiOnline && activeId === cam.id;
          const isSwitching = switchingId === cam.id;
          const vehicles = isActive ? (liveMetrics.vehiclesPassed || 0) : null;
          const violations = isActive ? (liveMetrics.violations || 0) : null;

          return (
            <div
              key={cam.id}
              style={{
                backgroundColor: '#ffffff',
                border: '1px solid var(--c-border)',
                borderRadius: 'var(--r-lg)',
                overflow: 'hidden',
                display: 'flex',
                flexDirection: 'column',
                boxShadow: '0 1px 3px 0 rgba(0, 0, 0, 0.04)',
              }}
            >
              {/* CCTV Stream Container */}
              <div style={{
                height: '260px',
                backgroundColor: '#090d16',
                position: 'relative',
                overflow: 'hidden',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center'
              }}>
                {isActive ? (
                  <img
                    src={cam.streamUrl}
                    alt={cam.name}
                    style={{
                      maxWidth: '100%',
                      maxHeight: '100%',
                      objectFit: 'contain',
                      display: 'block',
                      margin: 'auto'
                    }}
                    onError={(e) => { e.target.style.display = 'none'; }}
                  />
                ) : (
                  <div
                    title={aiOnline ? 'Camera đang chờ — AI chỉ giám sát một camera tại một thời điểm' : 'AI Engine chưa chạy'}
                    style={{
                      display: 'flex',
                      flexDirection: 'column',
                      alignItems: 'center',
                      justifyContent: 'center',
                      gap: '8px',
                      color: '#64748b',
                      padding: '20px',
                      textAlign: 'center',
                    }}
                  >
                    <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                      <path d="M23 7l-7 5 7 5V7z"/><rect x="1" y="5" width="15" height="14" rx="2" ry="2"/>
                    </svg>
                    <span style={{ fontSize: '12px', fontWeight: 700, color: '#e2e8f0' }}>
                      {aiOnline ? 'CAMERA CHƯA ĐƯỢC GIÁM SÁT' : 'AI ENGINE CHƯA CHẠY'}
                    </span>
                    <span style={{ fontSize: '11px', color: '#94a3b8', maxWidth: '290px', lineHeight: 1.5 }}>
                      {aiOnline
                        ? 'AI chỉ suy luận một camera tại một thời điểm (giới hạn CPU). Bấm nút bên dưới để chuyển luồng phân tích sang camera này.'
                        : 'Bật ai-service (port 5000) để xem luồng và chuyển camera.'}
                    </span>
                  </div>
                )}

                {/* Badges */}
                <div style={{
                  position: 'absolute',
                  top: '10px',
                  left: '10px',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px'
                }}>
                  <span style={{
                    backgroundColor: 'rgba(15, 23, 42, 0.85)',
                    color: '#ffffff',
                    fontFamily: 'var(--mono)',
                    fontSize: '11px',
                    fontWeight: 700,
                    padding: '3px 8px',
                    borderRadius: '4px',
                  }}>
                    {cam.code}
                  </span>
                  {isActive && (
                    <span style={{
                      backgroundColor: '#dc2626',
                      color: '#ffffff',
                      fontSize: '10px',
                      fontWeight: 700,
                      padding: '2px 6px',
                      borderRadius: '4px',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '4px'
                    }}>
                      <span style={{ width: '6px', height: '6px', borderRadius: '50%', backgroundColor: '#ffffff' }} />
                      LIVE
                    </span>
                  )}
                </div>

                <div style={{
                  position: 'absolute',
                  top: '10px',
                  right: '10px',
                  backgroundColor: isActive ? '#16a34a' : '#475569',
                  color: '#ffffff',
                  fontSize: '10.5px',
                  fontWeight: 700,
                  padding: '3px 8px',
                  borderRadius: '4px',
                }}>
                  {isActive ? 'ĐANG GIÁM SÁT' : (aiOnline ? 'CHỜ CHUYỂN' : 'AI NGOẠI TUYẾN')}
                </div>
              </div>

              {/* Body Info */}
              <div style={{ padding: '16px 18px', display: 'flex', flexDirection: 'column', gap: '12px', flex: 1 }}>
                <div>
                  <h3 style={{ fontSize: '14px', fontWeight: 700, color: 'var(--t-primary)', margin: '0 0 3px 0' }}>
                    {cam.name}
                  </h3>
                  <div style={{ fontSize: '12px', color: 'var(--t-muted)' }}>
                    📍 {cam.locationDescription}
                  </div>
                </div>

                {/* Metadata spec grid */}
                <div style={{
                  backgroundColor: '#f8fafc',
                  borderRadius: '6px',
                  border: '1px solid var(--c-border)',
                  padding: '10px 12px',
                  display: 'grid',
                  gridTemplateColumns: '1fr 1fr',
                  gap: '8px',
                  fontSize: '12px'
                }}>
                  <div>
                    <span style={{ color: 'var(--t-muted)', display: 'block', fontSize: '10.5px' }}>MÔ HÌNH THỊ GIÁC:</span>
                    <strong style={{ color: '#1d4ed8' }}>{cam.aiModel}</strong>
                  </div>
                  <div>
                    <span style={{ color: 'var(--t-muted)', display: 'block', fontSize: '10.5px' }}>ĐỘ PHÂN GIẢI ĐANG XỬ LÝ:</span>
                    <strong style={{ color: 'var(--t-secondary)' }}>
                      {isActive && activeResolution ? activeResolution : '—'}
                    </strong>
                  </div>
                  <div>
                    <span style={{ color: 'var(--t-muted)', display: 'block', fontSize: '10.5px' }}>LƯU LƯỢNG PHIÊN NÀY:</span>
                    <strong style={{ color: '#16a34a' }}>{vehicles == null ? '—' : `${vehicles} lượt xe`}</strong>
                  </div>
                  <div>
                    <span style={{ color: 'var(--t-muted)', display: 'block', fontSize: '10.5px' }}>SỐ CA VI PHẠM PHIÊN NÀY:</span>
                    <strong style={{ color: violations > 0 ? '#dc2626' : 'var(--t-secondary)' }}>
                      {violations == null ? '—' : `${violations} ca`}
                    </strong>
                  </div>
                </div>

                <div style={{ fontSize: '10.5px', color: 'var(--t-muted)', marginTop: '-4px' }}>
                  Số liệu là của phiên AI đang chạy và chỉ áp dụng cho camera đang được giám sát.
                </div>

                {/* Action button */}
                <div style={{ marginTop: 'auto', paddingTop: '4px' }}>
                  {isActive ? (
                    <button
                      onClick={() => setSelectedCamera(cam)}
                      className="btn btn-primary"
                      style={{
                        width: '100%',
                        justifyContent: 'center',
                        padding: '8px 14px',
                        fontSize: '12.5px',
                        fontWeight: 600
                      }}
                    >
                      Xem Toàn Màn Hình HD ➔
                    </button>
                  ) : (
                    <button
                      onClick={() => switchTo(cam.id)}
                      disabled={!aiOnline || Boolean(switchingId)}
                      className="btn btn-primary"
                      style={{
                        width: '100%',
                        justifyContent: 'center',
                        padding: '8px 14px',
                        fontSize: '12.5px',
                        fontWeight: 600,
                        opacity: (!aiOnline || (switchingId && !isSwitching)) ? 0.55 : 1,
                        cursor: (!aiOnline || switchingId) ? 'not-allowed' : 'pointer',
                      }}
                    >
                      {isSwitching ? 'Đang chuyển camera...' : 'Chuyển AI Sang Camera Này ➔'}
                    </button>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Camera Detailed Inspection Modal */}
      {selectedCamera && (
        <div style={{
          position: 'fixed',
          inset: 0,
          backgroundColor: 'rgba(15, 23, 42, 0.65)',
          backdropFilter: 'blur(4px)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 1000,
          padding: '24px'
        }}>
          <div style={{
            backgroundColor: '#ffffff',
            border: '1px solid var(--c-border)',
            borderRadius: 'var(--r-xl)',
            width: '100%',
            maxWidth: '920px',
            overflow: 'hidden',
            boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.1)',
            display: 'flex',
            flexDirection: 'column'
          }}>
            {/* Modal Header */}
            <div style={{
              padding: '14px 20px',
              backgroundColor: '#f8fafc',
              borderBottom: '1px solid var(--c-border)',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center'
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <span style={{
                  backgroundColor: '#1d4ed8',
                  color: '#ffffff',
                  fontSize: '11.5px',
                  fontWeight: 700,
                  padding: '3px 8px',
                  borderRadius: '4px'
                }}>
                  {selectedCamera.code}
                </span>
                <span style={{ fontSize: '14px', fontWeight: 700, color: 'var(--t-primary)' }}>
                  {selectedCamera.name}
                </span>
              </div>
              <button
                onClick={() => setSelectedCamera(null)}
                style={{
                  backgroundColor: 'transparent',
                  border: 'none',
                  color: '#64748b',
                  cursor: 'pointer',
                  padding: '4px',
                }}
              >
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
                </svg>
              </button>
            </div>

            {/* Modal Body */}
            <div style={{ display: 'grid', gridTemplateColumns: '1.6fr 1fr', minHeight: '440px' }}>
              {/* Video Player Side */}
              <div style={{
                backgroundColor: '#090d16',
                position: 'relative',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                overflow: 'hidden',
                borderRight: '1px solid var(--c-border)'
              }}>
                {selectedIsActive ? (
                  <img
                    src={selectedCamera.streamUrl}
                    alt="Live Video"
                    style={{ maxWidth: '100%', maxHeight: '100%', objectFit: 'contain' }}
                  />
                ) : (
                  <div style={{
                    display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
                    gap: '10px', color: '#94a3b8', padding: '24px', textAlign: 'center',
                  }}>
                    <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                      <path d="M23 7l-7 5 7 5V7z"/><rect x="1" y="5" width="15" height="14" rx="2" ry="2"/>
                    </svg>
                    <div style={{ fontSize: '13px', fontWeight: 700, color: '#e2e8f0' }}>
                      {aiOnline ? 'Camera này chưa được AI giám sát' : 'AI Engine chưa chạy'}
                    </div>
                    <div style={{ fontSize: '11.5px', maxWidth: '320px', lineHeight: 1.5 }}>
                      AI chỉ chạy một camera tại một thời điểm. Chuyển sang camera này để xem luồng có phân tích.
                    </div>
                    <button
                      onClick={() => switchTo(selectedCamera.id)}
                      disabled={!aiOnline || Boolean(switchingId)}
                      className="btn btn-primary"
                      style={{ padding: '7px 14px', fontSize: '12px' }}
                    >
                      {switchingId === selectedCamera.id ? 'Đang chuyển camera...' : `Chuyển sang ${selectedCamera.code}`}
                    </button>
                  </div>
                )}
              </div>

              {/* Sidebar Info */}
              <div style={{ padding: '20px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
                <div>
                  <h4 style={{ fontSize: '11px', color: '#64748b', margin: '0 0 8px 0', textTransform: 'uppercase', letterSpacing: '0.4px', fontWeight: 700 }}>
                    Thông Số Kỹ Thuật Trạm Camera
                  </h4>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', fontSize: '12px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span style={{ color: '#64748b' }}>Vị Trí Lắp Đặt:</span>
                      <strong style={{ color: '#0f172a' }}>{selectedCamera.locationDescription}</strong>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span style={{ color: '#64748b' }}>Mô Hình Phân Tích:</span>
                      <strong style={{ color: '#1d4ed8' }}>{selectedCamera.aiModel}</strong>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span style={{ color: '#64748b' }}>Độ Phân Giải:</span>
                      <strong style={{ color: '#0f172a' }}>{selectedIsActive && activeResolution ? activeResolution : '—'}</strong>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span style={{ color: '#64748b' }}>Tốc Độ Khung Hình:</span>
                      <strong style={{ color: '#16a34a' }}>{selectedIsActive ? `${liveMetrics.fps || 0} FPS` : '—'}</strong>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span style={{ color: '#64748b' }}>Trạng Thái:</span>
                      <strong style={{ color: selectedIsActive ? '#16a34a' : '#64748b' }}>
                        {selectedIsActive ? 'ĐANG GIÁM SÁT' : 'CHỜ CHUYỂN'}
                      </strong>
                    </div>
                  </div>
                </div>

                <div style={{
                  backgroundColor: '#f8fafc',
                  borderRadius: '6px',
                  padding: '12px',
                  border: '1px solid var(--c-border)'
                }}>
                  <div style={{ fontSize: '11.5px', fontWeight: 700, color: '#334155', marginBottom: '8px' }}>
                    TRẠNG THÁI TRUYỀN PHÁT
                  </div>
                  <div style={{ fontSize: '12px', color: '#64748b', lineHeight: 1.5 }}>
                    Luồng MJPEG được AI giải mã và phát hiện đối tượng bằng YOLO11s + ViT + ByteTrack trước khi gửi dữ liệu vi phạm về Spring Boot Backend.
                    {!selectedIsActive && ' Camera này hiện không nằm trong luồng suy luận — bấm nút chuyển camera để giám sát.'}
                  </div>
                </div>

                <div style={{ marginTop: 'auto', display: 'flex', gap: '10px' }}>
                  <button
                    onClick={() => setSelectedCamera(null)}
                    className="btn btn-secondary"
                    style={{ flex: 1, justifyContent: 'center' }}
                  >
                    Đóng Cửa Sổ
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
