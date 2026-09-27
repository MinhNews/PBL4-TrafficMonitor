import React, { useState, useEffect, useCallback } from 'react';
import { violationAPI } from '../services/api';
import { useAuth } from '../context/AuthContext';

const VIOLATION_TYPES = [
    { value: 'ALL', label: 'Tất Cả Loại' },
    { value: 'RED_LIGHT_CROSS', label: 'Vượt Đèn Đỏ' },
    { value: 'NO_HELMET', label: 'Không Đội Mũ BH' },
];
const STATUS_TYPES = [
    { value: 'ALL', label: 'Tất Cả Trạng Thái' },
    { value: 'PENDING', label: 'Chờ Duyệt' },
    { value: 'CONFIRMED', label: 'Đã Xác Nhận' },
    { value: 'DISMISSED', label: 'Đã Bác Bỏ' },
];

export default function ViolationsManager({ onOpenModal }) {
    const { isAdmin } = useAuth();
    const [violations, setViolations] = useState([]);
    const [typeFilter, setTypeFilter] = useState('ALL');
    const [statusFilter, setStatusFilter] = useState('ALL');
    const [searchTerm, setSearchTerm] = useState('');
    const [loading, setLoading] = useState(false);
    const [selectedIds, setSelectedIds] = useState(new Set());

    const loadViolations = useCallback(() => {
        setLoading(true);
        violationAPI.getAll({ page: 0, size: 200 })
            .then(res => { if (res?.data?.content) setViolations(res.data.content); })
            .catch(err => console.error('Error loading violations:', err))
            .finally(() => setLoading(false));
    }, []);

    useEffect(() => { loadViolations(); }, [loadViolations]);

    useEffect(() => {
        function handleUpdate(e) {
            const { id, status, notes } = e.detail || {};
            if (id && status) {
                setViolations(prev => prev.map(v => v.id === id ? { ...v, status, notes: notes !== undefined ? notes : v.notes } : v));
            }
        }
        window.addEventListener('violation:updated', handleUpdate);
        return () => window.removeEventListener('violation:updated', handleUpdate);
    }, []);

    const filtered = violations.filter(v => {
        const type = v.type || v.violationType;
        const matchType = typeFilter === 'ALL' || type === typeFilter;
        const matchStatus = statusFilter === 'ALL' || v.status === statusFilter;
        const q = searchTerm.trim().toLowerCase();
        const matchSearch = !q || String(v.id).includes(q)
            || (v.licensePlate || '').toLowerCase().includes(q)
            || (v.cameraName || '').toLowerCase().includes(q);
        return matchType && matchStatus && matchSearch;
    });

    const pendingCount = violations.filter(v => v.status === 'PENDING').length;
    const confirmedCount = violations.filter(v => v.status === 'CONFIRMED').length;

    function toggleSelect(id) {
        setSelectedIds(prev => {
            const next = new Set(prev);
            next.has(id) ? next.delete(id) : next.add(id);
            return next;
        });
    }

    return (
        <div style={{ padding: '20px 24px', display: 'flex', flexDirection: 'column', gap: '16px' }}>

            {/* Page header */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <div>
                    <h1 style={{ fontSize: '17px', fontWeight: 800, color: 'var(--t-primary)', margin: 0 }}>
                        Hồ Sơ Vi Phạm Giao Thông
                    </h1>
                    <div style={{ fontSize: '12px', color: 'var(--t-muted)', marginTop: '3px' }}>
                        Đối soát & phê duyệt biên bản xử phạt — Nghị Định 168/2024/NĐ-CP
                    </div>
                </div>
                <button
                    onClick={loadViolations}
                    className="btn btn-ghost"
                    style={{ gap: '6px', padding: '7px 14px' }}
                >
                    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <polyline points="23 4 23 10 17 10"/><polyline points="1 20 1 14 7 14"/>
                        <path d="M3.51 9a9 9 0 0114.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0020.49 15"/>
                    </svg>
                    Làm Mới
                </button>
            </div>

            {/* Summary stat row */}
            <div style={{ display: 'flex', gap: '10px' }}>
                <SummaryChip label="Tổng" value={violations.length} color="blue" />
                <SummaryChip label="Chờ Duyệt" value={pendingCount} color="amber" pulse />
                <SummaryChip label="Đã Duyệt" value={confirmedCount} color="green" />
            </div>

            {/* Filter row */}
            <div style={{ display: 'flex', gap: '10px', alignItems: 'center', flexWrap: 'wrap' }}>
                {/* Search */}
                <div style={{ position: 'relative', flex: '1', minWidth: '200px', maxWidth: '280px' }}>
                    <div style={{ position: 'absolute', left: '10px', top: '50%', transform: 'translateY(-50%)', color: 'var(--t-muted)' }}>
                        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
                        </svg>
                    </div>
                    <input
                        className="input-field"
                        style={{ paddingLeft: '32px', height: '36px', fontSize: '12.5px' }}
                        placeholder="Tìm theo ID, biển số, camera..."
                        value={searchTerm}
                        onChange={e => setSearchTerm(e.target.value)}
                    />
                </div>

                <select
                    className="input-field"
                    style={{ height: '36px', fontSize: '12.5px', width: 'auto', minWidth: '150px', cursor: 'pointer' }}
                    value={typeFilter}
                    onChange={e => setTypeFilter(e.target.value)}
                >
                    {VIOLATION_TYPES.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
                </select>

                <select
                    className="input-field"
                    style={{ height: '36px', fontSize: '12.5px', width: 'auto', minWidth: '160px', cursor: 'pointer' }}
                    value={statusFilter}
                    onChange={e => setStatusFilter(e.target.value)}
                >
                    {STATUS_TYPES.map(s => <option key={s.value} value={s.value}>{s.label}</option>)}
                </select>

                <div style={{ flex: 1 }} />

                <div style={{ fontFamily: 'var(--mono)', fontSize: '11px', color: 'var(--t-muted)', background: '#f8fafc', border: '1px solid var(--c-border)', borderRadius: '6px', padding: '5px 10px' }}>
                    {filtered.length} / {violations.length}
                </div>
            </div>

            {/* Table */}
            <div style={{
                background: 'var(--c-surface)',
                border: '1px solid var(--c-border)',
                borderRadius: 'var(--r-xl)',
                overflow: 'hidden',
            }}>
                {loading ? (
                    <div style={{ display: 'flex', justifyContent: 'center', padding: '60px', color: 'var(--t-muted)' }}>
                        <div className="spinner" />
                    </div>
                ) : filtered.length === 0 ? (
                    <div style={{ padding: '60px', textAlign: 'center', color: 'var(--t-muted)', fontSize: '13px' }}>
                        <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" style={{ opacity: 0.3, margin: '0 auto 12px' }}>
                            <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><polyline points="14 2 14 8 20 8"/>
                            <line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/>
                        </svg>
                        <div>Không tìm thấy hồ sơ vi phạm nào</div>
                    </div>
                ) : (
                    <div style={{ overflowX: 'auto' }}>
                        <table className="data-table">
                            <thead>
                                <tr>
                                    <th style={{ width: '44px' }}></th>
                                    <th>#ID</th>
                                    <th>Thời Gian</th>
                                    <th>Loại Vi Phạm</th>
                                    <th>Phương Tiện</th>
                                    <th>Biển Số</th>
                                    <th>Độ Tin Cậy</th>
                                    <th>Camera</th>
                                    <th>Trạng Thái</th>
                                    <th>Hành Động</th>
                                </tr>
                            </thead>
                            <tbody>
                                {filtered.map(v => {
                                    const type = v.type || v.violationType;
                                    const isSelected = selectedIds.has(v.id);
                                    return (
                                        <tr
                                            key={v.id}
                                            style={{
                                                background: isSelected ? 'rgba(37,99,235,0.06)' : undefined,
                                                cursor: 'pointer',
                                            }}
                                        >
                                            <td style={{ padding: '10px 12px' }}>
                                                <input
                                                    type="checkbox"
                                                    checked={isSelected}
                                                    onChange={() => toggleSelect(v.id)}
                                                    onClick={e => e.stopPropagation()}
                                                    style={{ accentColor: 'var(--c-blue)', cursor: 'pointer' }}
                                                />
                                            </td>
                                            <td onClick={() => onOpenModal?.(v)}>
                                                <span style={{ fontFamily: 'var(--mono)', fontSize: '12px', color: 'var(--t-accent)', fontWeight: 600 }}>
                                                    #{v.id}
                                                </span>
                                            </td>
                                            <td onClick={() => onOpenModal?.(v)}>
                                                <span style={{ fontFamily: 'var(--mono)', fontSize: '11px' }}>
                                                    {v.detectedAt ? new Date(v.detectedAt).toLocaleString('vi-VN', { hour12: false }) : '—'}
                                                </span>
                                            </td>
                                            <td onClick={() => onOpenModal?.(v)}>
                                                {type === 'RED_LIGHT_CROSS'
                                                    ? <span className="badge badge-red">Vượt Đèn Đỏ</span>
                                                    : type === 'NO_HELMET'
                                                        ? <span className="badge badge-amber">Không Đội Mũ</span>
                                                        : <span className="badge badge-gray">{type || 'N/A'}</span>
                                                }
                                            </td>
                                            <td onClick={() => onOpenModal?.(v)}>
                                                <span style={{ fontSize: '12px', textTransform: 'capitalize' }}>
                                                    {(v.vehicleType || 'N/A').toLowerCase()}
                                                </span>
                                            </td>
                                            <td onClick={() => onOpenModal?.(v)}>
                                                {v.licensePlate
                                                    ? <span style={{ fontFamily: 'var(--mono)', fontSize: '12px', color: '#0f172a', background: '#f1f5f9', border: '1px solid #cbd5e1', padding: '2px 7px', borderRadius: '4px', fontWeight: 600 }}>{v.licensePlate}</span>
                                                    : <span style={{ color: 'var(--t-muted)', fontSize: '12px' }}>—</span>
                                                }
                                            </td>
                                            <td onClick={() => onOpenModal?.(v)}>
                                                {v.confidence != null ? (() => {
                                                    const confPercent = Math.round(v.confidence <= 1 ? v.confidence * 100 : v.confidence);
                                                    return (
                                                        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                                                            <div style={{ width: '50px', height: '5px', background: '#e2e8f0', borderRadius: '3px', overflow: 'hidden' }}>
                                                                <div style={{ height: '100%', width: `${Math.min(100, confPercent)}%`, background: confPercent >= 70 ? '#16a34a' : '#d97706', borderRadius: '3px' }} />
                                                            </div>
                                                            <span style={{ fontFamily: 'var(--mono)', fontSize: '11px', color: '#475569', fontWeight: 600 }}>
                                                                {confPercent}%
                                                            </span>
                                                        </div>
                                                    );
                                                })() : <span style={{ color: 'var(--t-muted)', fontSize: '12px' }}>—</span>}
                                            </td>
                                            <td onClick={() => onOpenModal?.(v)}>
                                                <span style={{ fontSize: '11.5px', color: 'var(--t-muted)' }}>
                                                    {v.cameraName || 'CAM-HK-01'}
                                                </span>
                                            </td>
                                            <td onClick={() => onOpenModal?.(v)}>
                                                {v.status === 'CONFIRMED'
                                                    ? <span className="badge badge-green">Đã Duyệt</span>
                                                    : v.status === 'DISMISSED'
                                                        ? <span className="badge badge-gray">Bác Bỏ</span>
                                                        : <span className="badge badge-amber">Chờ Duyệt</span>
                                                }
                                            </td>
                                            <td>
                                                <button
                                                    className="btn btn-ghost"
                                                    onClick={() => onOpenModal?.(v)}
                                                    style={{ padding: '4px 12px', fontSize: '11.5px' }}
                                                >
                                                    Xem Hồ Sơ
                                                </button>
                                            </td>
                                        </tr>
                                    );
                                })}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>
        </div>
    );
}

function SummaryChip({ label, value, color, pulse }) {
    const colors = {
        blue:  { bg: '#eff6ff', border: '#bfdbfe', dot: '#1d4ed8', text: '#1e40af' },
        amber: { bg: '#fffbeb', border: '#fde68a', dot: '#d97706', text: '#92400e' },
        green: { bg: '#f0fdf4', border: '#bbf7d0', dot: '#16a34a', text: '#166534' },
    };
    const c = colors[color] || colors.blue;
    return (
        <div style={{
            display: 'flex', alignItems: 'center', gap: '8px',
            backgroundColor: c.bg,
            border: `1px solid ${c.border}`,
            borderRadius: '6px',
            padding: '6px 14px',
        }}>
            <div style={{
                width: 7, height: 7, borderRadius: '50%', backgroundColor: c.dot, flexShrink: 0,
            }} />
            <span style={{ fontSize: '11.5px', color: '#475569', fontWeight: 600 }}>{label}:</span>
            <span style={{ fontFamily: 'var(--mono)', fontSize: '15px', fontWeight: 800, color: c.text }}>{value}</span>
        </div>
    );
}
