import React from 'react';

export default function StatCard({ title, value, icon, color, subText }) {
  return (
    <div style={{
      backgroundColor: '#ffffff',
      borderRadius: '18px',
      padding: '24px 22px',
      boxShadow: '0 4px 25px rgba(0, 0, 0, 0.05)',
      border: '1px solid #e2e8f0',
      borderTop: `4px solid ${color}`,
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'center',
      transition: 'all 0.2s ease',
      cursor: 'default',
      position: 'relative',
      overflow: 'hidden'
    }}
    onMouseEnter={(e) => {
      e.currentTarget.style.transform = 'translateY(-3px)';
      e.currentTarget.style.boxShadow = '0 12px 30px rgba(0, 0, 0, 0.08)';
    }}
    onMouseLeave={(e) => {
      e.currentTarget.style.transform = 'translateY(0)';
      e.currentTarget.style.boxShadow = '0 4px 25px rgba(0, 0, 0, 0.05)';
    }}
    >
      <div>
        <span style={{ fontSize: '11.5px', fontWeight: '800', color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.6px' }}>
          {title}
        </span>
        <h3 style={{ fontSize: '32px', fontWeight: '900', margin: '6px 0 4px 0', color: '#0f172a', letterSpacing: '-0.5px' }}>
          {value != null ? value.toLocaleString() : '0'}
        </h3>
        {subText && (
          <span style={{ fontSize: '12px', color: '#94a3b8', display: 'flex', alignItems: 'center', gap: '4px' }}>
            <span>●</span> {subText}
          </span>
        )}
      </div>

      <div style={{
        width: '58px',
        height: '58px',
        borderRadius: '16px',
        backgroundColor: `${color}14`,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        fontSize: '28px',
        flexShrink: 0
      }}>
        {icon}
      </div>
    </div>
  );
}