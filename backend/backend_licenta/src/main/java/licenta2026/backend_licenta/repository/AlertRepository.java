package licenta2026.backend_licenta.repository;

import licenta2026.backend_licenta.entity.Alert;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.time.LocalDateTime;
import java.util.List;

@Repository
public interface AlertRepository extends JpaRepository<Alert, Long> {
    List<Alert> findByResolvedFalseOrderByCreatedAtDesc();
    List<Alert> findAllByOrderByCreatedAtDesc();
    List<Alert> findByCreatedAtAfterOrderByCreatedAtDesc(LocalDateTime since);
    long countByResolvedFalse();
    long countBySeverity(String severity);
}
