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
    private long packetCount;
    private long byteCount;
    private double duration;
    private double connectionsPerSecond;
    private LocalDateTime timestamp;

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
    public long getPacketCount() { return packetCount; }
    public long getByteCount() { return byteCount; }
    public double getDuration() { return duration; }
    public double getConnectionsPerSecond() { return connectionsPerSecond; }
    public LocalDateTime getTimestamp() { return timestamp; }
    public MonitoringSession getSession() { return session; }

    public void setId(Long id) { this.id = id; }
    public void setSourceIp(String sourceIp) { this.sourceIp = sourceIp; }
    public void setDestinationIp(String destinationIp) { this.destinationIp = destinationIp; }
    public void setSourcePort(int sourcePort) { this.sourcePort = sourcePort; }
    public void setDestinationPort(int destinationPort) { this.destinationPort = destinationPort; }
    public void setProtocol(String protocol) { this.protocol = protocol; }
    public void setPacketCount(long packetCount) { this.packetCount = packetCount; }
    public void setByteCount(long byteCount) { this.byteCount = byteCount; }
    public void setDuration(double duration) { this.duration = duration; }
    public void setConnectionsPerSecond(double connectionsPerSecond) { this.connectionsPerSecond = connectionsPerSecond; }
    public void setTimestamp(LocalDateTime timestamp) { this.timestamp = timestamp; }
    public void setSession(MonitoringSession session) { this.session = session; }
}
