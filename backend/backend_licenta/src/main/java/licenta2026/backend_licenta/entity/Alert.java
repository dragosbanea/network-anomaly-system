package licenta2026.backend_licenta.entity;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import jakarta.persistence.*;
import java.time.LocalDateTime;

@Entity
@Table(name = "alerts")
@JsonIgnoreProperties({"hibernateLazyInitializer", "handler", "trafficFlow"})
public class Alert {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    private String alertType;
    private String severity;
    private String sourceIp;
    private String destinationIp;
    private int destinationPort;
    private String protocol;
    private double anomalyScore;
    private String description;
    private LocalDateTime createdAt;
    private boolean resolved;
    private LocalDateTime resolvedAt;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "traffic_flow_id")
    private TrafficFlow trafficFlow;

    public Alert() {}

    public Long getId() { return id; }
    public String getAlertType() { return alertType; }
    public String getSeverity() { return severity; }
    public String getSourceIp() { return sourceIp; }
    public String getDestinationIp() { return destinationIp; }
    public int getDestinationPort() { return destinationPort; }
    public String getProtocol() { return protocol; }
    public double getAnomalyScore() { return anomalyScore; }
    public String getDescription() { return description; }
    public LocalDateTime getCreatedAt() { return createdAt; }
    public boolean isResolved() { return resolved; }
    public LocalDateTime getResolvedAt() { return resolvedAt; }
    public TrafficFlow getTrafficFlow() { return trafficFlow; }

    public void setId(Long id) { this.id = id; }
    public void setAlertType(String alertType) { this.alertType = alertType; }
    public void setSeverity(String severity) { this.severity = severity; }
    public void setSourceIp(String sourceIp) { this.sourceIp = sourceIp; }
    public void setDestinationIp(String destinationIp) { this.destinationIp = destinationIp; }
    public void setDestinationPort(int destinationPort) { this.destinationPort = destinationPort; }
    public void setProtocol(String protocol) { this.protocol = protocol; }
    public void setAnomalyScore(double anomalyScore) { this.anomalyScore = anomalyScore; }
    public void setDescription(String description) { this.description = description; }
    public void setCreatedAt(LocalDateTime createdAt) { this.createdAt = createdAt; }
    public void setResolved(boolean resolved) { this.resolved = resolved; }
    public void setResolvedAt(LocalDateTime resolvedAt) { this.resolvedAt = resolvedAt; }
    public void setTrafficFlow(TrafficFlow trafficFlow) { this.trafficFlow = trafficFlow; }
}
