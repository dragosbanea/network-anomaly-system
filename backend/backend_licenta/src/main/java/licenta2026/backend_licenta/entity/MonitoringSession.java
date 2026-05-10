package licenta2026.backend_licenta.entity;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import jakarta.persistence.*;
import java.time.LocalDateTime;

@Entity
@Table(name = "monitoring_sessions")
@JsonIgnoreProperties({"hibernateLazyInitializer", "handler"})
public class MonitoringSession {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    private LocalDateTime startedAt;
    private LocalDateTime endedAt;
    private boolean active;
    private String networkInterface;
    private long totalFlowsAnalyzed;
    private long anomaliesDetected;

    public MonitoringSession() {}

    public MonitoringSession(String networkInterface) {
        this.networkInterface = networkInterface;
        this.startedAt = LocalDateTime.now();
        this.active = true;
        this.totalFlowsAnalyzed = 0;
        this.anomaliesDetected = 0;
    }

    public Long getId() { return id; }
    public LocalDateTime getStartedAt() { return startedAt; }
    public LocalDateTime getEndedAt() { return endedAt; }
    public boolean isActive() { return active; }
    public String getNetworkInterface() { return networkInterface; }
    public long getTotalFlowsAnalyzed() { return totalFlowsAnalyzed; }
    public long getAnomaliesDetected() { return anomaliesDetected; }

    public void setEndedAt(LocalDateTime endedAt) { this.endedAt = endedAt; }
    public void setActive(boolean active) { this.active = active; }
    public void setTotalFlowsAnalyzed(long totalFlowsAnalyzed) { this.totalFlowsAnalyzed = totalFlowsAnalyzed; }
    public void setAnomaliesDetected(long anomaliesDetected) { this.anomaliesDetected = anomaliesDetected; }
}
