package licenta2026.backend_licenta;

import licenta2026.backend_licenta.entity.Alert;
import licenta2026.backend_licenta.entity.TrafficFlow;
import licenta2026.backend_licenta.repository.AlertRepository;
import licenta2026.backend_licenta.service.AlertService;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.messaging.simp.SimpMessagingTemplate;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
@DisplayName("AlertService — clasificare alerte")
class AlertServiceTest {

    @Mock
    private AlertRepository alertRepository;

    @Mock
    private SimpMessagingTemplate messagingTemplate;

    @InjectMocks
    private AlertService alertService;

    private TrafficFlow makeFlow(String srcIp, String dstIp, int dstPort,
                                  String protocol, double packetsPerSec,
                                  long fwdBytes, long bwdBytes, double duration) {
        TrafficFlow f = new TrafficFlow();
        f.setSourceIp(srcIp);
        f.setDestinationIp(dstIp);
        f.setSourcePort(50000);
        f.setDestinationPort(dstPort);
        f.setProtocol(protocol);
        f.setFlowPacketsPerSec(packetsPerSec);
        f.setTotalFwdBytes(fwdBytes);
        f.setTotalBwdBytes(bwdBytes);
        f.setFlowDuration(duration);
        f.setFlowBytesPerSec((fwdBytes + bwdBytes) / Math.max(duration, 0.001));
        return f;
    }

    @BeforeEach
    void setUp() {
        when(alertRepository.save(any(Alert.class))).thenAnswer(inv -> inv.getArgument(0));
    }

    // ------------------------------------------------------------------ //
    // 1. Clasificarea severității pe baza scorului de anomalie            //
    // ------------------------------------------------------------------ //
    @Nested
    @DisplayName("Clasificarea severității")
    class SeverityClassification {

        private Alert createAlertWithScore(double score) {
            TrafficFlow flow = makeFlow("1.1.1.1", "2.2.2.2", 80, "TCP", 5.0, 1000, 500, 1.0);
            return alertService.createAlert(flow, score, "BENIGN");
        }

        @Test
        @DisplayName("Scor > 0.8 → CRITICAL")
        void scoreCritical() {
            Alert a = createAlertWithScore(0.95);
            assertThat(a.getSeverity()).isEqualTo("CRITICAL");
        }

        @Test
        @DisplayName("Scor 0.61–0.80 → HIGH")
        void scoreHigh() {
            Alert a = createAlertWithScore(0.75);
            assertThat(a.getSeverity()).isEqualTo("HIGH");
        }

        @Test
        @DisplayName("Scor 0.41–0.60 → MEDIUM")
        void scoreMedium() {
            Alert a = createAlertWithScore(0.50);
            assertThat(a.getSeverity()).isEqualTo("MEDIUM");
        }

        @Test
        @DisplayName("Scor ≤ 0.40 → LOW")
        void scoreLow() {
            Alert a = createAlertWithScore(0.30);
            assertThat(a.getSeverity()).isEqualTo("LOW");
        }

        @Test
        @DisplayName("Pragul exact 0.8 → HIGH")
        void scoreBoundary08() {
            Alert a = createAlertWithScore(0.80);
            assertThat(a.getSeverity()).isEqualTo("HIGH");
        }
    }

    // ------------------------------------------------------------------ //
    // 2. Clasificarea tipului de atac din eticheta ML                     //
    // ------------------------------------------------------------------ //
    @Nested
    @DisplayName("Tipul alertei din eticheta ML")
    class AlertTypeFromMlLabel {

        private Alert createWithLabel(String mlLabel, int dstPort) {
            TrafficFlow flow = makeFlow("10.0.0.1", "192.168.1.1", dstPort, "TCP", 5.0, 1000, 500, 1.0);
            return alertService.createAlert(flow, 0.9, mlLabel);
        }

        @Test
        @DisplayName("Eticheta PortScan → PORT_SCAN")
        void portScanLabel() {
            assertThat(createWithLabel("PortScan", 445).getAlertType()).isEqualTo("PORT_SCAN");
        }

        @Test
        @DisplayName("Eticheta DDoS → DOS")
        void ddosLabel() {
            assertThat(createWithLabel("DDoS", 80).getAlertType()).isEqualTo("DOS");
        }

        @Test
        @DisplayName("Eticheta DoS Hulk → DOS")
        void dosHulkLabel() {
            assertThat(createWithLabel("DoS Hulk", 80).getAlertType()).isEqualTo("DOS");
        }

        @Test
        @DisplayName("Eticheta SSH-Patator → BRUTE_FORCE")
        void sshPatatorLabel() {
            assertThat(createWithLabel("SSH-Patator", 22).getAlertType()).isEqualTo("BRUTE_FORCE");
        }

