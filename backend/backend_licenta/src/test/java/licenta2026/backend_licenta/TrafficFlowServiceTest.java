package licenta2026.backend_licenta;

import licenta2026.backend_licenta.dto.AiPredictionResponse;
import licenta2026.backend_licenta.dto.TrafficFlowRequest;
import licenta2026.backend_licenta.entity.AnalysisResult;
import licenta2026.backend_licenta.entity.TrafficFlow;
import licenta2026.backend_licenta.repository.AnalysisResultRepository;
import licenta2026.backend_licenta.repository.MonitoringSessionRepository;
import licenta2026.backend_licenta.repository.TrafficFlowRepository;
import licenta2026.backend_licenta.service.AlertService;
import licenta2026.backend_licenta.service.MonitoringService;
import licenta2026.backend_licenta.service.TrafficFlowService;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.test.util.ReflectionTestUtils;
import org.springframework.web.client.RestClientException;
import org.springframework.web.client.RestTemplate;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatNoException;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
@DisplayName("TrafficFlowService — pipeline de analiză")
class TrafficFlowServiceTest {

    @Mock private TrafficFlowRepository flowRepository;
    @Mock private AnalysisResultRepository resultRepository;
    @Mock private MonitoringSessionRepository sessionRepository;
    @Mock private AlertService alertService;
    @Mock private MonitoringService monitoringService;
    @Mock private RestTemplate restTemplate;

    @InjectMocks
    private TrafficFlowService service;

    @BeforeEach
    void setUp() {
        ReflectionTestUtils.setField(service, "aiServiceUrl", "http://localhost:5000");
        when(flowRepository.save(any(TrafficFlow.class))).thenAnswer(i -> i.getArgument(0));
        when(resultRepository.save(any(AnalysisResult.class))).thenAnswer(i -> i.getArgument(0));
    }

    private TrafficFlowRequest makeRequest(Long sessionId) {
        TrafficFlowRequest req = new TrafficFlowRequest();
        req.setSourceIp("10.0.0.1");
        req.setDestinationIp("192.168.1.1");
        req.setSourcePort(50000);
        req.setDestinationPort(80);
        req.setProtocol("TCP");
        req.setTotalFwdPackets(10);
        req.setTotalBwdPackets(8);
        req.setTotalFwdBytes(3000);
        req.setTotalBwdBytes(12000);
        req.setFlowDuration(2.0);
        req.setFlowBytesPerSec(7500.0);
        req.setFlowPacketsPerSec(9.0);
        req.setSynFlagCount(1);
        req.setRstFlagCount(0);
        req.setAvgPacketSize(833.0);
        req.setSessionId(sessionId);
        return req;
    }

    private AiPredictionResponse makePrediction(boolean anomaly, double score, String label) {
        AiPredictionResponse r = new AiPredictionResponse();
        r.setAnomaly(anomaly);
        r.setAnomalyScore(score);
        r.setConfidence(anomaly ? score : 1 - score);
        r.setLabel(label);
        return r;
    }

    // ------------------------------------------------------------------ //
    // 1. Flux benign                                                       //
    // ------------------------------------------------------------------ //
    @Nested
    @DisplayName("Flux benign")
    class FluxBenign {

        @BeforeEach
        void stubAi() {
            when(restTemplate.postForObject(anyString(), any(), eq(AiPredictionResponse.class)))
                    .thenReturn(makePrediction(false, 0.05, "BENIGN"));
        }

        @Test
        @DisplayName("Rezultatul are anomaly=false")
        void rezultatBenign() {
            AnalysisResult result = service.analyzeFlow(makeRequest(null));
            assertThat(result.isAnomaly()).isFalse();
        }

        @Test
        @DisplayName("Nicio alertă nu este creată")
        void niciOAlerta() {
            service.analyzeFlow(makeRequest(null));
            verify(alertService, never()).createAlert(any(), anyDouble(), anyString());
        }

        @Test
        @DisplayName("Fluxul este persistat în repository")
        void fluxPersitat() {
            service.analyzeFlow(makeRequest(null));
            verify(flowRepository, times(1)).save(any(TrafficFlow.class));
        }

        @Test
        @DisplayName("Rezultatul analizei este persistat")
        void rezultatPersitat() {
            service.analyzeFlow(makeRequest(null));
            verify(resultRepository, times(1)).save(any(AnalysisResult.class));
        }
    }

    // ------------------------------------------------------------------ //
    // 2. Flux anomalie                                                     //
    // ------------------------------------------------------------------ //
    @Nested
    @DisplayName("Flux anomalie")
    class FluxAnomalie {

        @BeforeEach
        void stubAi() {
            when(restTemplate.postForObject(anyString(), any(), eq(AiPredictionResponse.class)))
                    .thenReturn(makePrediction(true, 0.92, "DDoS"));
        }

