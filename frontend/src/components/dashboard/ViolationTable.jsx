import React from 'react';

export default function ViolationTable({ violations, onSelectViolation }) {
  // Hàm bổ trợ hiển thị tên lỗi tiếng Việt
  const renderViolationType = (v) => {
    const type = v.typeDisplay || v.violationType || v.type;
    if (type === 'RED_LIGHT_CROSS' || type === 'Vượt đèn đỏ') return 'Vượt đèn đỏ';
    if (type === 'NO_HELMET' || type === 'Không đội mũ bảo hiểm') return 'Không đội mũ bảo hiểm';
    return type || 'Vi phạm khác';
  };

  // Hàm định dạng ngày giờ hiển thị đẹp
  const formatDateTime = (dateStr) => {
    if (!dateStr) return 'N/A';
    if (typeof dateStr === 'string') {
      return dateStr.replace('T', ' ').substring(0, 19);
    }
    return dateStr;
  };

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
              violations.map((v) => {
                const typeCode = v.violationType || v.type;
                const isNoHelmet = typeCode === 'NO_HELMET';

                return (
                  <tr 
                    key={v.id} 
                    style={{ 
                      borderBottom: '1px solid #f1f5f9', 
                      fontSize: '13.5px',
                      transition: 'background-color 0.2s'
                    }}
                    onMouseEnter={(e) => e.currentTarget.style.backgroundColor = '#f8fafc'}
                    onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'transparent'}
                  >
                    <td style={{ padding: '12px', fontWeight: '700', color: '#0f172a' }}>#{v.id}</td>
                    <td style={{ padding: '12px', color: '#64748b' }}>
                      {formatDateTime(v.detectedAt)}
                    </td>
                    <td style={{ padding: '12px' }}>
                      <span style={{
                        padding: '4px 10px', 
                        borderRadius: '20px', 
                        fontSize: '12px', 
                        fontWeight: '700',
                        backgroundColor: isNoHelmet ? '#fef3c7' : '#fee2e2',
                        color: isNoHelmet ? '#d97706' : '#dc2626'
                      }}>
                        {renderViolationType(v)}
                      </span>
                    </td>
                    <td style={{ padding: '12px', fontWeight: '500', color: '#334155' }}>
                      {v.vehicleType || 'N/A'}
                    </td>
                    <td style={{ padding: '12px', fontWeight: '700', color: '#059669' }}>
                      {v.confidence ? `${Math.round(v.confidence * (v.confidence <= 1 ? 100 : 1))}%` : 'N/A'}
                    </td>
                    <td style={{ padding: '12px' }}>
                      <span style={{
                        padding: '4px 10px', 
                        borderRadius: '20px', 
                        fontSize: '12px', 
                        fontWeight: '700',
                        backgroundColor: v.status === 'CONFIRMED' ? '#dcfce7' : v.status === 'DISMISSED' ? '#f1f5f9' : '#e0f2fe',
                        color: v.status === 'CONFIRMED' ? '#16a34a' : v.status === 'DISMISSED' ? '#64748b' : '#0284c7'
                      }}>
                        {v.status || 'PENDING'}
                      </span>
                    </td>
                    <td style={{ padding: '12px' }}>
                      <button
                        onClick={() => onSelectViolation(v)}
                        style={{
                          padding: '6px 14px', 
                          borderRadius: '8px', 
                          border: 'none',
                          backgroundColor: '#3b82f6', 
                          color: '#ffffff', 
                          cursor: 'pointer',
                          fontWeight: '700', 
                          fontSize: '12px',
                          boxShadow: '0 2px 4px rgba(59, 130, 246, 0.2)'
                        }}
                      >
                        Chi tiết
                      </button>
                    </td>
                  </tr>
                );
              })
            ) : (
              <tr>
                <td colSpan="7" style={{ textAlign: 'center', padding: '24px', color: '#94a3b8' }}>
                  Chưa có vi phạm nào được ghi nhận.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}