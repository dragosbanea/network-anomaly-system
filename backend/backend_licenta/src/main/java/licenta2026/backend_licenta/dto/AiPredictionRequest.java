package licenta2026.backend_licenta.dto;

public class AiPredictionRequest {
    private long packetCount;
    private long byteCount;
    private double duration;
    private int protocol;
    private int destinationPort;
    private double connectionsPerSecond;

    public AiPredictionRequest() {}

    public AiPredictionRequest(long packetCount, long byteCount, double duration,
                                int protocol, int destinationPort, double connectionsPerSecond) {
        this.packetCount = packetCount;
        this.byteCount = byteCount;
        this.duration = duration;
        this.protocol = protocol;
        this.destinationPort = destinationPort;
        this.connectionsPerSecond = connectionsPerSecond;
    }

    public long getPacketCount() { return packetCount; }
    public long getByteCount() { return byteCount; }
    public double getDuration() { return duration; }
    public int getProtocol() { return protocol; }
    public int getDestinationPort() { return destinationPort; }
    public double getConnectionsPerSecond() { return connectionsPerSecond; }

    public void setPacketCount(long packetCount) { this.packetCount = packetCount; }
    public void setByteCount(long byteCount) { this.byteCount = byteCount; }
    public void setDuration(double duration) { this.duration = duration; }
    public void setProtocol(int protocol) { this.protocol = protocol; }
    public void setDestinationPort(int destinationPort) { this.destinationPort = destinationPort; }
    public void setConnectionsPerSecond(double connectionsPerSecond) { this.connectionsPerSecond = connectionsPerSecond; }
}
