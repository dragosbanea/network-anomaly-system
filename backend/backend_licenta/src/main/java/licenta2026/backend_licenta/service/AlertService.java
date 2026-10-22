package licenta2026.backend_licenta.service;

import licenta2026.backend_licenta.entity.Alert;
import licenta2026.backend_licenta.entity.TrafficFlow;
import licenta2026.backend_licenta.repository.AlertRepository;
import org.springframework.messaging.simp.SimpMessagingTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Optional;

@Service
@Transactional
public class AlertService {

    private final AlertRepository alertRepository;
    private final SimpMessagingTemplate messagingTemplate;

    public AlertService(AlertRepository alertRepository, SimpMessagingTemplate messagingTemplate) {
        this.alertRepository   = alertRepository;
        this.messagingTemplate = messagingTemplate;
    }

    public Alert createAlert(TrafficFlow flow, double anomalyScore, String mlLabel) {
        Alert alert = new Alert();
        alert.setTrafficFlow(flow);
        alert.setSourceIp(flow.getSourceIp());
        alert.setDestinationIp(flow.getDestinationIp());
        alert.setDestinationPort(flow.getDestinationPort());
        alert.setProtocol(flow.getProtocol());
        alert.setAnomalyScore(anomalyScore);
        alert.setCreatedAt(LocalDateTime.now());
        alert.setResolved(false);
        alert.setAlertType(classifyAlertType(flow, mlLabel));
        alert.setSeverity(classifySeverity(anomalyScore));
        alert.setDescription(buildDescription(flow, anomalyScore, mlLabel));
        Alert saved = alertRepository.save(alert);

        // Push real-time notification to connected frontend clients
        messagingTemplate.convertAndSend("/topic/alerts", saved);

        return saved;
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

    private String classifyAlertType(TrafficFlow flow, String mlLabel) {
        if (mlLabel != null && !mlLabel.equals("NORMAL") && !mlLabel.equals("BENIGN")) {
            String label = mlLabel.toUpperCase();
            if (label.contains("PORTSCAN") || label.contains("PORT_SCAN") || label.contains("PORT SCAN"))
                return "PORT_SCAN";
            if (label.contains("DDOS") || label.contains("DOS HULK") || label.contains("DOS SLOWLORIS")
                    || label.contains("DOS SLOWHTTPTEST") || label.contains("DOS GOLDENEYE")
                    || label.contains("HEARTBLEED"))
                return "DOS";
            if (label.contains("BRUTE") || label.contains("SSH-PATATOR") || label.contains("FTP-PATATOR"))
                return "BRUTE_FORCE";
            if (label.contains("BOT"))
                return "BOT";
            if (label.contains("WEB ATTACK") || label.contains("WEBATTACK"))
                return "WEB_ATTACK";
            if (label.contains("INFILTRAT"))
                return "INFILTRATION";
            if (label.contains("UNKNOWN"))
                return "UNKNOWN_ANOMALY";
        }
        // Fallback to heuristics when ML label is generic
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

    private String buildDescription(TrafficFlow flow, double score, String mlLabel) {
        String labelPart = (mlLabel != null && !mlLabel.equals("NORMAL")) ? " [" + mlLabel + "]" : "";
        return String.format("Anomaly detected%s from %s to %s:%d (%s) — score: %.2f",
                labelPart, flow.getSourceIp(), flow.getDestinationIp(),
                flow.getDestinationPort(), flow.getProtocol(), score);
    }
}
