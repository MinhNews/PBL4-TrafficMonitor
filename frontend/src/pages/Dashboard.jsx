import React, { useState, useEffect } from 'react';
import { connectWebSocket } from '../services/socket';
import HourlyChart from '../components/dashboard/HourlyChart';
import ViolationTable from '../components/dashboard/ViolationTable';
import ViolationModal from '../components/violations/ViolationModal';

export default function Dashboard() {
  const [violations, setViolations] = useState([]);
  const [selectedViolation, setSelectedViolation] = useState(null);
  
  // State khởi tạo 24 khung giờ trong ngày cho Recharts
  const [hourlyData, setHourlyData] = useState(
    Array.from({ length: 24 }, (_, i) => ({ label: `${i}h`, count: 0 }))
  );

  const [stats, setStats] = useState({
    totalViolations: 0,
    redLightCount: 0,
    noHelmetCount: 0
  });

  useEffect(() => {
    // Kích hoạt kết nối WebSocket STOMP real-time
    const client = connectWebSocket((newViolation) => {
      // 1. Tự động chèn bản ghi vi phạm mới lên đầu danh sách
      setViolations((prev) => [newViolation, ...prev]);

      // 2. Tự động nhảy số đếm ở các thẻ thống kê StatCard
      setStats((prev) => ({
        ...prev,
        totalViolations: prev.totalViolations + 1,
        redLightCount: (newViolation.violationType === 'RED_LIGHT_CROSS' || newViolation.type === 'RED_LIGHT_CROSS')
          ? prev.redLightCount + 1 : prev.redLightCount,
        noHelmetCount: (newViolation.violationType === 'NO_HELMET' || newViolation.type === 'NO_HELMET')
          ? prev.noHelmetCount + 1 : prev.noHelmetCount
      }));

      // 3. Tự động cập nhật cột biểu đồ Recharts tương ứng với khung giờ hiện tại
      const currentHour = new Date().getHours();
      setHourlyData((prev) =>
        prev.map((item, index) =>
          index === currentHour ? { ...item, count: item.count + 1 } : item
        )
      );
    });

    return () => client.deactivate(); // Ngắt kết nối khi component unmount
  }, []);

  return (
    <div style={{ padding: '24px', backgroundColor: '#f8fafc', minHeight: '100vh' }}>
      <div style={{ marginBottom: '24px' }}>
        <h1 style={{ fontSize: '24px', fontWeight: '800', color: '#0f172a', margin: 0 }}>
          🚦 Hệ Thống Giám Sát Giao Thông Real-Time (PBL4)
        </h1>
        <p style={{ color: '#64748b', fontSize: '14px', marginTop: '4px' }}>
          Tự động phát hiện vi phạm NĐ 168/2024/NĐ-CP qua AI & Cập nhật thời gian thực
        </p>
      </div>

      {/* 1. Các thẻ Thống kê Stat Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '16px', marginBottom: '24px' }}>
        <div style={{ backgroundColor: '#fff', padding: '20px', borderRadius: '16px', boxShadow: '0 4px 20px rgba(0,0,0,0.05)' }}>
          <div style={{ fontSize: '13px', color: '#64748b', fontWeight: '600' }}>TỔNG SỐ VI PHẠM</div>
          <div style={{ fontSize: '28px', fontWeight: '900', color: '#0f172a', marginTop: '8px' }}>{stats.totalViolations}</div>
        </div>
        <div style={{ backgroundColor: '#fff', padding: '20px', borderRadius: '16px', boxShadow: '0 4px 20px rgba(0,0,0,0.05)' }}>
          <div style={{ fontSize: '13px', color: '#dc2626', fontWeight: '600' }}>🚨 VƯỢT ĐÈN ĐỎ</div>
          <div style={{ fontSize: '28px', fontWeight: '900', color: '#dc2626', marginTop: '8px' }}>{stats.redLightCount}</div>
        </div>
        <div style={{ backgroundColor: '#fff', padding: '20px', borderRadius: '16px', boxShadow: '0 4px 20px rgba(0,0,0,0.05)' }}>
          <div style={{ fontSize: '13px', color: '#d97706', fontWeight: '600' }}>🪖 KHÔNG ĐỘI MŨ BH</div>
          <div style={{ fontSize: '28px', fontWeight: '900', color: '#d97706', marginTop: '8px' }}>{stats.noHelmetCount}</div>
        </div>
      </div>

      {/* 2. Biểu đồ 24h Recharts */}
      <div style={{ marginBottom: '24px' }}>
        <HourlyChart data={hourlyData} />
      </div>

      {/* 3. Bảng dữ liệu vi phạm */}
      <ViolationTable 
        violations={violations} 
        onSelectViolation={(v) => setSelectedViolation(v)} 
      />

      {/* 4. Modal xem chi tiết hình phạt NĐ 168/2024 */}
      {selectedViolation && (
        <ViolationModal 
          violation={selectedViolation} 
          onClose={() => setSelectedViolation(null)} 
        />
      )}
    </div>
  );
}