import React, { useState, useEffect } from 'react';

const CAMERAS_DATA = [
  {
    id: 1,
    code: 'CAM-HK-01',
    name: 'Camera 01: Ngã Tư Hòa Khánh (Phía Bắc)',
    intersection: 'Nút Giao Tôn Đức Thắng - Nguyễn Lương Bằng',
    location: 'Quận Liên Chiểu, TP. Đà Nẵng',
    coords: { x: '35%', y: '40%' },
    ip: '127.0.0.1:5000',
    protocol: 'MJPEG / HTTP RTSP',
    resolution: 'Vertical 4K (405×720 Stream)',
    aiModel: 'YOLO11n + ByteTrack',
    status: 'ONLINE',
    streamUrl: 'http://localhost:5000/video_feed',
    latency: '18ms',
    violationsCount: 37,
    vehiclesPassed: 217,
  },
  {
    id: 2,
    code: 'CAM-HK-02',
    name: 'Camera 02: Ngã Tư Hòa Khánh (Phía Nam)',
    intersection: 'Nút Giao Tôn Đức Thắng - Âu Cơ',
    location: 'Quận Liên Chiểu, TP. Đà Nẵng',
    coords: { x: '42%', y: '48%' },
    ip: '192.168.1.106:554',
    protocol: 'RTSP H.264',
    resolution: '1920×1080 @ 30 FPS',
    aiModel: 'Deformable DETR (Standby)',
    status: 'STANDBY',
    streamUrl: null,
    latency: '24ms',
    violationsCount: 0,
    vehiclesPassed: 0,
  },
  {
    id: 3,
    code: 'CAM-BK-01',
    name: 'Camera 03: Cổng ĐH Bách Khoa ĐN',
    intersection: 'Đường Nguyễn Lương Bằng — Hòa Khánh Bắc',
    location: 'Liên Chiểu, TP. Đà Nẵng',
    coords: { x: '28%', y: '30%' },
    ip: '192.168.1.107:554',
    protocol: 'RTSP H.265',
    resolution: '1280×720 @ 30 FPS',
    aiModel: 'YOLO11n + ViT Helmet',
    status: 'STANDBY',
    streamUrl: null,
    latency: '32ms',
    violationsCount: 0,
    vehiclesPassed: 0,
  },
  {
    id: 4,
    code: 'CAM-CR-01',
    name: 'Camera 04: Cầu Rồng (Đầu Tây)',
    intersection: 'Nút Giao Bạch Đằng - 2 Tháng 9',
    location: 'Quận Hải Châu, TP. Đà Nẵng',
    coords: { x: '68%', y: '62%' },
    ip: '192.168.1.110:554',
    protocol: 'RTSP 4K UltraHD',
    resolution: '3840×2160 @ 60 FPS',
    aiModel: 'YOLO11x + ByteTrack',
    status: 'STANDBY',
    streamUrl: null,
    latency: '45ms',
    violationsCount: 0,
    vehiclesPassed: 0,
  }
];

