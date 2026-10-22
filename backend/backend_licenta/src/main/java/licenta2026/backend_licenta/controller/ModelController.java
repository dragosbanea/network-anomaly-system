package licenta2026.backend_licenta.controller;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.client.RestTemplate;

import java.util.Map;

@RestController
@RequestMapping("/api/model")
public class ModelController {

    private final RestTemplate restTemplate;

    @Value("${ai.service.url}")
    private String aiServiceUrl;

    public ModelController(RestTemplate restTemplate) {
        this.restTemplate = restTemplate;
    }

    @GetMapping("/metrics")
    public ResponseEntity<?> getMetrics() {
        try {
            Object metrics = restTemplate.getForObject(aiServiceUrl + "/metrics", Object.class);
            return ResponseEntity.ok(metrics);
        } catch (Exception e) {
            return ResponseEntity.status(503)
                    .body(Map.of("error", "AI service unavailable or metrics not generated yet. " +
                            "Run: python model.py --compare"));
        }
    }

    @GetMapping("/info")
    public ResponseEntity<?> getModelInfo() {
        try {
            Object info = restTemplate.getForObject(aiServiceUrl + "/model/info", Object.class);
            return ResponseEntity.ok(info);
        } catch (Exception e) {
            return ResponseEntity.status(503)
                    .body(Map.of("error", "AI service unavailable"));
        }
    }
}
