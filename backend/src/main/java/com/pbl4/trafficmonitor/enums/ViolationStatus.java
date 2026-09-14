package com.pbl4.trafficmonitor.enums;

public enum ViolationStatus {
    PENDING,     // AI vừa phát hiện, chờ CSGT duyệt
    CONFIRMED,   // CSGT đã xác nhận phạt
    DISMISSED    // CSGT bác bỏ (báo động giả)
}
