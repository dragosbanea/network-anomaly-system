package licenta2026.backend_licenta.controller;

import licenta2026.backend_licenta.entity.MonitoringSession;
import licenta2026.backend_licenta.service.MonitoringService;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/monitoring")
public class MonitoringController {

    private final MonitoringService monitoringService;

    public MonitoringController(MonitoringService monitoringService) {
        this.monitoringService = monitoringService;
    }

    @PostMapping("/start")
    public ResponseEntity<MonitoringSession> startSession(
            @RequestBody Map<String, String> body) {
        String iface = body.getOrDefault("networkInterface", "eth0");
        return ResponseEntity.ok(monitoringService.startSession(iface));
    }

    @PostMapping("/stop")
    public ResponseEntity<MonitoringSession> stopSession() {
        return monitoringService.stopSession()
                .map(ResponseEntity::ok)
                .orElse(ResponseEntity.notFound().build());
    }

    @GetMapping("/active")
    public ResponseEntity<MonitoringSession> getActiveSession() {
        return monitoringService.getActiveSession()
                .map(ResponseEntity::ok)
                .orElse(ResponseEntity.noContent().build());
    }

    @GetMapping("/sessions")
    public ResponseEntity<List<MonitoringSession>> getAllSessions() {
        return ResponseEntity.ok(monitoringService.getAllSessions());
    }
}
