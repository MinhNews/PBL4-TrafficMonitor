import React, { useState } from 'react';

export default function ViolationModal({ violation, onClose, onConfirm, onDismiss }) {
    const [notes, setNotes] = useState('');

    if (!violation) return null;

    return (
        <div style={{
            position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
            backgroundColor: 'rgba(0, 0, 0, 0.65)', display: 'flex',
            alignItems: 'center', justifyContent: 'center', zIndex: 1000
        }}>
            <div style={{
                backgroundColor: '#ffffff', borderRadius: '20px', width: '680px',
                maxWidth: '90%', maxHeight: '90vh', overflowY: 'auto', padding: '24px',
                boxShadow: '0 20px 50px rgba(0,0,0,0.3)'
            }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '16px' }}>
                    <h3 style={{ margin: 0, fontSize: '20px', color: '#1e293b' }}>
                        Hồ Sơ Vi Phạm #{violation.id}
                    </h3>
                    <button onClick={onClose} style={{ background: 'none', border: 'none', fontSize: '20px', cursor: 'pointer' }}>✖</button>
                </div>

                {/* Ảnh bằng chứng từ Backend ImageController */}
                <div style={{ borderRadius: '12px', overflow: 'hidden', marginBottom: '16px', background: '#0f172a', textAlign: 'center' }}>
                    <img
                        src={violation.imageUrl || 'https://via.placeholder.com/600x320?text=Chua+co+anh+bang+chung'}
                        alt="Bằng chứng vi phạm"
                        style={{ maxWidth: '100%', maxHeight: '350px', objectFit: 'contain' }}
                    />
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', fontSize: '13.5px', marginBottom: '16px' }}>
                    <div><strong>Lỗi vi phạm:</strong> {violation.typeDisplay}</div>
                    <div><strong>Phương tiện:</strong> {violation.vehicleType}</div>
                    <div><strong>Camera ghi hình:</strong> {violation.cameraName}</div>
                    <div><strong>Độ tin cậy AI:</strong> {violation.confidence}%</div>
                    <div><strong>Thời gian ghi nhận:</strong> {violation.detectedAt?.replace('T', ' ')}</div>
                    <div><strong>Trạng thái duyệt:</strong> {violation.status}</div>
                </div>

                <div style={{ marginBottom: '20px' }}>
                    <label style={{ display: 'block', fontSize: '13px', fontWeight: '700', marginBottom: '6px', color: '#475569' }}>
                        Ý kiến xử lý của CSGT trực ban:
                    </label>
                    <textarea
                        rows="2"
                        value={notes}
                        onChange={(e) => setNotes(e.target.value)}
                        placeholder="Nhập ghi chú xử phạt hoặc lý do bác bỏ..."
                        style={{ width: '100%', padding: '10px 12px', borderRadius: '8px', border: '1px solid #cbd5e1', boxSizing: 'border-box', fontFamily: 'inherit' }}
                    />
                </div>

                <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px' }}>
                    <button onClick={() => onDismiss(violation.id, notes)} style={{ padding: '10px 20px', borderRadius: '10px', border: 'none', backgroundColor: '#ef4444', color: '#fff', fontWeight: '700', cursor: 'pointer' }}>
                        ❌ Bác bỏ (Báo giả)
                    </button>
                    <button onClick={() => onConfirm(violation.id, notes)} style={{ padding: '10px 20px', borderRadius: '10px', border: 'none', backgroundColor: '#16a34a', color: '#fff', fontWeight: '700', cursor: 'pointer' }}>
                        ✅ Xác nhận xử phạt
                    </button>
                </div>
            </div>
        </div>
    );
}