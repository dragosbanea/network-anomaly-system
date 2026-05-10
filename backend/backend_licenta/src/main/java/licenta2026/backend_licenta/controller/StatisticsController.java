package licenta2026.backend_licenta.controller;

import licenta2026.backend_licenta.service.StatisticsService;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

@RestController
@RequestMapping("/api/statistics")
public class StatisticsController {

    private final StatisticsService statisticsService;

    public StatisticsController(StatisticsService statisticsService) {
        this.statisticsService = statisticsService;
    }

    @GetMapping("/dashboard")
    public ResponseEntity<Map<String, Object>> getDashboardStats() {
        return ResponseEntity.ok(statisticsService.getDashboardStats());
    }

    @GetMapping("/recent")
    public ResponseEntity<Map<String, Object>> getRecentStats(
            @RequestParam(defaultValue = "60") int minutes) {
        return ResponseEntity.ok(statisticsService.getRecentStats(minutes));
    }
}
