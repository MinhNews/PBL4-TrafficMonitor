import React from 'react';
import {
    ResponsiveContainer, ComposedChart, Bar, Line, XAxis, YAxis,
    Tooltip, CartesianGrid, Cell, Legend,
} from 'recharts';

const HOUR_NOW = new Date().getHours();

function CustomTooltip({ active, payload, label }) {
    if (!active || !payload?.length) return null;

    const row = payload[0]?.payload || {};
    const violations = row.count || 0;
    const vehicles = row.vehicleCount || 0;
    const motorcycles = row.motorcycleCount || 0;
    const cars = row.carCount || 0;

    return (
        <div style={{
            backgroundColor: '#ffffff',
            border: '1px solid #e2e8f0',
            borderRadius: '6px',
            padding: '8px 12px',
            fontSize: '12px',
            boxShadow: '0 4px 12px rgba(0,0,0,0.08)',
            minWidth: '168px',
        }}>
            <div style={{ fontWeight: 700, marginBottom: '2px', color: '#0f172a' }}>{label}</div>
            <div style={{ color: '#16a34a', fontWeight: 700 }}>{vehicles} lượt xe</div>
            {vehicles > 0 && (
                <div style={{ color: '#64748b', fontSize: '11px', marginLeft: '10px' }}>
                    {motorcycles} xe máy · {cars} ô tô
                </div>
            )}
            <div style={{ color: '#dc2626', fontWeight: 600 }}>{violations} ca vi phạm</div>
        </div>
    );
}

function LegendContent({ payload }) {
    if (!payload?.length) return null;
    return (
        <div style={{ display: 'flex', gap: '14px', justifyContent: 'flex-end', paddingRight: '8px' }}>
            {payload.map((entry) => (
                <div key={entry.dataKey} style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
                    <span style={{
                        width: '9px', height: '9px', borderRadius: '2px',
                        backgroundColor: entry.color, display: 'inline-block',
                    }} />
                    <span style={{ fontSize: '10.5px', color: '#64748b', fontWeight: 600 }}>
                        {entry.value}
                    </span>
                </div>
            ))}
        </div>
    );
}

export default function HourlyChart({ data }) {
    const hasFlowData = (data || []).some(d => (d.vehicleCount || 0) > 0);

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
                    Lưu Lượng Xe & Vi Phạm Theo Khung Giờ (24 Giờ)
                </span>
                <span style={{ fontSize: '11px', color: 'var(--t-muted)' }}>
                    Ngày {new Date().toLocaleDateString('vi-VN')}
                </span>
            </div>
            <div style={{ padding: '16px 16px 8px 16px', height: '215px' }}>
                <ResponsiveContainer width="100%" height="100%">
                    <ComposedChart data={data} margin={{ top: 4, right: 4, left: -24, bottom: 0 }} barCategoryGap="28%">
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
                        {/* Trục trái: số ca vi phạm */}
                        <YAxis
                            yAxisId="left"
                            stroke="transparent"
                            tick={{ fill: '#94a3b8', fontSize: 10, fontFamily: 'var(--mono)' }}
                            tickLine={false}
                            allowDecimals={false}
                        />
                        {/* Trục phải: lưu lượng xe (khác đơn vị, cần trục riêng) */}
                        <YAxis
                            yAxisId="right"
                            orientation="right"
                            stroke="transparent"
                            tick={{ fill: '#86efac', fontSize: 10, fontFamily: 'var(--mono)' }}
                            tickLine={false}
                            allowDecimals={false}
                            width={38}
                        />
                        <Tooltip content={<CustomTooltip />} cursor={{ fill: '#f8fafc' }} />
                        <Legend content={<LegendContent />} verticalAlign="top" height={22} />

                        {/* Cột: vi phạm */}
                        <Bar yAxisId="left" dataKey="count" name="Vi phạm" radius={[3, 3, 0, 0]} maxBarSize={18}>
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

                        {/* Đường: lưu lượng xe trong giờ */}
                        <Line
                            yAxisId="right"
                            type="monotone"
                            dataKey="vehicleCount"
                            name="Lượt xe"
                            stroke="#16a34a"
                            strokeWidth={2}
                            dot={{ r: 2.5, strokeWidth: 0, fill: '#16a34a' }}
                            activeDot={{ r: 4 }}
                            isAnimationActive={false}
                        />
                    </ComposedChart>
                </ResponsiveContainer>
            </div>
            {!hasFlowData && (
                <div style={{
                    padding: '0 16px 12px 16px',
                    fontSize: '10.5px',
                    color: 'var(--t-muted)',
                }}>
                    Chưa có dữ liệu lưu lượng hôm nay — bật AI Engine để bắt đầu đếm xe qua vạch.
                </div>
            )}
        </div>
    );
}
