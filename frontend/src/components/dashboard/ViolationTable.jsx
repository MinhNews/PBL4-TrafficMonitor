import React from 'react';

export default function ViolationTable({ violations, onSelectViolation }) {
    return (
        <div style={{
            backgroundColor: '#ffffff',
            borderRadius: '16px',
            padding: '20px',
            boxShadow: '0 4px 20px rgba(0, 0, 0, 0.05)'
        }}>
            <h3 style={{ fontSize: '18px', fontWeight: '700', marginBottom: '16px', color: '#1e293b' }}>
                🚨 Danh Sách Vi Phạm Gần Đây
            </h3>
            <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
                    <thead>
                        <tr style={{ borderBottom: '2px solid #f1f5f9', color: '#64748b', fontSize: '13px' }}>
                            <th style={{ padding: '12px' }}>ID</th>
                            <th style={{ padding: '12px' }}>Thời Gian</th>
                            <th style={{ padding: '12px' }}>Loại Lỗi</th>
                            <th style={{ padding: '12px' }}>Phương Tiện</th>
                            <th style={{ padding: '12px' }}>Độ Tin Cậy</th>
                            <th style={{ padding: '12px' }}>Trạng Thái</th>
                            <th style={{ padding: '12px' }}>Hành Động</th>
                        </tr>
                    </thead>
                    <tbody>
                        {violations && violations.length > 0 ? (
                            violations.map((v) => (
                                <tr key={v.id} style={{ borderBottom: '1px solid #f1f5f9', fontSize: '13.5px' }}>
                                    <td style={{ padding: '12px', fontWeight: '700' }}>#{v.id}</td>
                                    <td style={{ padding: '12px', color: '#64748b' }}>
                                        {v.detectedAt ? v.detectedAt.replace('T', ' ') : 'N/A'}
                                    </td>
                                    <td style={{ padding: '12px' }}>
                                        <span style={{
                                            padding: '4px 10px', borderRadius: '20px', fontSize: '12px', fontWeight: '700',
                                            backgroundColor: v.type === 'NO_HELMET' ? '#fef3c7' : '#fee2e2',
                                            color: v.type === 'NO_HELMET' ? '#d97706' : '#dc2626'
                                        }}>
                                            {v.typeDisplay}
                                        </span>
                                    </td>
                                    <td style={{ padding: '12px' }}>{v.vehicleType}</td>
                                    <td style={{ padding: '12px', fontWeight: '700', color: '#059669' }}>
                                        {v.confidence}%
                                    </td>
                                    <td style={{ padding: '12px' }}>
                                        <span style={{
                                            padding: '4px 10px', borderRadius: '20px', fontSize: '12px', fontWeight: '700',
                                            backgroundColor: v.status === 'CONFIRMED' ? '#dcfce7' : v.status === 'DISMISSED' ? '#f1f5f9' : '#e0f2fe',
                                            color: v.status === 'CONFIRMED' ? '#16a34a' : v.status === 'DISMISSED' ? '#64748b' : '#0284c7'
                                        }}>
                                            {v.status}
                                        </span>
                                    </td>
                                    <td style={{ padding: '12px' }}>
                                        <button
                                            onClick={() => onSelectViolation(v)}
                                            style={{
                                                padding: '6px 14px', borderRadius: '8px', border: 'none',
                                                backgroundColor: '#3b82f6', color: '#ffffff', cursor: 'pointer',
                                                fontWeight: '700', fontSize: '12px'
                                            }}
                                        >
                                            Chi tiết
                                        </button>
                                    </td>
                                </tr>
                            ))
                        ) : (
                            <tr>
                                <td colSpan="7" style={{ textAlign: 'center', padding: '24px', color: '#94a3b8' }}>
                                    Chưa có vi phạm nào được ghi nhận hôm nay.
                                </td>
                            </tr>
                        )}
                    </tbody>
                </table>
            </div>
        </div>
    );
}