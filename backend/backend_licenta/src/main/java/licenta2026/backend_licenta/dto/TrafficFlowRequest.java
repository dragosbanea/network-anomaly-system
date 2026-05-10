package licenta2026.backend_licenta.dto;

public class TrafficFlowRequest {
    private String sourceIp;
    private String destinationIp;
    private int sourcePort;
    private int destinationPort;
    private String protocol;
    private long packetCount;
    private long byteCount;
    private double duration;
    private double connectionsPerSecond;
    private Long sessionId;

    public String getSourceIp() { return sourceIp; }
    public String getDestinationIp() { return destinationIp; }
    public int getSourcePort() { return sourcePort; }
    public int getDestinationPort() { return destinationPort; }
    public String getProtocol() { return protocol; }
    public long getPacketCount() { return packetCount; }
    public long getByteCount() { return byteCount; }
    public double getDuration() { return duration; }
    public double getConnectionsPerSecond() { return connectionsPerSecond; }
    public Long getSessionId() { return sessionId; }

    public void setSourceIp(String sourceIp) { this.sourceIp = sourceIp; }
    public void setDestinationIp(String destinationIp) { this.destinationIp = destinationIp; }
    public void setSourcePort(int sourcePort) { this.sourcePort = sourcePort; }
    public void setDestinationPort(int destinationPort) { this.destinationPort = destinationPort; }
    public void setProtocol(String protocol) { this.protocol = protocol; }
    public void setPacketCount(long packetCount) { this.packetCount = packetCount; }
    public void setByteCount(long byteCount) { this.byteCount = byteCount; }
    public void setDuration(double duration) { this.duration = duration; }
    public void setConnectionsPerSecond(double connectionsPerSecond) { this.connectionsPerSecond = connectionsPerSecond; }
    public void setSessionId(Long sessionId) { this.sessionId = sessionId; }
}
