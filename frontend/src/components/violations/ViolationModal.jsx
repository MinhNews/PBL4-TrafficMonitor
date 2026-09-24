import React, { useState } from 'react';

export default function ViolationModal({ violation, onClose, onConfirm, onDismiss }) {
    const [notes, setNotes] = useState('');

    if (!violation) return null;

    // Xác định mức phạt NĐ 168/2024 (ưu tiên từ Backend DTO, fallback theo loại xe)
    const isCar = (violation.vehicleType || '').toUpperCase() === 'CAR';
    const isNoHelmet = violation.violationType === 'NO_HELMET' || violation.type === 'NO_HELMET';

    let fineText = '4.000.000 - 6.000.000 VNĐ';
    let penaltyPoints = 4;
    let legalBasis = 'Căn cứ: Điểm a Khoản 9 Điều 6 Nghị định 168/2024/NĐ-CP';

    if (violation.fineAmount) {
        fineText = `${violation.fineAmount.toLocaleString('vi-VN')} VNĐ`;
    } else if (isNoHelmet) {
        fineText = '800.000 - 1.000.000 VNĐ';
        penaltyPoints = 0;
        legalBasis = 'Căn cứ: Khoản 3 Điều 7 Nghị định 168/2024/NĐ-CP';
    } else if (isCar) {
        fineText = '18.000.000 - 20.000.000 VNĐ';
        penaltyPoints = 4;
        legalBasis = 'Căn cứ: Điểm a Khoản 9 Điều 6 Nghị định 168/2024/NĐ-CP';
    }

    if (violation.penaltyPoints !== undefined && violation.penaltyPoints !== null) {
        penaltyPoints = violation.penaltyPoints;
    }
    if (violation.legalBasis) {
        legalBasis = violation.legalBasis;
    }

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

                {/* Ảnh bằng chứng từ Backend (Cloudinary / File upload) */}
                <div style={{ borderRadius: '12px', overflow: 'hidden', marginBottom: '16px', background: '#0f172a', textAlign: 'center' }}>
                    <img
                        src={violation.imageUrl || 'https://via.placeholder.com/600x320?text=Chua+co+anh+bang+chung'}
                        alt="Bằng chứng vi phạm"
                        style={{ maxWidth: '100%', maxHeight: '330px', objectFit: 'contain' }}
                    />
                </div>

                {/* ⚖️ Thẻ Căn Cứ Xử Phạt Chuẩn Nghị Định 168/2024 (Quest 3 - Task 3.4) */}
                <div style={{
                    backgroundColor: '#fff1f2', border: '1.5px solid #fecdd3', borderRadius: '12px',
                    padding: '16px', marginBottom: '18px', display: 'flex', justifyContent: 'space-between', alignItems: 'center'
                }}>
                    <div>
                        <div style={{ fontSize: '11px', fontWeight: '800', color: '#be123c', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                            ⚖️ KHUNG HÌNH PHẠT ĐỀ XUẤT (NGHỊ ĐỊNH 168/2024/NĐ-CP)
                        </div>
                        <div style={{ fontSize: '20px', fontWeight: '900', color: '#9f1239', margin: '4px 0 2px 0' }}>
                            {fineText}
                        </div>
                        <div style={{ fontSize: '12px', color: '#881337' }}>
                            {legalBasis}
                        </div>
                    </div>
                    {penaltyPoints > 0 && (
                        <div style={{ textAlign: 'center', background: '#e11d48', color: '#fff', padding: '8px 16px', borderRadius: '10px' }}>
                            <div style={{ fontSize: '18px', fontWeight: '900' }}>-{penaltyPoints < 10 ? `0${penaltyPoints}` : penaltyPoints} ĐIỂM</div>
                            <div style={{ fontSize: '10px', textTransform: 'uppercase', opacity: 0.9 }}>Trừ điểm GPLX</div>
                        </div>
                    )}
                </div>

                {/* Thông tin chi tiết vi phạm */}
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', fontSize: '13.5px', marginBottom: '16px' }}>
                    <div><strong>Lỗi vi phạm:</strong> {violation.typeDisplay || violation.violationType || violation.type}</div>
                    <div><strong>Phương tiện:</strong> {violation.vehicleType || 'N/A'}</div>
                    <div><strong>Camera ghi hình:</strong> {violation.cameraName || 'Camera 01 - Hòa Khánh'}</div>
                    <div><strong>Độ tin cậy AI:</strong> {violation.confidence ? `${Math.round(violation.confidence * (violation.confidence <= 1 ? 100 : 1))}%` : 'N/A'}</div>
                    <div><strong>Thời gian ghi nhận:</strong> {violation.detectedAt?.replace('T', ' ')?.substring(0, 19)}</div>
                    <div><strong>Trạng thái duyệt:</strong> {violation.status || 'PENDING'}</div>
                </div>

                {/* Ý kiến xử lý của CSGT */}
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

                {/* Nút hành động */}
                <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px' }}>
                    <button
                        onClick={() => onDismiss && onDismiss(violation.id, notes)}
                        style={{ padding: '10px 20px', borderRadius: '10px', border: 'none', backgroundColor: '#ef4444', color: '#fff', fontWeight: '700', cursor: 'pointer' }}
                    >
                        ❌ Bác bỏ (Báo giả)
                    </button>
                    <button
                        onClick={() => onConfirm && onConfirm(violation.id, notes)}
                        style={{ padding: '10px 20px', borderRadius: '10px', border: 'none', backgroundColor: '#16a34a', color: '#fff', fontWeight: '700', cursor: 'pointer' }}
                    >
                        ✅ Xác nhận xử phạt
                    </button>
                </div>
            </div>
        </div>
    );
}