import React, { useState, useEffect } from 'react';
import { statsAPI, violationAPI } from '../services/api';
import { connectWebSocket } from '../services/socket';
import StatCard from '../components/dashboard/StatCard';
import HourlyChart from '../components/dashboard/HourlyChart';
import LiveCamera from '../components/dashboard/LiveCamera';
import ViolationTable from '../components/dashboard/ViolationTable';
import ViolationModal from '../components/violations/ViolationModal';

export default function Dashboard() {
  const [violations, setViolations] = useState([]);
  const [selectedViolation, setSelectedViolation] = useState(null);

  // Khởi tạo sẵn 24 khung giờ cho biểu đồ Recharts (0h -> 23h)
  const [hourlyData, setHourlyData] = useState(
    Array.from({ length: 24 }, (_, i) => ({ label: `${i}h`, count: 0 }))
  );

  const [stats, setStats] = useState({
    totalViolations: 0,
    redLightCount: 0,
    noHelmetCount: 0,
    vehiclesPassedToday: 0
  });

  // 1. Nạp dữ liệu ban đầu từ Backend REST API
  async function loadData() {
    try {
      const [statsRes, violationsRes, hourlyRes] = await Promise.all([
        statsAPI.getToday(),
        violationAPI.getAll({ page: 0, size: 10 }),
        statsAPI.getHourly()
      ]);

      if (statsRes?.data) {
        setStats(statsRes.data);
      }
      if (violationsRes?.data?.content) {
        setViolations(violationsRes.data.content);
      }
      if (hourlyRes?.data && Array.isArray(hourlyRes.data)) {
        setHourlyData(hourlyRes.data);
      }
    } catch (err) {
      console.error('❌ Lỗi nạp dữ liệu ban đầu từ Backend:', err);
    }
  }

  // 2. Hàm xử lý CSGT duyệt phạt / bác bỏ
  async function handleConfirm(id, notes) {
    try {
      await violationAPI.confirm(id, notes);
      setSelectedViolation(null);
      await loadData();
    } catch (err) {
      console.error('❌ Lỗi duyệt vi phạm:', err);
    }
  }

  async function handleDismiss(id, notes) {
    try {
      await violationAPI.dismiss(id, notes);
      setSelectedViolation(null);
      await loadData();
    } catch (err) {
      console.error('❌ Lỗi bác bỏ vi phạm:', err);
    }
  }

  // 3. Vòng đời: Load ban đầu + Lắng nghe WebSocket Real-time STOMP
  useEffect(() => {
    loadData();

    // Kết nối WebSocket thời gian thực (Quest 3 - Task 3.1 & 3.2)
    const client = connectWebSocket((newViolation) => {
      console.log('🚨 [Real-Time] Nhận bản ghi vi phạm mới:', newViolation);

      // 1. Chèn ngay bản ghi mới lên đầu danh sách vi phạm
      setViolations((prev) => [newViolation, ...prev]);

      // 2. Tự động tăng số đếm ở các thẻ thống kê StatCard
      const isRedLight = newViolation.violationType === 'RED_LIGHT_CROSS' || newViolation.type === 'RED_LIGHT_CROSS';
      const isNoHelmet = newViolation.violationType === 'NO_HELMET' || newViolation.type === 'NO_HELMET';

      setStats((prev) => ({
        ...prev,
        totalViolations: (prev.totalViolations || 0) + 1,
        redLightCount: isRedLight ? (prev.redLightCount || 0) + 1 : prev.redLightCount,
        noHelmetCount: isNoHelmet ? (prev.noHelmetCount || 0) + 1 : prev.noHelmetCount
      }));

      // 3. Tự động cập nhật cột biểu đồ Recharts tương ứng khung giờ hiện tại
      const currentHour = new Date().getHours();
      setHourlyData((prev) =>
        prev.map((item, index) =>
          index === currentHour ? { ...item, count: (item.count || 0) + 1 } : item
        )
      );
    });

    return () => client.deactivate(); // Ngắt kết nối khi component unmount
  }, []);

  return (
    <div style={{ padding: '28px', backgroundColor: '#f8fafc', minHeight: '100vh', fontFamily: 'Inter, sans-serif' }}>
      {/* Tiêu đề Header CAND & Giám sát */}
      <header style={{ marginBottom: '24px' }}>
        <h1 style={{ fontSize: '26px', fontWeight: '800', color: '#0f172a', margin: 0 }}>
          🚦 Hệ Thống Giám Sát Giao Thông Thông Minh Real-Time (PBL4)
        </h1>
        <p style={{ color: '#64748b', fontSize: '14px', marginTop: '6px' }}>
          Tự động phát hiện vi phạm Nghị định 168/2024/NĐ-CP qua AI & Cập nhật thời gian thực STOMP
        </p>
      </header>

      {/* 4 Thẻ Thống Kê Stat Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(230px, 1fr))', gap: '18px', marginBottom: '24px' }}>
        <StatCard
          title="TỔNG SỐ VI PHẠM"
          value={stats.totalViolations}
          icon="🚨"
          color="#dc2626"
          subText="Tổng lượt bắt được hôm nay"
        />
        <StatCard
          title="VƯỢT ĐÈN ĐỎ"
          value={stats.redLightCount}
          icon="🚦"
          color="#ef4444"
          subText="Trừ 4 điểm GPLX (NĐ 168)"
        />
        <StatCard
          title="KHÔNG ĐỘI MŨ BH"
          value={stats.noHelmetCount}
          icon="⛑️"
          color="#d97706"
          subText="Phạt 800k - 1.000.000 VNĐ"
        />
        <StatCard
          title="LƯU LƯỢNG XE QUA"
          value={stats.vehiclesPassedToday}
          icon="🚗"
          color="#059669"
          subText="Tổng phương tiện hôm nay"
        />
      </div>

      {/* Biểu đồ Recharts 24h Mật độ vi phạm */}
      <div style={{ marginBottom: '24px' }}>
        <HourlyChart data={hourlyData} />
      </div>

      {/* Khung Camera Giám sát Live & Bảng Vi Phạm */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1.35fr', gap: '24px', alignItems: 'start' }}>
        <LiveCamera />
        <ViolationTable
          violations={violations}
          onSelectViolation={(v) => setSelectedViolation(v)}
        />
      </div>

      {/* Modal CSGT Duyệt Phạt Nguội & Khung Hình Phạt NĐ 168/2024 */}
      {selectedViolation && (
        <ViolationModal
          violation={selectedViolation}
          onClose={() => setSelectedViolation(null)}
          onConfirm={handleConfirm}
          onDismiss={handleDismiss}
        />
      )}
    </div>
  );
}