        @Test
        @DisplayName("Rezultatul are anomaly=true")
        void rezultatAnomalie() {
            AnalysisResult result = service.analyzeFlow(makeRequest(null));
            assertThat(result.isAnomaly()).isTrue();
        }

        @Test
        @DisplayName("O alertă este creată")
        void alertaCreata() {
            service.analyzeFlow(makeRequest(null));
            verify(alertService, times(1)).createAlert(any(TrafficFlow.class), eq(0.92), eq("DDoS"));
        }

        @Test
        @DisplayName("Scorul de anomalie este transmis corect")
        void scorCorect() {
            AnalysisResult result = service.analyzeFlow(makeRequest(null));
            assertThat(result.getAnomalyScore()).isEqualTo(0.92);
        }

        @Test
        @DisplayName("Eticheta ML este salvată în detalii")
        void etichetaSalvata() {
            AnalysisResult result = service.analyzeFlow(makeRequest(null));
            assertThat(result.getDetails()).isEqualTo("DDoS");
        }
    }

    // ------------------------------------------------------------------ //
    // 3. Integrarea cu MonitoringService                                  //
    // ------------------------------------------------------------------ //
    @Nested
    @DisplayName("Integrare MonitoringService")
    class IntegrareMonitoring {

        @Test
        @DisplayName("Fără sessionId — monitoringService nu este apelat")
        void faraSessionFaraMonitoring() {
            when(restTemplate.postForObject(anyString(), any(), eq(AiPredictionResponse.class)))
                    .thenReturn(makePrediction(false, 0.1, "BENIGN"));
            service.analyzeFlow(makeRequest(null));
            verify(monitoringService, never()).incrementFlowCount(any());
        }

        @Test
        @DisplayName("Cu sessionId — incrementFlowCount este apelat")
        void cuSessionIncrementFlow() {
            when(restTemplate.postForObject(anyString(), any(), eq(AiPredictionResponse.class)))
                    .thenReturn(makePrediction(false, 0.1, "BENIGN"));
            service.analyzeFlow(makeRequest(1L));
            verify(monitoringService, times(1)).incrementFlowCount(1L);
        }

        @Test
        @DisplayName("Anomalie cu sessionId — incrementAnomalyCount este apelat")
        void anomalieCuSessionIncrementAnomaly() {
            when(restTemplate.postForObject(anyString(), any(), eq(AiPredictionResponse.class)))
                    .thenReturn(makePrediction(true, 0.88, "PortScan"));
            service.analyzeFlow(makeRequest(1L));
            verify(monitoringService, times(1)).incrementAnomalyCount(1L);
        }

        @Test
        @DisplayName("Flux benign cu sessionId — incrementAnomalyCount nu este apelat")
        void benignFaraIncrementAnomaly() {
            when(restTemplate.postForObject(anyString(), any(), eq(AiPredictionResponse.class)))
                    .thenReturn(makePrediction(false, 0.05, "BENIGN"));
            service.analyzeFlow(makeRequest(1L));
            verify(monitoringService, never()).incrementAnomalyCount(any());
        }
    }

    // ------------------------------------------------------------------ //
    // 4. Reziliență la căderea serviciului AI                             //
    // ------------------------------------------------------------------ //
    @Nested
    @DisplayName("Reziliență serviciu AI")
    class RezilientaAI {

        @Test
        @DisplayName("Serviciu AI indisponibil — nicio excepție propagată")
        void serviciiAiCazutFaraExceptie() {
            when(restTemplate.postForObject(anyString(), any(), eq(AiPredictionResponse.class)))
                    .thenThrow(new RestClientException("Connection refused"));
            assertThatNoException().isThrownBy(() -> service.analyzeFlow(makeRequest(null)));
        }

        @Test
        @DisplayName("Serviciu AI indisponibil — fallback anomaly=false")
        void serviciiAiCazutFallbackBenign() {
            when(restTemplate.postForObject(anyString(), any(), eq(AiPredictionResponse.class)))
                    .thenThrow(new RestClientException("Connection refused"));
            AnalysisResult result = service.analyzeFlow(makeRequest(null));
            assertThat(result.isAnomaly()).isFalse();
        }

        @Test
        @DisplayName("Serviciu AI indisponibil — nicio alertă generată")
        void serviciiAiCazutNiciOAlerta() {
            when(restTemplate.postForObject(anyString(), any(), eq(AiPredictionResponse.class)))
                    .thenThrow(new RestClientException("Connection refused"));
            service.analyzeFlow(makeRequest(null));
            verify(alertService, never()).createAlert(any(), anyDouble(), anyString());
        }
    }
}
