package licenta2026.backend_licenta.entity;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import jakarta.persistence.*;
import java.time.LocalDateTime;

@Entity
@Table(name = "traffic_flows")
@JsonIgnoreProperties({"hibernateLazyInitializer", "handler", "session"})
public class TrafficFlow {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    private String sourceIp;
    private String destinationIp;
    private int sourcePort;
    private int destinationPort;
    private String protocol;
    private LocalDateTime timestamp;

    // --- Core flow metrics (map 1:1 to CICIDS2017 features) ---
    private long totalFwdPackets;
    private long totalBwdPackets;
    private long totalFwdBytes;
    private long totalBwdBytes;
    private double flowDuration;        // seconds
    private double flowBytesPerSec;
    private double flowPacketsPerSec;
    private int synFlagCount;
    private int rstFlagCount;
    private double avgPacketSize;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "session_id")
    private MonitoringSession session;

    public TrafficFlow() {}

    public Long getId() { return id; }
    public String getSourceIp() { return sourceIp; }
    public String getDestinationIp() { return destinationIp; }
    public int getSourcePort() { return sourcePort; }
    public int getDestinationPort() { return destinationPort; }
    public String getProtocol() { return protocol; }
    public LocalDateTime getTimestamp() { return timestamp; }
    public long getTotalFwdPackets() { return totalFwdPackets; }
    public long getTotalBwdPackets() { return totalBwdPackets; }
    public long getTotalFwdBytes() { return totalFwdBytes; }
    public long getTotalBwdBytes() { return totalBwdBytes; }
    public double getFlowDuration() { return flowDuration; }
    public double getFlowBytesPerSec() { return flowBytesPerSec; }
    public double getFlowPacketsPerSec() { return flowPacketsPerSec; }
    public int getSynFlagCount() { return synFlagCount; }
    public int getRstFlagCount() { return rstFlagCount; }
    public double getAvgPacketSize() { return avgPacketSize; }
    public MonitoringSession getSession() { return session; }

    public void setId(Long id) { this.id = id; }
    public void setSourceIp(String v) { this.sourceIp = v; }
    public void setDestinationIp(String v) { this.destinationIp = v; }
    public void setSourcePort(int v) { this.sourcePort = v; }
    public void setDestinationPort(int v) { this.destinationPort = v; }
    public void setProtocol(String v) { this.protocol = v; }
    public void setTimestamp(LocalDateTime v) { this.timestamp = v; }
    public void setTotalFwdPackets(long v) { this.totalFwdPackets = v; }
    public void setTotalBwdPackets(long v) { this.totalBwdPackets = v; }
    public void setTotalFwdBytes(long v) { this.totalFwdBytes = v; }
    public void setTotalBwdBytes(long v) { this.totalBwdBytes = v; }
    public void setFlowDuration(double v) { this.flowDuration = v; }
    public void setFlowBytesPerSec(double v) { this.flowBytesPerSec = v; }
    public void setFlowPacketsPerSec(double v) { this.flowPacketsPerSec = v; }
    public void setSynFlagCount(int v) { this.synFlagCount = v; }
    public void setRstFlagCount(int v) { this.rstFlagCount = v; }
    public void setAvgPacketSize(double v) { this.avgPacketSize = v; }
    public void setSession(MonitoringSession v) { this.session = v; }
}
