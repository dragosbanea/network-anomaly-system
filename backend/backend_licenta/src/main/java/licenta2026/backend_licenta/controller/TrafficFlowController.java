package licenta2026.backend_licenta.controller;

import licenta2026.backend_licenta.dto.TrafficFlowRequest;
import licenta2026.backend_licenta.entity.AnalysisResult;
import licenta2026.backend_licenta.entity.TrafficFlow;
import licenta2026.backend_licenta.service.TrafficFlowService;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/traffic")
public class TrafficFlowController {

    private final TrafficFlowService trafficFlowService;

    public TrafficFlowController(TrafficFlowService trafficFlowService) {
        this.trafficFlowService = trafficFlowService;
    }

    @PostMapping("/analyze")
    public ResponseEntity<AnalysisResult> analyzeFlow(@RequestBody TrafficFlowRequest request) {
        return ResponseEntity.ok(trafficFlowService.analyzeFlow(request));
    }

    @GetMapping("/recent")
    public ResponseEntity<List<TrafficFlow>> getRecentFlows(
            @RequestParam(defaultValue = "10") int minutes) {
        return ResponseEntity.ok(trafficFlowService.getRecentFlows(minutes));
    }

    @GetMapping("/results")
    public ResponseEntity<List<AnalysisResult>> getAllResults() {
        return ResponseEntity.ok(trafficFlowService.getAllResults());
    }

    @GetMapping("/anomalies")
    public ResponseEntity<List<AnalysisResult>> getAnomalies() {
        return ResponseEntity.ok(trafficFlowService.getAnomalyResults());
    }
}
