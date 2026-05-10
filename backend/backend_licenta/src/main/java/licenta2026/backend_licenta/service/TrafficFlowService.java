package licenta2026.backend_licenta.service;

import licenta2026.backend_licenta.dto.AiPredictionRequest;
import licenta2026.backend_licenta.dto.AiPredictionResponse;
import licenta2026.backend_licenta.dto.TrafficFlowRequest;
import licenta2026.backend_licenta.entity.AnalysisResult;
import licenta2026.backend_licenta.entity.MonitoringSession;
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
import java.util.Map;

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

    private static final Map<String, Integer> PROTOCOL_MAP = Map.of(
            "TCP", 6, "UDP", 17, "ICMP", 1
    );

    public TrafficFlowService(TrafficFlowRepository flowRepository,
                               AnalysisResultRepository resultRepository,
                               MonitoringSessionRepository sessionRepository,
                               AlertService alertService,
                               MonitoringService monitoringService,
                               RestTemplate restTemplate) {
        this.flowRepository = flowRepository;
        this.resultRepository = resultRepository;
        this.sessionRepository = sessionRepository;
        this.alertService = alertService;
        this.monitoringService = monitoringService;
        this.restTemplate = restTemplate;
    }

    public AnalysisResult analyzeFlow(TrafficFlowRequest request) {
        TrafficFlow flow = buildFlow(request);
        flow = flowRepository.save(flow);

        if (request.getSessionId() != null) {
            monitoringService.incrementFlowCount(request.getSessionId());
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
            alertService.createAlert(flow, prediction.getAnomalyScore());
            if (request.getSessionId() != null) {
                monitoringService.incrementAnomalyCount(request.getSessionId());
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

    private TrafficFlow buildFlow(TrafficFlowRequest req) {
        TrafficFlow flow = new TrafficFlow();
        flow.setSourceIp(req.getSourceIp());
        flow.setDestinationIp(req.getDestinationIp());
        flow.setSourcePort(req.getSourcePort());
        flow.setDestinationPort(req.getDestinationPort());
        flow.setProtocol(req.getProtocol());
        flow.setPacketCount(req.getPacketCount());
        flow.setByteCount(req.getByteCount());
        flow.setDuration(req.getDuration());
        flow.setConnectionsPerSecond(req.getConnectionsPerSecond());
        flow.setTimestamp(LocalDateTime.now());

        if (req.getSessionId() != null) {
            sessionRepository.findById(req.getSessionId()).ifPresent(flow::setSession);
        }
        return flow;
    }

    private AiPredictionResponse callAiService(TrafficFlow flow) {
        try {
            int protocolNum = PROTOCOL_MAP.getOrDefault(flow.getProtocol(), 6);
            AiPredictionRequest aiReq = new AiPredictionRequest(
                    flow.getPacketCount(), flow.getByteCount(), flow.getDuration(),
                    protocolNum, flow.getDestinationPort(), flow.getConnectionsPerSecond());
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
