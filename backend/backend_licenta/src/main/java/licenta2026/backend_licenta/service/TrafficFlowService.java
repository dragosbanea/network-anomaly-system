package licenta2026.backend_licenta.service;

import licenta2026.backend_licenta.dto.AiPredictionRequest;
import licenta2026.backend_licenta.dto.AiPredictionResponse;
import licenta2026.backend_licenta.dto.TrafficFlowRequest;
import licenta2026.backend_licenta.entity.AnalysisResult;
import licenta2026.backend_licenta.entity.TrafficFlow;
import licenta2026.backend_licenta.repository.AnalysisResultRepository;
import licenta2026.backend_licenta.repository.MonitoringSessionRepository;
import licenta2026.backend_licenta.repository.TrafficFlowRepository;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.client.RestTemplate;

import java.time.LocalDateTime;
import java.util.List;

@Service
@Transactional
public class TrafficFlowService {

    private final TrafficFlowRepository flowRepository;
    private final AnalysisResultRepository resultRepository;
    private final MonitoringSessionRepository sessionRepository;
    private final AlertService alertService;
    private final MonitoringService monitoringService;
    private final RestTemplate restTemplate;

    @Value("${ai.service.url}")
    private String aiServiceUrl;

    public TrafficFlowService(TrafficFlowRepository flowRepository,
                               AnalysisResultRepository resultRepository,
                               MonitoringSessionRepository sessionRepository,
                               AlertService alertService,
                               MonitoringService monitoringService,
                               RestTemplate restTemplate) {
        this.flowRepository    = flowRepository;
        this.resultRepository  = resultRepository;
        this.sessionRepository = sessionRepository;
        this.alertService      = alertService;
        this.monitoringService = monitoringService;
        this.restTemplate      = restTemplate;
    }

    public AnalysisResult analyzeFlow(TrafficFlowRequest request) {
        Long sessionId = request.getSessionId();
        if (sessionId == null) {
            sessionId = monitoringService.getActiveSession()
                    .map(s -> s.getId())
                    .orElse(null);
        }

        TrafficFlow flow = buildFlow(request, sessionId);
        flow = flowRepository.save(flow);

        if (sessionId != null) {
            monitoringService.incrementFlowCount(sessionId);
        }

        AiPredictionResponse prediction = callAiService(flow);

        AnalysisResult result = new AnalysisResult();
        result.setTrafficFlow(flow);
        result.setAnomaly(prediction.isAnomaly());
        result.setAnomalyScore(prediction.getAnomalyScore());
        result.setConfidence(prediction.getConfidence());
        result.setDetails(prediction.getLabel());
        result.setAnalyzedAt(LocalDateTime.now());
        result = resultRepository.save(result);

        if (prediction.isAnomaly()) {
            alertService.createAlert(flow, prediction.getAnomalyScore(), prediction.getLabel());
            if (sessionId != null) {
                monitoringService.incrementAnomalyCount(sessionId);
            }
        }

        return result;
    }

    public List<TrafficFlow> getRecentFlows(int minutes) {
        return flowRepository.findByTimestampAfterOrderByTimestampDesc(
                LocalDateTime.now().minusMinutes(minutes));
    }

    public List<AnalysisResult> getAnomalyResults() {
        return resultRepository.findByAnomalyTrueOrderByAnalyzedAtDesc();
    }

    public List<AnalysisResult> getAllResults() {
        return resultRepository.findAll();
    }

    private TrafficFlow buildFlow(TrafficFlowRequest req, Long sessionId) {
        TrafficFlow flow = new TrafficFlow();
        flow.setSourceIp(req.getSourceIp());
        flow.setDestinationIp(req.getDestinationIp());
        flow.setSourcePort(req.getSourcePort());
        flow.setDestinationPort(req.getDestinationPort());
        flow.setProtocol(req.getProtocol());
        flow.setTotalFwdPackets(req.getTotalFwdPackets());
        flow.setTotalBwdPackets(req.getTotalBwdPackets());
        flow.setTotalFwdBytes(req.getTotalFwdBytes());
        flow.setTotalBwdBytes(req.getTotalBwdBytes());
        flow.setFlowDuration(req.getFlowDuration());
        flow.setFlowBytesPerSec(req.getFlowBytesPerSec());
        flow.setFlowPacketsPerSec(req.getFlowPacketsPerSec());
        flow.setSynFlagCount(req.getSynFlagCount());
        flow.setRstFlagCount(req.getRstFlagCount());
        flow.setAvgPacketSize(req.getAvgPacketSize());
        // Extended
        flow.setFinFlagCount(req.getFinFlagCount());
        flow.setAckFlagCount(req.getAckFlagCount());
        flow.setPshFlagCount(req.getPshFlagCount());
        flow.setUrgFlagCount(req.getUrgFlagCount());
        flow.setFwdPacketLenMin(req.getFwdPacketLenMin());
        flow.setFwdPacketLenMax(req.getFwdPacketLenMax());
        flow.setBwdPacketLenMax(req.getBwdPacketLenMax());
        flow.setPacketLenStd(req.getPacketLenStd());
        flow.setTimestamp(LocalDateTime.now());

        if (sessionId != null) {
            sessionRepository.findById(sessionId).ifPresent(flow::setSession);
        }
        return flow;
    }

    private AiPredictionResponse callAiService(TrafficFlow flow) {
        try {
            AiPredictionRequest aiReq = new AiPredictionRequest(
                    flow.getDestinationPort(),
                    flow.getFlowDuration(),
                    flow.getTotalFwdPackets(),
                    flow.getTotalBwdPackets(),
                    flow.getTotalFwdBytes(),
                    flow.getTotalBwdBytes(),
                    flow.getFlowBytesPerSec(),
                    flow.getFlowPacketsPerSec(),
                    flow.getSynFlagCount(),
                    flow.getRstFlagCount(),
                    flow.getAvgPacketSize(),
                    flow.getFinFlagCount(),
                    flow.getAckFlagCount(),
                    flow.getPshFlagCount(),
                    flow.getUrgFlagCount(),
                    flow.getFwdPacketLenMin(),
                    flow.getFwdPacketLenMax(),
                    flow.getBwdPacketLenMax(),
                    flow.getPacketLenStd()
            );
            return restTemplate.postForObject(aiServiceUrl + "/predict", aiReq, AiPredictionResponse.class);
        } catch (Exception e) {
            AiPredictionResponse fallback = new AiPredictionResponse();
            fallback.setAnomaly(false);
            fallback.setAnomalyScore(0.0);
            fallback.setConfidence(0.0);
            fallback.setLabel("AI service unavailable");
            return fallback;
        }
    }
}
