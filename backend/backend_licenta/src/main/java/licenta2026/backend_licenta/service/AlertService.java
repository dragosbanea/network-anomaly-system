package licenta2026.backend_licenta.service;

import licenta2026.backend_licenta.entity.Alert;
import licenta2026.backend_licenta.entity.TrafficFlow;
import licenta2026.backend_licenta.repository.AlertRepository;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Optional;

@Service
@Transactional
public class AlertService {

    private final AlertRepository alertRepository;

    public AlertService(AlertRepository alertRepository) {
        this.alertRepository = alertRepository;
    }

    public Alert createAlert(TrafficFlow flow, double anomalyScore) {
        Alert alert = new Alert();
        alert.setTrafficFlow(flow);
        alert.setSourceIp(flow.getSourceIp());
        alert.setDestinationIp(flow.getDestinationIp());
        alert.setDestinationPort(flow.getDestinationPort());
        alert.setProtocol(flow.getProtocol());
        alert.setAnomalyScore(anomalyScore);
        alert.setCreatedAt(LocalDateTime.now());
        alert.setResolved(false);
        alert.setAlertType(classifyAlertType(flow, anomalyScore));
        alert.setSeverity(classifySeverity(anomalyScore));
        alert.setDescription(buildDescription(flow, anomalyScore));
        return alertRepository.save(alert);
    }

    public List<Alert> getActiveAlerts() {
        return alertRepository.findByResolvedFalseOrderByCreatedAtDesc();
    }

    public List<Alert> getAllAlerts() {
        return alertRepository.findAllByOrderByCreatedAtDesc();
    }

    public List<Alert> getRecentAlerts(int minutes) {
        return alertRepository.findByCreatedAtAfterOrderByCreatedAtDesc(
                LocalDateTime.now().minusMinutes(minutes));
    }

    public Optional<Alert> resolveAlert(Long id) {
        return alertRepository.findById(id).map(alert -> {
            alert.setResolved(true);
            alert.setResolvedAt(LocalDateTime.now());
            return alertRepository.save(alert);
        });
    }

    public long countUnresolved() {
        return alertRepository.countByResolvedFalse();
    }

    private String classifyAlertType(TrafficFlow flow, double score) {
        if (flow.getFlowPacketsPerSec() > 100) return "PORT_SCAN";
        if ((flow.getTotalFwdBytes() + flow.getTotalBwdBytes()) > 1_000_000
                && flow.getFlowDuration() < 2) return "DOS";
        int port = flow.getDestinationPort();
        if (port == 22 || port == 3389 || port == 21 || port == 23) return "BRUTE_FORCE";
        return "ANOMALY";
    }

    private String classifySeverity(double score) {
        if (score > 0.8) return "CRITICAL";
        if (score > 0.6) return "HIGH";
        if (score > 0.4) return "MEDIUM";
        return "LOW";
    }

    private String buildDescription(TrafficFlow flow, double score) {
        return String.format("Anomaly detected from %s to %s:%d (%s) — score: %.2f",
                flow.getSourceIp(), flow.getDestinationIp(),
                flow.getDestinationPort(), flow.getProtocol(), score);
    }
}
