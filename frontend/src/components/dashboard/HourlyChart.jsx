import React from 'react';
import {
    ResponsiveContainer, BarChart, Bar, XAxis, YAxis,
    Tooltip, CartesianGrid, Cell,
} from 'recharts';

const HOUR_NOW = new Date().getHours();

function CustomTooltip({ active, payload, label }) {
    if (!active || !payload?.length) return null;
    return (
        <div style={{
            backgroundColor: '#ffffff',
            border: '1px solid #e2e8f0',
            borderRadius: '6px',
            padding: '8px 12px',
            fontSize: '12px',
            boxShadow: '0 4px 12px rgba(0,0,0,0.08)',
        }}>
            <div style={{ fontWeight: 700, marginBottom: '2px', color: '#0f172a' }}>{label}</div>
            <div style={{ color: '#dc2626', fontWeight: 600 }}>{payload[0].value} ca vi phạm</div>
        </div>
    );
}

export default function HourlyChart({ data }) {
    return (
        <div style={{
            backgroundColor: '#ffffff',
            border: '1px solid var(--c-border)',
            borderRadius: 'var(--r-lg)',
            overflow: 'hidden',
            boxShadow: '0 1px 3px 0 rgba(0,0,0,0.04)',
        }}>
            <div style={{
                padding: '12px 16px',
                borderBottom: '1px solid var(--c-border)',
                backgroundColor: '#f8fafc',
                display: 'flex', justifyContent: 'space-between', alignItems: 'center',
            }}>
                <span style={{ fontSize: '13px', fontWeight: 700, color: 'var(--t-primary)' }}>
                    Mật Độ Vi Phạm Theo Khung Giờ (24 Giờ)
                </span>
                <span style={{ fontSize: '11px', color: 'var(--t-muted)' }}>
                    Ngày {new Date().toLocaleDateString('vi-VN')}
                </span>
            </div>
            <div style={{ padding: '16px', height: '170px' }}>
                <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={data} margin={{ top: 4, right: 4, left: -28, bottom: 0 }} barCategoryGap="28%">
                        <CartesianGrid
                            strokeDasharray="3 3"
                            vertical={false}
                            stroke="#f1f5f9"
                        />
                        <XAxis
                            dataKey="label"
                            stroke="transparent"
                            tick={{ fill: '#64748b', fontSize: 10, fontFamily: 'var(--mono)' }}
                            tickLine={false}
                            interval={2}
                        />
                        <YAxis
                            stroke="transparent"
                            tick={{ fill: '#64748b', fontSize: 10, fontFamily: 'var(--mono)' }}
                            tickLine={false}
                            allowDecimals={false}
                        />
                        <Tooltip content={<CustomTooltip />} cursor={{ fill: '#f8fafc' }} />
                        <Bar dataKey="count" radius={[3, 3, 0, 0]}>
                            {data.map((entry, index) => (
                                <Cell
                                    key={index}
                                    fill={
                                        index === HOUR_NOW
                                            ? '#dc2626'
                                            : entry.count > 0
                                                ? '#3b82f6'
                                                : '#e2e8f0'
                                    }
                                />
                            ))}
                        </Bar>
                    </BarChart>
                </ResponsiveContainer>
            </div>
        </div>
    );
}