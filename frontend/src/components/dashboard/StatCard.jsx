import React from 'react';

export default function StatCard({ title, value, icon, color, subText }) {
    return (
        <div style={{
            backgroundColor: '#ffffff',
            borderRadius: '16px',
            padding: '24px',
            boxShadow: '0 4px 20px rgba(0, 0, 0, 0.05)',
            borderLeft: `6px solid ${color}`,
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            transition: 'transform 0.2s',
            cursor: 'default'
        }}>
            <div>
                <span style={{ fontSize: '13px', fontWeight: '700', color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                    {title}
                </span>
                <h3 style={{ fontSize: '32px', fontWeight: '800', margin: '8px 0 4px 0', color: '#1e293b' }}>
                    {value != null ? value.toLocaleString() : '0'}
                </h3>
                {subText && <span style={{ fontSize: '12px', color: '#94a3b8' }}>{subText}</span>}
            </div>
            <div style={{
                width: '56px', height: '56px', borderRadius: '14px',
                backgroundColor: `${color}18`, display: 'flex', alignItems: 'center',
                justifyContent: 'center', fontSize: '28px'
            }}>
                {icon}
            </div>
        </div>
    );
}