package com.pbl4.trafficmonitor.entity;

import jakarta.persistence.*;
import lombok.*;

@Entity 
@Table(name = "vehicles")
@Data 
@Builder 
@NoArgsConstructor 
@AllArgsConstructor
public class Vehicle {
    @Id 
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false, length = 30)
    private String type;         // MOTORCYCLE, CAR, TRUCK, BUS

    @Column(name = "name_vi", length = 50)
    private String nameVi;       // "Xe máy", "Ô tô"

    @Column(length = 200)
    private String description;
}
