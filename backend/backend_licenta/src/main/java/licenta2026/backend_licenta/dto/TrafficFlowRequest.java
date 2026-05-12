package licenta2026.backend_licenta.dto;

public class TrafficFlowRequest {
    private String sourceIp;
    private String destinationIp;
    private int sourcePort;
    private int destinationPort;
    private String protocol;
    private long totalFwdPackets;
    private long totalBwdPackets;
    private long totalFwdBytes;
    private long totalBwdBytes;
    private double flowDuration;
    private double flowBytesPerSec;
    private double flowPacketsPerSec;
    private int synFlagCount;
    private int rstFlagCount;
    private double avgPacketSize;
    private Long sessionId;

    public String getSourceIp() { return sourceIp; }
    public String getDestinationIp() { return destinationIp; }
    public int getSourcePort() { return sourcePort; }
    public int getDestinationPort() { return destinationPort; }
    public String getProtocol() { return protocol; }
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
    public Long getSessionId() { return sessionId; }

    public void setSourceIp(String v) { this.sourceIp = v; }
    public void setDestinationIp(String v) { this.destinationIp = v; }
    public void setSourcePort(int v) { this.sourcePort = v; }
    public void setDestinationPort(int v) { this.destinationPort = v; }
    public void setProtocol(String v) { this.protocol = v; }
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
    public void setSessionId(Long v) { this.sessionId = v; }
}
