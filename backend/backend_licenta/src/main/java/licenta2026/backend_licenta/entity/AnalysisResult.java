package licenta2026.backend_licenta.entity;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import jakarta.persistence.*;
import java.time.LocalDateTime;

@Entity
@Table(name = "analysis_results")
@JsonIgnoreProperties({"hibernateLazyInitializer", "handler"})
public class AnalysisResult {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @OneToOne(fetch = FetchType.EAGER)
    @JoinColumn(name = "traffic_flow_id")
    private TrafficFlow trafficFlow;

    private boolean anomaly;
    private double anomalyScore;
    private double confidence;
    private String details;
    private LocalDateTime analyzedAt;

    public AnalysisResult() {}

    public Long getId() { return id; }
    public TrafficFlow getTrafficFlow() { return trafficFlow; }
    public boolean isAnomaly() { return anomaly; }
    public double getAnomalyScore() { return anomalyScore; }
    public double getConfidence() { return confidence; }
    public String getDetails() { return details; }
    public LocalDateTime getAnalyzedAt() { return analyzedAt; }

    public void setId(Long id) { this.id = id; }
    public void setTrafficFlow(TrafficFlow trafficFlow) { this.trafficFlow = trafficFlow; }
    public void setAnomaly(boolean anomaly) { this.anomaly = anomaly; }
    public void setAnomalyScore(double anomalyScore) { this.anomalyScore = anomalyScore; }
    public void setConfidence(double confidence) { this.confidence = confidence; }
    public void setDetails(String details) { this.details = details; }
    public void setAnalyzedAt(LocalDateTime analyzedAt) { this.analyzedAt = analyzedAt; }
}