export default function CamerasMap() {
  const [activeTab, setActiveTab] = useState('grid'); // 'grid' | 'gis'
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [selectedCamera, setSelectedCamera] = useState(null);
  const [liveMetrics, setLiveMetrics] = useState({ fps: 30, light: 'GREEN', vehiclesPassed: 217, violations: 37 });

  useEffect(() => {
    async function checkStatus() {
      try {
        const res = await fetch('http://localhost:5000/status', { signal: AbortSignal.timeout(1500) });
        if (res.ok) {
          const data = await res.json();
          setLiveMetrics(data);
        }
      } catch {}
    }
    checkStatus();
    const interval = setInterval(checkStatus, 3000);
    return () => clearInterval(interval);
  }, []);

  const filteredCameras = CAMERAS_DATA.filter(cam => {
    if (statusFilter === 'ALL') return true;
    return cam.status === statusFilter;
  });

  return (
    <div style={{ padding: '24px', display: 'flex', flexDirection: 'column', gap: '20px' }}>
      
      {/* Header bar */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '14px' }}>
        <div>
          <h1 style={{ fontSize: '18px', fontWeight: 800, color: 'var(--t-primary)', margin: 0 }}>
            Mạng Lưới Hạ Tầng Camera Giám Sát
          </h1>
          <div style={{ fontSize: '12px', color: 'var(--t-muted)', marginTop: '3px' }}>
            Quản trị luồng camera luồng IP/RTSP và trạng thái các trạm thị giác máy tính tại các nút giao trọng điểm
          </div>
        </div>

        {/* View toggle & Filters */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
          {/* Status filter */}
          <div style={{
            display: 'flex',
            backgroundColor: '#ffffff',
            borderRadius: '6px',
            border: '1px solid var(--c-border)',
            padding: '2px',
          }}>
            {[
              { id: 'ALL', label: 'Tất Cả Camera' },
              { id: 'ONLINE', label: 'Trực Tuyến (1)' },
              { id: 'STANDBY', label: 'Chế Độ Chờ (3)' },
            ].map(f => (
              <button
                key={f.id}
                onClick={() => setStatusFilter(f.id)}
                style={{
                  padding: '5px 12px',
                  borderRadius: '4px',
                  fontSize: '12px',
                  fontWeight: 600,
                  backgroundColor: statusFilter === f.id ? 'var(--c-blue)' : 'transparent',
                  color: statusFilter === f.id ? '#ffffff' : 'var(--t-secondary)',
                  transition: 'all 0.15s ease'
                }}
              >
                {f.label}
              </button>
            ))}
          </div>

          {/* View switcher */}
          <div style={{
            display: 'flex',
            backgroundColor: '#ffffff',
            borderRadius: '6px',
            border: '1px solid var(--c-border)',
            padding: '2px',
          }}>
            <button
              onClick={() => setActiveTab('grid')}
              style={{
                padding: '6px 14px',
                borderRadius: '4px',
                fontSize: '12px',
                fontWeight: 600,
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                backgroundColor: activeTab === 'grid' ? '#f1f5f9' : 'transparent',
                color: activeTab === 'grid' ? 'var(--t-primary)' : 'var(--t-muted)',
              }}
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/>
                <rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/>
              </svg>
              Danh Sách Camera
            </button>
            <button
              onClick={() => setActiveTab('gis')}
              style={{
                padding: '6px 14px',
                borderRadius: '4px',
                fontSize: '12px',
                fontWeight: 600,
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                backgroundColor: activeTab === 'gis' ? '#f1f5f9' : 'transparent',
                color: activeTab === 'gis' ? 'var(--t-primary)' : 'var(--t-muted)',
              }}
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <polygon points="1 6 1 22 8 18 16 22 23 18 23 2 16 6 8 2 1 6"/>
                <line x1="8" y1="2" x2="8" y2="18"/><line x1="16" y1="6" x2="16" y2="22"/>
              </svg>
              Bản Đồ Nút Giao GIS
            </button>
          </div>
        </div>
      </div>

      {/* Main content body */}
      {activeTab === 'grid' ? (
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fill, minmax(360px, 1fr))',
          gap: '20px'
        }}>
          {filteredCameras.map((cam) => {
            const isOnline = cam.status === 'ONLINE';
            const vehicles = isOnline ? (liveMetrics.vehiclesPassed || cam.vehiclesPassed) : cam.vehiclesPassed;
            const violations = isOnline ? (liveMetrics.violations || cam.violationsCount) : cam.violationsCount;

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
                {/* CCTV Stream Container (object-fit: contain to show full vertical video) */}
                <div style={{
                  height: '240px',
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
                        CAMERA ĐANG Ở CHẾ ĐỘ CHỜ
                      </span>
                    </div>
                  )}

                  {/* Top badges */}
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
                      }}>
                        TRỰC TIẾP
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
                    {isOnline ? 'KẾT NỐI TỐT' : 'CHỜ KÍCH HOẠT'}
                  </div>
                </div>

                {/* Body info */}
                <div style={{ padding: '16px 18px', display: 'flex', flexDirection: 'column', gap: '12px', flex: 1 }}>
                  <div>
                    <h3 style={{ fontSize: '14px', fontWeight: 700, color: 'var(--t-primary)', margin: '0 0 3px 0' }}>
                      {cam.name}
                    </h3>
                    <div style={{ fontSize: '12px', color: 'var(--t-muted)' }}>
                      📍 {cam.intersection}
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
                      className={isOnline ? 'btn btn-primary' : 'btn btn-secondary'}
                      style={{
                        width: '100%',
                        justifyContent: 'center',
                        padding: '8px 14px',
                        fontSize: '12.5px',
                        fontWeight: 600
                      }}
                    >
                      {isOnline ? 'Mở Khung Hình Chi Tiết HD ➔' : 'Cấu Hình Trạm Camera'}
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        /* Clean GIS Map View */
        <div style={{
          backgroundColor: '#ffffff',
          border: '1px solid var(--c-border)',
          borderRadius: 'var(--r-lg)',
          padding: '24px',
          minHeight: '520px',
          position: 'relative',
          display: 'flex',
          flexDirection: 'column',
          boxShadow: '0 1px 3px 0 rgba(0, 0, 0, 0.04)',
        }}>
          {/* Map Header */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
            <div>
              <h2 style={{ fontSize: '15px', fontWeight: 700, color: 'var(--t-primary)', margin: 0 }}>
                Bản Đồ Nút Giao Thông TP. Đà Nẵng
              </h2>
              <div style={{ fontSize: '12px', color: 'var(--t-muted)' }}>
                Hệ thống định vị các trạm camera quan sát và kết nối điều hành tín hiệu
              </div>
            </div>
            <div style={{
              backgroundColor: '#f8fafc',
              border: '1px solid var(--c-border)',
              padding: '6px 12px',
              borderRadius: '6px',
              fontSize: '12px',
              fontWeight: 500,
              color: '#475569'
            }}>
              Trung Tâm Điều Hành: 16.0544° N, 108.2022° E
            </div>
          </div>

          {/* Interactive GIS Visualizer Canvas */}
          <div style={{
            flex: 1,
            minHeight: '420px',
            position: 'relative',
            borderRadius: '8px',
            backgroundColor: '#f1f5f9',
            border: '1px solid #cbd5e1',
            overflow: 'hidden'
          }}>
            {/* SVG Connecting Routes between nodes */}
            <svg style={{ position: 'absolute', inset: 0, width: '100%', height: '100%' }}>
              <line x1="35%" y1="40%" x2="42%" y2="48%" stroke="#94a3b8" strokeWidth="3" strokeDasharray="5,5" />
              <line x1="35%" y1="40%" x2="28%" y2="30%" stroke="#1d4ed8" strokeWidth="3" />
              <line x1="42%" y1="48%" x2="68%" y2="62%" stroke="#94a3b8" strokeWidth="2" strokeDasharray="6,6" />
            </svg>

            {/* Render Nodes */}
            {CAMERAS_DATA.map(cam => {
              const isOnline = cam.status === 'ONLINE';
              return (
                <div
                  key={cam.id}
                  onClick={() => setSelectedCamera(cam)}
                  style={{
                    position: 'absolute',
                    left: cam.coords.x,
                    top: cam.coords.y,
                    transform: 'translate(-50%, -50%)',
                    cursor: 'pointer',
                    zIndex: 20,
                  }}
                >
                  <div style={{
                    width: '32px', height: '32px',
                    borderRadius: '50%',
                    backgroundColor: isOnline ? '#1d4ed8' : '#ffffff',
                    border: isOnline ? '3px solid #93c5fd' : '2px solid #94a3b8',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    boxShadow: '0 2px 8px rgba(0,0,0,0.15)',
                  }}>
                    <span style={{
                      width: '10px', height: '10px', borderRadius: '50%',
                      backgroundColor: isOnline ? '#22c55e' : '#94a3b8'
                    }} />
                  </div>

                  {/* Clean Label */}
                  <div style={{
                    marginTop: '6px',
                    backgroundColor: '#ffffff',
                    border: '1px solid var(--c-border)',
                    borderRadius: '4px',
                    padding: '3px 8px',
                    whiteSpace: 'nowrap',
                    textAlign: 'center',
                    boxShadow: '0 2px 4px rgba(0,0,0,0.06)'
                  }}>
                    <div style={{ fontSize: '11px', fontWeight: 700, color: 'var(--t-primary)' }}>{cam.code}</div>
                    <div style={{ fontSize: '10px', color: isOnline ? '#16a34a' : 'var(--t-muted)' }}>
                      {isOnline ? 'Đang hoạt động' : 'Chờ kết nối'}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

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
                {selectedCamera.status === 'ONLINE' ? (
                  <img
                    src={selectedCamera.streamUrl}
                    alt="Live Video"
                    style={{ maxWidth: '100%', maxHeight: '100%', objectFit: 'contain' }}
                  />
                ) : (
                  <div style={{ textAlign: 'center', color: '#94a3b8' }}>
                    <div style={{ fontSize: '32px', marginBottom: '8px' }}>📡</div>
                    <div style={{ fontSize: '13px', fontWeight: 700 }}>Chờ mở cổng RTSP từ camera</div>
                    <div style={{ fontSize: '11px', marginTop: '4px', color: '#64748b' }}>IP: {selectedCamera.ip}</div>
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
                      <strong style={{ color: '#0f172a' }}>{selectedCamera.location}</strong>
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
                      <span style={{ color: '#64748b' }}>Độ Trễ Mạng (Ping):</span>
                      <strong style={{ color: '#16a34a' }}>{selectedCamera.latency}</strong>
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
                    Luồng RTSP/MJPEG được giải mã và gắn nhãn AI thời gian thực tại trạm biên trước khi phát tới trung tâm điều hành.
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
