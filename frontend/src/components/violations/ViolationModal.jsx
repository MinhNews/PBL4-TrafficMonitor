import React, { useState, useRef, useEffect } from 'react';
import { violationAPI } from '../../services/api';

export default function ViolationModal({ violation, onClose, onConfirm, onDismiss }) {
    const [notes, setNotes] = useState('');
    const [isLightboxOpen, setIsLightboxOpen] = useState(false);
    const [downloading, setDownloading] = useState(false);
    const [submitting, setSubmitting] = useState(false);
    const [toast, setToast] = useState(null); // { message, type }
    const [zoomScale, setZoomScale] = useState(1);
    const [rotation, setRotation] = useState(0);
    const [panOffset, setPanOffset] = useState({ x: 0, y: 0 });
    const [isDragging, setIsDragging] = useState(false);
    const dragStartRef = useRef({ x: 0, y: 0 });

    if (!violation) return null;

    // Xác định mức phạt NĐ 168/2024 (ưu tiên từ Backend DTO, fallback theo loại xe)
    const isCar = (violation.vehicleType || '').toUpperCase() === 'CAR';
    const isNoHelmet = violation.violationType === 'NO_HELMET' || violation.type === 'NO_HELMET';

    let fineText = '4.000.000 - 6.000.000 VNĐ';
    let penaltyPoints = 4;
    let legalBasis = 'Căn cứ: Điểm a Khoản 9 Điều 6 Nghị định 168/2024/NĐ-CP';

    if (violation.fineAmount) {
        fineText = String(violation.fineAmount).includes('VNĐ')
            ? String(violation.fineAmount)
            : `${Number(violation.fineAmount).toLocaleString('vi-VN')} VNĐ`;
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

    const imageUrl = violation.imageUrl || 'https://via.placeholder.com/600x320?text=Chua+co+anh+bang+chung';

    // Lightbox handlers
    function openLightbox() {
        setZoomScale(1);
        setRotation(0);
        setPanOffset({ x: 0, y: 0 });
        setIsLightboxOpen(true);
    }

    function closeLightbox() {
        setIsLightboxOpen(false);
        setZoomScale(1);
        setRotation(0);
        setPanOffset({ x: 0, y: 0 });
    }

    function handleZoomIn() {
        setZoomScale(s => Math.min(4, +(s + 0.3).toFixed(1)));
    }

    function handleZoomOut() {
        setZoomScale(s => Math.max(0.5, +(s - 0.3).toFixed(1)));
    }

    function handleResetZoom() {
        setZoomScale(1);
        setRotation(0);
        setPanOffset({ x: 0, y: 0 });
    }

    function handleRotate() {
        setRotation(r => (r + 90) % 360);
    }

    async function downloadEvidenceImage(e) {
        if (e) {
            e.preventDefault();
            e.stopPropagation();
        }
        setDownloading(true);
        const cleanId = violation.id || Date.now();
        const fileName = `Bien_ban_vi_pham_${cleanId}.jpg`;

        try {
            // Cách 1: Fetch trực tiếp dữ liệu nhị phân (Blob) -> Tải về ngay lập tức với tên file tùy chỉnh
            const response = await fetch(imageUrl, { mode: 'cors' });
            if (!response.ok) throw new Error('Fetch image blob failed');
            const blob = await response.blob();
            const blobUrl = window.URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.style.display = 'none';
            link.href = blobUrl;
            link.download = fileName;
            document.body.appendChild(link);
            link.click();
            window.URL.revokeObjectURL(blobUrl);
            document.body.removeChild(link);
        } catch (err) {
            console.warn('Direct blob download failed, using Cloudinary attachment header fallback:', err);
            // Cách 2: Tận dụng cờ fl_attachment của Cloudinary CDN
            // Cloudinary sẽ tự động gửi Header: Content-Disposition: attachment, bắt trình duyệt phải TẢI XUỐNG thay vì mở trang
            let downloadUrl = imageUrl;
            if (imageUrl.includes('res.cloudinary.com') && imageUrl.includes('/upload/')) {
                downloadUrl = imageUrl.replace('/upload/', `/upload/fl_attachment:Bien_ban_vi_pham_${cleanId}/`);
            }
            const link = document.createElement('a');
            link.style.display = 'none';
            link.href = downloadUrl;
            link.download = fileName;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
        } finally {
            setTimeout(() => setDownloading(false), 800);
        }
    }

    async function handleConfirm() {
        if (submitting) return;
        setSubmitting(true);
        setToast(null);
        try {
            await violationAPI.confirm(violation.id, notes);
            setToast({ message: 'Xác nhận xử phạt vi phạm thành công!', type: 'success' });
            window.dispatchEvent(new CustomEvent('violation:updated', { 
                detail: { id: violation.id, status: 'CONFIRMED', notes } 
            }));
            onConfirm?.(violation.id, notes);
            setTimeout(() => {
                onClose();
            }, 600);
        } catch (err) {
            console.error('Lỗi khi xác nhận vi phạm:', err);
            setToast({ message: 'Không thể kết nối đến máy chủ để xác nhận. Vui lòng thử lại!', type: 'error' });
            setSubmitting(false);
        }
    }

    async function handleDismiss() {
        if (submitting) return;
        setSubmitting(true);
        setToast(null);
        try {
            await violationAPI.dismiss(violation.id, notes);
            setToast({ message: 'Đã bác bỏ hồ sơ vi phạm (Báo giả)!', type: 'warning' });
            window.dispatchEvent(new CustomEvent('violation:updated', { 
                detail: { id: violation.id, status: 'DISMISSED', notes } 
            }));
            onDismiss?.(violation.id, notes);
            setTimeout(() => {
                onClose();
            }, 600);
        } catch (err) {
            console.error('Lỗi khi bác bỏ vi phạm:', err);
            setToast({ message: 'Không thể kết nối đến máy chủ để bác bỏ. Vui lòng thử lại!', type: 'error' });
            setSubmitting(false);
        }
    }

    function handleWheel(e) {
        if (!isLightboxOpen) return;
        e.preventDefault();
        if (e.deltaY < 0) {
            handleZoomIn();
        } else {
            handleZoomOut();
        }
    }

    function handleMouseDown(e) {
        if (zoomScale <= 1) return;
        setIsDragging(true);
        dragStartRef.current = {
            x: e.clientX - panOffset.x,
            y: e.clientY - panOffset.y,
        };
    }

    function handleMouseMove(e) {
        if (!isDragging) return;
        setPanOffset({
            x: e.clientX - dragStartRef.current.x,
            y: e.clientY - dragStartRef.current.y,
        });
    }

    function handleMouseUp() {
        setIsDragging(false);
    }

    // Keyboard shortcuts for Lightbox (ESC to close, + / - to zoom)
    useEffect(() => {
        function handleKeyDown(e) {
            if (e.key === 'Escape') {
                if (isLightboxOpen) {
                    closeLightbox();
                } else {
                    onClose();
                }
            }
            if (isLightboxOpen) {
                if (e.key === '+' || e.key === '=') handleZoomIn();
                if (e.key === '-') handleZoomOut();
                if (e.key === '0') handleResetZoom();
            }
        }
        window.addEventListener('keydown', handleKeyDown);
        return () => window.removeEventListener('keydown', handleKeyDown);
    }, [isLightboxOpen, onClose]);

    return (
        <>
            {/* MAIN VIOLATION DOSSIER MODAL */}
            <div 
                onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
                style={{
                    position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
                    backgroundColor: 'rgba(15, 23, 42, 0.72)', display: 'flex',
                    alignItems: 'center', justifyContent: 'center', zIndex: 1000,
                    backdropFilter: 'blur(4px)', padding: '20px'
                }}
            >
                <div style={{
                    backgroundColor: '#ffffff', borderRadius: '16px', width: '740px',
                    maxWidth: '96%', maxHeight: '92vh', overflowY: 'auto', padding: '0 24px 24px 24px',
                    boxShadow: '0 20px 50px rgba(0,0,0,0.25)', position: 'relative',
                    border: '1px solid var(--c-border)'
                }}>
                    {/* Header Sticky */}
                    <div style={{
                        position: 'sticky', top: 0, backgroundColor: '#ffffff', zIndex: 10,
                        paddingTop: '20px', paddingBottom: '14px', marginBottom: '14px',
                        borderBottom: '1px solid #f1f5f9', display: 'flex', justifyContent: 'space-between', alignItems: 'center'
                    }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                            <div style={{
                                width: '32px', height: '32px', borderRadius: '6px',
                                backgroundColor: '#1d4ed8', color: '#ffffff',
                                display: 'flex', alignItems: 'center', justifyContent: 'center'
                            }}>
                                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                    <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/>
                                    <polyline points="14 2 14 8 20 8"/>
                                </svg>
                            </div>
                            <div>
                                <h3 style={{ margin: 0, fontSize: '17px', fontWeight: '800', color: '#0f172a' }}>
                                    Hồ Sơ Vi Phạm Giao Thông #{violation.id}
                                </h3>
                                <div style={{ fontSize: '11px', color: '#64748b' }}>
                                    Trích xuất tự động từ Camera Giám sát AI
                                </div>
                            </div>
                        </div>

                        <button 
                            onClick={onClose}
                            title="Đóng cửa sổ (ESC)"
                            style={{
                                display: 'flex', alignItems: 'center', justifyContent: 'center',
                                width: '32px', height: '32px', borderRadius: '6px',
                                border: '1px solid #cbd5e1', backgroundColor: '#f8fafc',
                                color: '#475569', fontSize: '15px', fontWeight: '700',
                                cursor: 'pointer', transition: 'all 0.15s ease', outline: 'none'
                            }}
                            onMouseEnter={(e) => { e.currentTarget.style.backgroundColor = '#fee2e2'; e.currentTarget.style.color = '#dc2626'; }}
                            onMouseLeave={(e) => { e.currentTarget.style.backgroundColor = '#f8fafc'; e.currentTarget.style.color = '#475569'; }}
                        >
                            ✕
                        </button>
                    </div>

                    {/* KHUNG ẢNH BẰNG CHỨNG: CĂN GIỮA 100%, TO RÕ RÀNG & CÓ THỂ BẤM ĐỂ PHÓNG TO */}
                    <div 
                        onClick={openLightbox}
                        title="Bấm vào để xem ảnh toàn màn hình và phóng to/thu nhỏ soi biển số"
                        style={{
                            borderRadius: '10px',
                            overflow: 'hidden',
                            marginBottom: '16px',
                            backgroundColor: '#090d16',
                            border: '1px solid #334155',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            position: 'relative',
                            cursor: 'zoom-in',
                            minHeight: '360px',
                            maxHeight: '460px',
                        }}
                    >
                        <img
                            src={imageUrl}
                            alt="Ảnh bằng chứng vi phạm giao thông"
                            style={{
                                maxWidth: '100%',
                                maxHeight: '460px',
                                height: 'auto',
                                width: 'auto',
                                objectFit: 'contain',
                                display: 'block',
                                margin: '0 auto',
                                transition: 'transform 0.2s ease',
                            }}
                        />

                        {/* Top-Right Badges: Phóng to & Tải ảnh */}
                        <div style={{
                            position: 'absolute',
                            top: '12px',
                            right: '12px',
                            display: 'flex',
                            gap: '8px',
                            zIndex: 2,
                        }}>
                            <button
                                onClick={downloadEvidenceImage}
                                disabled={downloading}
                                title="Tải file ảnh bằng chứng này về máy"
                                style={{
                                    backgroundColor: 'rgba(15, 23, 42, 0.85)',
                                    color: '#ffffff',
                                    padding: '6px 12px',
                                    borderRadius: '6px',
                                    fontSize: '11.5px',
                                    fontWeight: 600,
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: '6px',
                                    border: '1px solid rgba(255, 255, 255, 0.2)',
                                    backdropFilter: 'blur(4px)',
                                    cursor: downloading ? 'wait' : 'pointer',
                                    boxShadow: '0 2px 6px rgba(0,0,0,0.3)'
                                }}
                            >
                                {downloading ? '⏳ Đang Tải...' : '📥 Tải Ảnh'}
                            </button>

                            <div style={{
                                backgroundColor: 'rgba(15, 23, 42, 0.85)',
                                color: '#ffffff',
                                padding: '6px 12px',
                                borderRadius: '6px',
                                fontSize: '11.5px',
                                fontWeight: 600,
                                display: 'flex',
                                alignItems: 'center',
                                gap: '6px',
                                border: '1px solid rgba(255, 255, 255, 0.2)',
                                backdropFilter: 'blur(4px)',
                                boxShadow: '0 2px 6px rgba(0,0,0,0.3)'
                            }}>
                                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2">
                                    <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
                                    <line x1="11" y1="8" x2="11" y2="14"/><line x1="8" y1="11" x2="14" y2="11"/>
                                </svg>
                                Phóng To
                            </div>
                        </div>

                        {/* Bottom-Left Badge: ID & Camera info */}
                        <div style={{
                            position: 'absolute',
                            bottom: '12px',
                            left: '12px',
                            backgroundColor: 'rgba(15, 23, 42, 0.85)',
                            color: '#e2e8f0',
                            padding: '4px 10px',
                            borderRadius: '4px',
                            fontSize: '11px',
                            fontFamily: 'var(--mono)',
                            border: '1px solid rgba(255, 255, 255, 0.15)'
                        }}>
                            BẰNG CHỨNG #{violation.id} · {violation.cameraName || 'CAM-HK-01'}
                        </div>
                    </div>

                    {/* ⚖️ Khung Hình Phạt Đề Xuất (Nghị Định 168/2024/NĐ-CP) */}
                    <div style={{
                        backgroundColor: '#fff1f2', border: '1.5px solid #fecdd3', borderRadius: '10px',
                        padding: '14px 18px', marginBottom: '16px', display: 'flex', justifyContent: 'space-between', alignItems: 'center'
                    }}>
                        <div>
                            <div style={{ fontSize: '11px', fontWeight: '800', color: '#be123c', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                                ⚖️ KHUNG HÌNH PHẠT ĐỀ XUẤT (NGHỊ ĐỊNH 168/2024/NĐ-CP)
                            </div>
                            <div style={{ fontSize: '20px', fontWeight: '900', color: '#9f1239', margin: '4px 0 2px 0' }}>
                                {fineText}
                            </div>
                            <div style={{ fontSize: '11.5px', color: '#881337' }}>
                                {legalBasis}
                            </div>
                        </div>
                        {penaltyPoints > 0 && (
                            <div style={{ textAlign: 'center', background: '#dc2626', color: '#fff', padding: '6px 14px', borderRadius: '8px' }}>
                                <div style={{ fontSize: '18px', fontWeight: '900' }}>-{penaltyPoints < 10 ? `0${penaltyPoints}` : penaltyPoints} ĐIỂM</div>
                                <div style={{ fontSize: '10px', textTransform: 'uppercase', opacity: 0.9 }}>Trừ điểm GPLX</div>
                            </div>
                        )}
                    </div>

                    {/* Thông Tin Chi Tiết Vi Phạm */}
                    <div style={{
                        backgroundColor: '#f8fafc',
                        border: '1px solid var(--c-border)',
                        borderRadius: '10px',
                        padding: '14px 16px',
                        display: 'grid',
                        gridTemplateColumns: '1fr 1fr',
                        gap: '10px',
                        fontSize: '12.5px',
                        marginBottom: '16px'
                    }}>
                        <div><strong style={{ color: '#475569' }}>Lỗi vi phạm:</strong> <span style={{ fontWeight: 700, color: '#dc2626' }}>{violation.typeDisplay || violation.violationType || violation.type}</span></div>
                        <div><strong style={{ color: '#475569' }}>Phương tiện:</strong> <span style={{ fontWeight: 600 }}>{violation.vehicleType || 'N/A'}</span></div>
                        <div><strong style={{ color: '#475569' }}>Camera ghi hình:</strong> <span>{violation.cameraName || 'Camera 01 - Hòa Khánh'}</span></div>
                        <div><strong style={{ color: '#475569' }}>Độ tin cậy AI:</strong> <span style={{ fontWeight: 700, color: '#16a34a' }}>{violation.confidence ? `${Math.round(violation.confidence * (violation.confidence <= 1 ? 100 : 1))}%` : 'N/A'}</span></div>
                        <div><strong style={{ color: '#475569' }}>Thời gian ghi nhận:</strong> <span>{violation.detectedAt?.replace('T', ' ')?.substring(0, 19)}</span></div>
                        <div><strong style={{ color: '#475569' }}>Trạng thái duyệt:</strong> <span style={{ fontWeight: 700, color: '#1d4ed8' }}>{violation.status || 'PENDING'}</span></div>
                    </div>

                    {/* Ý kiến xử lý của CSGT */}
                    <div style={{ marginBottom: '18px' }}>
                        <label style={{ display: 'block', fontSize: '12.5px', fontWeight: '700', marginBottom: '6px', color: '#334155' }}>
                            Ý kiến xử lý của CSGT trực ban:
                        </label>
                        <textarea
                            rows="2"
                            value={notes}
                            onChange={(e) => setNotes(e.target.value)}
                            placeholder="Nhập ghi chú xử phạt hoặc lý do bác bỏ..."
                            style={{
                                width: '100%', padding: '10px 12px', borderRadius: '6px',
                                border: '1px solid #cbd5e1', boxSizing: 'border-box',
                                fontFamily: 'inherit', fontSize: '13px', outline: 'none'
                            }}
                        />
                    </div>

                    {/* Toast Notification Banner */}
                    {toast && (
                        <div style={{
                            padding: '10px 14px',
                            borderRadius: '6px',
                            marginBottom: '14px',
                            fontSize: '12.5px',
                            fontWeight: 600,
                            display: 'flex',
                            alignItems: 'center',
                            gap: '8px',
                            backgroundColor: toast.type === 'success' ? '#f0fdf4' : toast.type === 'warning' ? '#fffbeb' : '#fef2f2',
                            color: toast.type === 'success' ? '#15803d' : toast.type === 'warning' ? '#92400e' : '#b91c1c',
                            border: toast.type === 'success' ? '1px solid #bbf7d0' : toast.type === 'warning' ? '1px solid #fde68a' : '1px solid #fecaca',
                        }}>
                            <span>{toast.type === 'success' ? '✓' : toast.type === 'warning' ? '⚠' : '✕'}</span>
                            <span>{toast.message}</span>
                        </div>
                    )}

                    {/* Nút hành động */}
                    <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
                        <button
                            onClick={onClose}
                            disabled={submitting}
                            style={{
                                padding: '9px 16px', borderRadius: '6px', border: '1px solid #cbd5e1',
                                backgroundColor: '#f8fafc', color: '#475569', fontWeight: '600', fontSize: '13px', cursor: submitting ? 'not-allowed' : 'pointer',
                                transition: 'all 0.15s ease'
                            }}
                        >
                            Đóng
                        </button>
                        <button
                            onClick={handleDismiss}
                            disabled={submitting}
                            style={{
                                padding: '9px 18px', borderRadius: '6px', border: 'none',
                                backgroundColor: '#dc2626', color: '#fff', fontWeight: '700', fontSize: '13px',
                                cursor: submitting ? 'wait' : 'pointer', opacity: submitting ? 0.7 : 1,
                                display: 'flex', alignItems: 'center', gap: '6px'
                            }}
                        >
                            {submitting ? '⏳ Đang xử lý...' : '✕ Bác Bỏ (Báo Giả)'}
                        </button>
                        <button
                            onClick={handleConfirm}
                            disabled={submitting}
                            style={{
                                padding: '9px 20px', borderRadius: '6px', border: 'none',
                                backgroundColor: '#16a34a', color: '#fff', fontWeight: '700', fontSize: '13px',
                                cursor: submitting ? 'wait' : 'pointer', opacity: submitting ? 0.7 : 1,
                                display: 'flex', alignItems: 'center', gap: '6px'
                            }}
                        >
                            {submitting ? '⏳ Đang xử lý...' : '✓ Xác Nhận Xử Phạt'}
                        </button>
                    </div>
                </div>
            </div>

            {/* LIGHTBOX INTERACTIVE FULLSCREEN VIEWER (ZOOM / PAN / ROTATE) */}
            {isLightboxOpen && (
                <div 
                    onWheel={handleWheel}
                    style={{
                        position: 'fixed',
                        inset: 0,
                        backgroundColor: 'rgba(5, 8, 15, 0.95)',
                        zIndex: 2000,
                        display: 'flex',
                        flexDirection: 'column',
                        backdropFilter: 'blur(8px)',
                        userSelect: 'none',
                    }}
                >
                    {/* Lightbox Toolbar Header */}
                    <div style={{
                        padding: '12px 24px',
                        backgroundColor: 'rgba(15, 23, 42, 0.9)',
                        borderBottom: '1px solid #1e293b',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        flexWrap: 'wrap',
                        gap: '12px',
                        zIndex: 10,
                    }}>
                        {/* Left: Info */}
                        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                            <span style={{
                                backgroundColor: '#1d4ed8', color: '#ffffff',
                                padding: '3px 8px', borderRadius: '4px', fontSize: '11px', fontWeight: 800
                            }}>
                                BIÊN BẢN #{violation.id}
                            </span>
                            <span style={{ color: '#f8fafc', fontSize: '13.5px', fontWeight: 700 }}>
                                Ảnh Bằng Chứng Vi Phạm (Độ Phóng Đại: {Math.round(zoomScale * 100)}%)
                            </span>
                            <span style={{ color: '#94a3b8', fontSize: '12px' }}>
                                Cuộn chuột hoặc bấm nút để phóng to / thu nhỏ
                            </span>
                        </div>

                        {/* Right: Controls (Zoom In, Zoom Out, Reset, Rotate, Download, Close) */}
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                            {/* Zoom In Button */}
                            <button
                                onClick={handleZoomIn}
                                title="Phóng to ảnh (+)"
                                style={{
                                    backgroundColor: '#1e293b', color: '#ffffff', border: '1px solid #334155',
                                    padding: '6px 12px', borderRadius: '6px', fontSize: '12px', fontWeight: 700,
                                    cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '5px'
                                }}
                            >
                                ➕ Phóng To
                            </button>

                            {/* Zoom Out Button */}
                            <button
                                onClick={handleZoomOut}
                                title="Thu nhỏ ảnh (-)"
                                style={{
                                    backgroundColor: '#1e293b', color: '#ffffff', border: '1px solid #334155',
                                    padding: '6px 12px', borderRadius: '6px', fontSize: '12px', fontWeight: 700,
                                    cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '5px'
                                }}
                            >
                                ➖ Thu Nhỏ
                            </button>

                            {/* Reset Zoom */}
                            <button
                                onClick={handleResetZoom}
                                title="Khôi phục kích thước 100% (Phím 0)"
                                style={{
                                    backgroundColor: '#1e293b', color: '#cbd5e1', border: '1px solid #334155',
                                    padding: '6px 12px', borderRadius: '6px', fontSize: '12px', fontWeight: 600,
                                    cursor: 'pointer'
                                }}
                            >
                                ↺ Mặc Định
                            </button>

                            {/* Rotate Button */}
                            <button
                                onClick={handleRotate}
                                title="Xoay ảnh 90 độ"
                                style={{
                                    backgroundColor: '#1e293b', color: '#cbd5e1', border: '1px solid #334155',
                                    padding: '6px 12px', borderRadius: '6px', fontSize: '12px', fontWeight: 600,
                                    cursor: 'pointer'
                                }}
                            >
                                ↻ Xoay
                            </button>

                            {/* Real Download Button (Direct file save) */}
                            <button
                                onClick={downloadEvidenceImage}
                                disabled={downloading}
                                title="Tải file ảnh bằng chứng về máy tính"
                                style={{
                                    backgroundColor: '#1e293b', color: '#cbd5e1', border: '1px solid #334155',
                                    padding: '6px 12px', borderRadius: '6px', fontSize: '12px', fontWeight: 600,
                                    cursor: downloading ? 'wait' : 'pointer', display: 'flex', alignItems: 'center', gap: '5px'
                                }}
                            >
                                {downloading ? '⏳ Đang Tải...' : '📥 Tải Về'}
                            </button>

                            {/* Close Button */}
                            <button
                                onClick={closeLightbox}
                                title="Đóng cửa sổ toàn màn hình (ESC)"
                                style={{
                                    backgroundColor: '#dc2626', color: '#ffffff', border: 'none',
                                    padding: '6px 14px', borderRadius: '6px', fontSize: '12px', fontWeight: 800,
                                    cursor: 'pointer', marginLeft: '6px'
                                }}
                            >
                                ✕ Đóng
                            </button>
                        </div>
                    </div>

                    {/* Interactive Canvas Area */}
                    <div 
                        onMouseDown={handleMouseDown}
                        onMouseMove={handleMouseMove}
                        onMouseUp={handleMouseUp}
                        onMouseLeave={handleMouseUp}
                        style={{
                            flex: 1,
                            position: 'relative',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            overflow: 'hidden',
                            cursor: zoomScale > 1 ? (isDragging ? 'grabbing' : 'grab') : 'default',
                        }}
                    >
                        <img
                            src={imageUrl}
                            alt="Ảnh bằng chứng vi phạm phóng to"
                            draggable={false}
                            style={{
                                maxWidth: zoomScale <= 1 ? '90vw' : 'none',
                                maxHeight: zoomScale <= 1 ? '85vh' : 'none',
                                transform: `translate(${panOffset.x}px, ${panOffset.y}px) scale(${zoomScale}) rotate(${rotation}deg)`,
                                transformOrigin: 'center center',
                                transition: isDragging ? 'none' : 'transform 0.15s ease-out',
                                boxShadow: '0 10px 40px rgba(0,0,0,0.6)',
                                borderRadius: '6px',
                                pointerEvents: 'none',
                            }}
                        />

                        {/* Floating Navigation Hint */}
                        <div style={{
                            position: 'absolute',
                            bottom: '20px',
                            backgroundColor: 'rgba(15, 23, 42, 0.85)',
                            color: '#94a3b8',
                            fontSize: '11.5px',
                            padding: '6px 14px',
                            borderRadius: '20px',
                            border: '1px solid rgba(255, 255, 255, 0.1)',
                            pointerEvents: 'none'
                        }}>
                            {zoomScale > 1 ? '🖱️ Kéo chuột để di chuyển vùng soi biển số · Cuộn chuột để thu phóng' : '🖱️ Cuộn chuột hoặc bấm nút [+] để phóng đại soi biển số'}
                        </div>
                    </div>
                </div>
            )}
        </>
    );
}