        @Test
        @DisplayName("Eticheta FTP-Patator → BRUTE_FORCE")
        void ftpPatatorLabel() {
            assertThat(createWithLabel("FTP-Patator", 21).getAlertType()).isEqualTo("BRUTE_FORCE");
        }

        @Test
        @DisplayName("Eticheta Bot → BOT")
        void botLabel() {
            assertThat(createWithLabel("Bot", 443).getAlertType()).isEqualTo("BOT");
        }

        @Test
        @DisplayName("Eticheta Web Attack → WEB_ATTACK")
        void webAttackLabel() {
            assertThat(createWithLabel("Web Attack - XSS", 80).getAlertType()).isEqualTo("WEB_ATTACK");
        }
    }

    // ------------------------------------------------------------------ //
    // 3. Euristici de rezervă (eticheta ML lipsă sau BENIGN)             //
    // ------------------------------------------------------------------ //
    @Nested
    @DisplayName("Euristici de rezervă")
    class FallbackHeuristics {

        @Test
        @DisplayName("Rate mare de pachete → PORT_SCAN")
        void highPacketRateIsPortScan() {
            TrafficFlow flow = makeFlow("10.0.0.99", "192.168.1.1", 445, "TCP", 200.0, 100, 0, 0.1);
            Alert a = alertService.createAlert(flow, 0.7, "BENIGN");
            assertThat(a.getAlertType()).isEqualTo("PORT_SCAN");
        }

        @Test
        @DisplayName("Volum mare în timp scurt → DOS")
        void highVolumeShortTimeIsDos() {
            TrafficFlow flow = makeFlow("10.0.0.99", "192.168.1.1", 80, "TCP", 50.0, 2_000_000, 0, 1.0);
            Alert a = alertService.createAlert(flow, 0.7, "BENIGN");
            assertThat(a.getAlertType()).isEqualTo("DOS");
        }

        @Test
        @DisplayName("Port destinație 22 (SSH) → BRUTE_FORCE")
        void port22IsBruteForce() {
            TrafficFlow flow = makeFlow("10.0.0.99", "192.168.1.1", 22, "TCP", 3.0, 1000, 1000, 10.0);
            Alert a = alertService.createAlert(flow, 0.6, "BENIGN");
            assertThat(a.getAlertType()).isEqualTo("BRUTE_FORCE");
        }

        @Test
        @DisplayName("Port destinație 3389 (RDP) → BRUTE_FORCE")
        void port3389IsBruteForce() {
            TrafficFlow flow = makeFlow("10.0.0.99", "192.168.1.1", 3389, "TCP", 3.0, 1000, 1000, 10.0);
            Alert a = alertService.createAlert(flow, 0.6, "BENIGN");
            assertThat(a.getAlertType()).isEqualTo("BRUTE_FORCE");
        }
    }

    // ------------------------------------------------------------------ //
    // 4. Notificare WebSocket la crearea alertei                         //
    // ------------------------------------------------------------------ //
    @Nested
    @DisplayName("Notificare WebSocket")
    class WebSocketNotification {

        @Test
        @DisplayName("createAlert trimite mesaj pe /topic/alerts")
        void alertIsBroadcast() {
            TrafficFlow flow = makeFlow("10.0.0.1", "192.168.1.1", 80, "TCP", 5.0, 1000, 500, 1.0);
            alertService.createAlert(flow, 0.9, "DDoS");
            verify(messagingTemplate, times(1))
                    .convertAndSend(eq("/topic/alerts"), any(Alert.class));
        }

        @Test
        @DisplayName("createAlert salvează alerta în repository")
        void alertIsPersisted() {
            TrafficFlow flow = makeFlow("10.0.0.1", "192.168.1.1", 80, "TCP", 5.0, 1000, 500, 1.0);
            alertService.createAlert(flow, 0.9, "DDoS");
            verify(alertRepository, times(1)).save(any(Alert.class));
        }

        @Test
        @DisplayName("Alerta nou creată are resolved=false")
        void alertNotResolvedByDefault() {
            TrafficFlow flow = makeFlow("10.0.0.1", "192.168.1.1", 80, "TCP", 5.0, 1000, 500, 1.0);
            Alert a = alertService.createAlert(flow, 0.9, "DDoS");
            assertThat(a.isResolved()).isFalse();
        }

        @Test
        @DisplayName("Alerta conține IP-urile din flux")
        void alertContainsFlowIps() {
            TrafficFlow flow = makeFlow("10.0.0.55", "172.16.0.1", 443, "TCP", 5.0, 1000, 500, 1.0);
            Alert a = alertService.createAlert(flow, 0.85, "Bot");
            assertThat(a.getSourceIp()).isEqualTo("10.0.0.55");
            assertThat(a.getDestinationIp()).isEqualTo("172.16.0.1");
        }
    }
}
