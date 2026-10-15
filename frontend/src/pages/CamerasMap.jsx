import React, { useState, useEffect } from 'react';
import { cameraAPI } from '../services/api';

const DEFAULT_CAMERA = {
  id: 1,
  code: 'CAM-HK-01',
  name: 'Camera 01: Ngã Tư Hòa Khánh',
  regionName: 'Ngã tư Hòa Khánh',
  locationDescription: 'Góc Tây Bắc nút giao — Quận Liên Chiểu, TP. Đà Nẵng',
  streamUrl: 'http://localhost:5000/video_feed',
  aiModel: 'YOLO11n + ByteTrack',
  resolution: 'Vertical HD (405×720 Stream)',
  status: 'ONLINE',
};

export default function CamerasMap() {
  const [cameras, setCameras] = useState([DEFAULT_CAMERA]);
  const [loading, setLoading] = useState(false);
  const [selectedCamera, setSelectedCamera] = useState(null);
  const [liveMetrics, setLiveMetrics] = useState({ fps: 30, light: 'GREEN', vehiclesPassed: 0, violations: 0 });

  // 1. Fetch active cameras from Backend API
  useEffect(() => {
    async function loadCameras() {
      try {
        setLoading(true);
        const res = await cameraAPI.getAll();
        if (res.data && res.data.length > 0) {
          const mapped = res.data.map(c => ({
            id: c.id,
            code: `CAM-HK-0${c.id}`,
            name: c.name || `Camera ${c.id}`,
            regionName: c.regionName || 'Ngã tư Hòa Khánh',
            locationDescription: c.locationDescription || 'Nút giao giám sát',
            streamUrl: c.streamUrl || 'http://localhost:5000/video_feed',
            aiModel: 'YOLO11n + ByteTrack',
            resolution: 'Vertical HD (405×720 Stream)',
            status: c.isActive ? 'ONLINE' : 'OFFLINE',
          }));
          setCameras(mapped);
        }
      } catch (err) {
        console.warn('Không tải được danh sách camera từ backend, sử dụng camera mặc định', err);
      } finally {
        setLoading(false);
      }
    }
    loadCameras();
  }, []);

  // 2. Poll live metrics from AI service
  useEffect(() => {
    async function checkStatus() {
      try {
        const res = await fetch('http://localhost:5000/status', { signal: AbortSignal.timeout(1500) });
        if (res.ok) {
          const data = await res.json();
          setLiveMetrics(data);
        }
      } catch {
        // AI service offline or busy
      }
    }
    checkStatus();
    const interval = setInterval(checkStatus, 2500);
    return () => clearInterval(interval);
  }, []);

  return (
    <div style={{ padding: '24px', display: 'flex', flexDirection: 'column', gap: '20px' }}>
      
      {/* Header bar */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '14px' }}>
        <div>
          <h1 style={{ fontSize: '18px', fontWeight: 800, color: 'var(--t-primary)', margin: 0 }}>
            Hạ Tầng Camera Giám Sát Nút Giao
          </h1>
          <div style={{ fontSize: '12px', color: 'var(--t-muted)', marginTop: '3px' }}>
            Quản trị luồng camera trực tiếp từ trạm thị giác máy tính và trạng thái nhận diện giao thông
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <span style={{
            fontSize: '12px',
            fontWeight: 600,
            padding: '4px 10px',
            borderRadius: '4px',
            backgroundColor: '#dcfce7',
            color: '#15803d',
            display: 'flex',
            alignItems: 'center',
            gap: '6px'
          }}>
            <span style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: '#22c55e' }} />
            {cameras.length} Trạm Đang Hoạt Động
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
          const isOnline = cam.status === 'ONLINE';
          const vehicles = liveMetrics.vehiclesPassed || 0;
          const violations = liveMetrics.violations || 0;

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
                {isOnline ? (
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
                  <div style={{
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    gap: '8px',
                    color: '#64748b'
                  }}>
                    <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                      <path d="M23 7l-7 5 7 5V7z"/><rect x="1" y="5" width="15" height="14" rx="2" ry="2"/>
                    </svg>
                    <span style={{ fontSize: '12px', fontWeight: 600 }}>
                      MẤT TÍN HIỆU CAMERA
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
                  {isOnline && (
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
                  backgroundColor: isOnline ? '#16a34a' : '#64748b',
                  color: '#ffffff',
                  fontSize: '10.5px',
                  fontWeight: 700,
                  padding: '3px 8px',
                  borderRadius: '4px',
                }}>
                  {isOnline ? 'KẾT NỐI TỐT' : 'NGOẠI TUYẾN'}
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
                    <span style={{ color: 'var(--t-muted)', display: 'block', fontSize: '10.5px' }}>ĐỘ PHÂN GIẢI:</span>
                    <strong style={{ color: 'var(--t-secondary)' }}>{cam.resolution}</strong>
                  </div>
                  <div>
                    <span style={{ color: 'var(--t-muted)', display: 'block', fontSize: '10.5px' }}>LƯU LƯỢNG XE QUA:</span>
                    <strong style={{ color: '#16a34a' }}>{vehicles} lượt xe</strong>
                  </div>
                  <div>
                    <span style={{ color: 'var(--t-muted)', display: 'block', fontSize: '10.5px' }}>SỐ CA VI PHẠM:</span>
                    <strong style={{ color: violations > 0 ? '#dc2626' : 'var(--t-secondary)' }}>{violations} ca</strong>
                  </div>
                </div>

                {/* Action button */}
                <div style={{ marginTop: 'auto', paddingTop: '4px' }}>
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
                <img
                  src={selectedCamera.streamUrl}
                  alt="Live Video"
                  style={{ maxWidth: '100%', maxHeight: '100%', objectFit: 'contain' }}
                />
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
                      <strong style={{ color: '#0f172a' }}>{selectedCamera.resolution}</strong>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span style={{ color: '#64748b' }}>Tốc Độ Khung Hình:</span>
                      <strong style={{ color: '#16a34a' }}>{liveMetrics.fps || 30} FPS</strong>
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
                    Luồng RTSP/MJPEG được giải mã và phát hiện đối tượng thời gian thực bằng YOLO11n + ByteTrack trước khi chuyển dữ liệu vi phạm về Spring Boot Backend.
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
