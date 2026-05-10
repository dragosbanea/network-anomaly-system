package licenta2026.backend_licenta.repository;

import licenta2026.backend_licenta.entity.MonitoringSession;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.Optional;

@Repository
public interface MonitoringSessionRepository extends JpaRepository<MonitoringSession, Long> {
    Optional<MonitoringSession> findByActiveTrue();
}
