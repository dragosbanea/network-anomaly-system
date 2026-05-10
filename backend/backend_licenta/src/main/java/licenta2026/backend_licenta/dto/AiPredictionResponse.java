package licenta2026.backend_licenta.dto;

public class AiPredictionResponse {
    private boolean anomaly;
    private double anomalyScore;
    private double confidence;
    private String label;

    public boolean isAnomaly() { return anomaly; }
    public double getAnomalyScore() { return anomalyScore; }
    public double getConfidence() { return confidence; }
    public String getLabel() { return label; }

    public void setAnomaly(boolean anomaly) { this.anomaly = anomaly; }
    public void setAnomalyScore(double anomalyScore) { this.anomalyScore = anomalyScore; }
    public void setConfidence(double confidence) { this.confidence = confidence; }
    public void setLabel(String label) { this.label = label; }
}
