package com.pbl4.trafficmonitor.repository;

import com.pbl4.trafficmonitor.entity.User;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;
import java.util.Optional;

@Repository
public interface UserRepository extends JpaRepository<User, Long> {
    // Tìm người dùng theo username để kiểm tra đăng nhập
    Optional<User> findByUsername(String username);
}
