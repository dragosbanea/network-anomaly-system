package licenta2026.backend_licenta.service;

import licenta2026.backend_licenta.entity.MonitoringSession;
import licenta2026.backend_licenta.repository.MonitoringSessionRepository;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Optional;

@Service
@Transactional
public class MonitoringService {

    private final MonitoringSessionRepository sessionRepository;

    public MonitoringService(MonitoringSessionRepository sessionRepository) {
        this.sessionRepository = sessionRepository;
    }

    public MonitoringSession startSession(String networkInterface) {
        sessionRepository.findByActiveTrue().ifPresent(s -> {
            s.setActive(false);
            s.setEndedAt(LocalDateTime.now());
            sessionRepository.save(s);
        });
        return sessionRepository.save(new MonitoringSession(networkInterface));
    }

    public Optional<MonitoringSession> stopSession() {
        return sessionRepository.findByActiveTrue().map(s -> {
            s.setActive(false);
            s.setEndedAt(LocalDateTime.now());
            return sessionRepository.save(s);
        });
    }

    public Optional<MonitoringSession> getActiveSession() {
        return sessionRepository.findByActiveTrue();
    }

    public List<MonitoringSession> getAllSessions() {
        return sessionRepository.findAll();
    }

    public void incrementFlowCount(Long sessionId) {
        sessionRepository.findById(sessionId).ifPresent(s -> {
            s.setTotalFlowsAnalyzed(s.getTotalFlowsAnalyzed() + 1);
            sessionRepository.save(s);
        });
    }

    public void incrementAnomalyCount(Long sessionId) {
        sessionRepository.findById(sessionId).ifPresent(s -> {
            s.setAnomaliesDetected(s.getAnomaliesDetected() + 1);
            sessionRepository.save(s);
        });
    }
}
