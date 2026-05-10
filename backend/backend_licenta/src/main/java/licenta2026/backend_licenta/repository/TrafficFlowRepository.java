package licenta2026.backend_licenta.repository;

import licenta2026.backend_licenta.entity.TrafficFlow;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.time.LocalDateTime;
import java.util.List;

@Repository
public interface TrafficFlowRepository extends JpaRepository<TrafficFlow, Long> {
    List<TrafficFlow> findBySessionIdOrderByTimestampDesc(Long sessionId);
    List<TrafficFlow> findByTimestampAfterOrderByTimestampDesc(LocalDateTime since);
    long countByTimestampAfter(LocalDateTime since);
}
