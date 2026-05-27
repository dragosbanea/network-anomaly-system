package licenta2026.backend_licenta.dto;

public class AiPredictionRequest {
    // Base 11 features
    private int destinationPort;
    private double flowDuration;
    private long totalFwdPackets;
    private long totalBwdPackets;
    private long totalFwdBytes;
    private long totalBwdBytes;
    private double flowBytesPerSec;
    private double flowPacketsPerSec;
    private int synFlagCount;
    private int rstFlagCount;
    private double avgPacketSize;
    // Extended 8 features
    private int finFlagCount;
    private int ackFlagCount;
    private int pshFlagCount;
    private int urgFlagCount;
    private double fwdPacketLenMin;
    private double fwdPacketLenMax;
    private double bwdPacketLenMax;
    private double packetLenStd;

    public AiPredictionRequest() {}

    public AiPredictionRequest(int destinationPort, double flowDuration,
                                long totalFwdPackets, long totalBwdPackets,
                                long totalFwdBytes, long totalBwdBytes,
                                double flowBytesPerSec, double flowPacketsPerSec,
                                int synFlagCount, int rstFlagCount, double avgPacketSize,
                                int finFlagCount, int ackFlagCount, int pshFlagCount,
                                int urgFlagCount, double fwdPacketLenMin, double fwdPacketLenMax,
                                double bwdPacketLenMax, double packetLenStd) {
        this.destinationPort  = destinationPort;
        this.flowDuration     = flowDuration;
        this.totalFwdPackets  = totalFwdPackets;
        this.totalBwdPackets  = totalBwdPackets;
        this.totalFwdBytes    = totalFwdBytes;
        this.totalBwdBytes    = totalBwdBytes;
        this.flowBytesPerSec  = flowBytesPerSec;
        this.flowPacketsPerSec = flowPacketsPerSec;
        this.synFlagCount     = synFlagCount;
        this.rstFlagCount     = rstFlagCount;
        this.avgPacketSize    = avgPacketSize;
        this.finFlagCount     = finFlagCount;
        this.ackFlagCount     = ackFlagCount;
        this.pshFlagCount     = pshFlagCount;
        this.urgFlagCount     = urgFlagCount;
        this.fwdPacketLenMin  = fwdPacketLenMin;
        this.fwdPacketLenMax  = fwdPacketLenMax;
        this.bwdPacketLenMax  = bwdPacketLenMax;
        this.packetLenStd     = packetLenStd;
    }

    public int getDestinationPort() { return destinationPort; }
    public double getFlowDuration() { return flowDuration; }
    public long getTotalFwdPackets() { return totalFwdPackets; }
    public long getTotalBwdPackets() { return totalBwdPackets; }
    public long getTotalFwdBytes() { return totalFwdBytes; }
    public long getTotalBwdBytes() { return totalBwdBytes; }
    public double getFlowBytesPerSec() { return flowBytesPerSec; }
    public double getFlowPacketsPerSec() { return flowPacketsPerSec; }
    public int getSynFlagCount() { return synFlagCount; }
    public int getRstFlagCount() { return rstFlagCount; }
    public double getAvgPacketSize() { return avgPacketSize; }
    public int getFinFlagCount() { return finFlagCount; }
    public int getAckFlagCount() { return ackFlagCount; }
    public int getPshFlagCount() { return pshFlagCount; }
    public int getUrgFlagCount() { return urgFlagCount; }
    public double getFwdPacketLenMin() { return fwdPacketLenMin; }
    public double getFwdPacketLenMax() { return fwdPacketLenMax; }
    public double getBwdPacketLenMax() { return bwdPacketLenMax; }
    public double getPacketLenStd() { return packetLenStd; }

    public void setDestinationPort(int v) { this.destinationPort = v; }
    public void setFlowDuration(double v) { this.flowDuration = v; }
    public void setTotalFwdPackets(long v) { this.totalFwdPackets = v; }
    public void setTotalBwdPackets(long v) { this.totalBwdPackets = v; }
    public void setTotalFwdBytes(long v) { this.totalFwdBytes = v; }
    public void setTotalBwdBytes(long v) { this.totalBwdBytes = v; }
    public void setFlowBytesPerSec(double v) { this.flowBytesPerSec = v; }
    public void setFlowPacketsPerSec(double v) { this.flowPacketsPerSec = v; }
    public void setSynFlagCount(int v) { this.synFlagCount = v; }
    public void setRstFlagCount(int v) { this.rstFlagCount = v; }
    public void setAvgPacketSize(double v) { this.avgPacketSize = v; }
    public void setFinFlagCount(int v) { this.finFlagCount = v; }
    public void setAckFlagCount(int v) { this.ackFlagCount = v; }
    public void setPshFlagCount(int v) { this.pshFlagCount = v; }
    public void setUrgFlagCount(int v) { this.urgFlagCount = v; }
    public void setFwdPacketLenMin(double v) { this.fwdPacketLenMin = v; }
    public void setFwdPacketLenMax(double v) { this.fwdPacketLenMax = v; }
    public void setBwdPacketLenMax(double v) { this.bwdPacketLenMax = v; }
    public void setPacketLenStd(double v) { this.packetLenStd = v; }
}
