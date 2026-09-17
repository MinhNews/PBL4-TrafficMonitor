import React, { useState, useEffect } from 'react';
import StatCard from '../components/dashboard/StatCard';
import LiveCamera from '../components/dashboard/LiveCamera';
import ViolationTable from '../components/dashboard/ViolationTable';
import ViolationModal from '../components/violations/ViolationModal';
import { statsAPI, violationAPI } from '../services/api';

export default function Dashboard() {
    const [stats, setStats] = useState({ totalViolations: 0, noHelmetCount: 0, redLightCount: 0, vehiclesPassedToday: 0 });
    const [violations, setViolations] = useState([]);
    const [selectedViolation, setSelectedViolation] = useState(null);

    useEffect(() => {
        loadData();
        const interval = setInterval(loadData, 15000); // Tự động làm mới sau mỗi 15 giây
        return () => clearInterval(interval);
    }, []);

    async function loadData() {
        try {
            const [statsRes, violationsRes] = await Promise.all([
                statsAPI.getToday(),
                violationAPI.getAll({ page: 0, size: 10 }),
            ]);
            setStats(statsRes.data);
            setViolations(violationsRes.data.content);
        } catch (err) {
            console.error('Lỗi nạp dữ liệu từ Backend:', err);
        }
    }

    async function handleConfirm(id, notes) {
        await violationAPI.confirm(id, notes);
        setSelectedViolation(null);
        loadData();
    }

    async function handleDismiss(id, notes) {
        await violationAPI.dismiss(id, notes);
        setSelectedViolation(null);
        loadData();
    }

    return (
        <div style={{ padding: '32px', backgroundColor: '#f8fafc', minHeight: '100vh', fontFamily: 'Inter, sans-serif' }}>
            <header style={{ marginBottom: '28px' }}>
                <h1 style={{ fontSize: '28px', fontWeight: '900', color: '#0f172a', margin: 0 }}>
                    🚦 Trung Tâm Giám Sát Giao Thông Thông Minh
                </h1>
                <p style={{ color: '#64748b', margin: '4px 0 0 0' }}>Hệ thống phát hiện vi phạm tự động bằng Deformable DETR & IoT</p>
            </header>

            {/* 4 THẺ THỐNG KÊ */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '20px', marginBottom: '28px' }}>
                <StatCard title="TỔNG VI PHẠM HÔM NAY" value={stats.totalViolations} icon="🚨" color="#dc2626" subText="Tổng lượt bắt được" />
                <StatCard title="KHÔNG ĐỘI MŨ BẢO HIỂM" value={stats.noHelmetCount} icon="⛑️" color="#d97706" subText="Lỗi ViT nhận diện" />
                <StatCard title="VƯỢT ĐÈN ĐỎ" value={stats.redLightCount} icon="🚦" color="#7c3aed" subText="Lỗi ByteTrack nhận diện" />
                <StatCard title="LƯU LƯỢNG XE QUA" value={stats.vehiclesPassedToday} icon="🚗" color="#059669" subText="Tổng phương tiện hôm nay" />
            </div>

            {/* KHUNG CAMERA & BẢNG VI PHẠM */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1.25fr', gap: '24px', alignItems: 'start' }}>
                <LiveCamera />
                <ViolationTable violations={violations} onSelectViolation={setSelectedViolation} />
            </div>

            {/* MODAL DUYỆT PHẠT */}
            <ViolationModal
                violation={selectedViolation}
                onClose={() => setSelectedViolation(null)}
                onConfirm={handleConfirm}
                onDismiss={handleDismiss}
            />
        </div>
    );
}