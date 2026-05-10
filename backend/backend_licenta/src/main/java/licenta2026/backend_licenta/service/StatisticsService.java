package licenta2026.backend_licenta.service;

import licenta2026.backend_licenta.repository.AlertRepository;
import licenta2026.backend_licenta.repository.AnalysisResultRepository;
import licenta2026.backend_licenta.repository.TrafficFlowRepository;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.HashMap;
import java.util.Map;

@Service
public class StatisticsService {

    private final TrafficFlowRepository flowRepository;
    private final AnalysisResultRepository resultRepository;
    private final AlertRepository alertRepository;

    public StatisticsService(TrafficFlowRepository flowRepository,
                              AnalysisResultRepository resultRepository,
                              AlertRepository alertRepository) {
        this.flowRepository = flowRepository;
        this.resultRepository = resultRepository;
        this.alertRepository = alertRepository;
    }

    public Map<String, Object> getDashboardStats() {
        Map<String, Object> stats = new HashMap<>();
        stats.put("totalFlows", flowRepository.count());
        stats.put("totalAnalyzed", resultRepository.count());
        stats.put("totalAnomalies", resultRepository.countByAnomalyTrue());
        stats.put("unresolvedAlerts", alertRepository.countByResolvedFalse());
        stats.put("criticalAlerts", alertRepository.countBySeverity("CRITICAL"));
        stats.put("highAlerts", alertRepository.countBySeverity("HIGH"));
        stats.put("mediumAlerts", alertRepository.countBySeverity("MEDIUM"));
        stats.put("lowAlerts", alertRepository.countBySeverity("LOW"));

        long total = resultRepository.count();
        long anomalies = resultRepository.countByAnomalyTrue();
        stats.put("anomalyRate", total > 0 ? (double) anomalies / total * 100 : 0.0);
        return stats;
    }

    public Map<String, Object> getRecentStats(int minutes) {
        LocalDateTime since = LocalDateTime.now().minusMinutes(minutes);
        Map<String, Object> stats = new HashMap<>();
        stats.put("recentFlows", flowRepository.countByTimestampAfter(since));
        stats.put("recentAnalyzed", resultRepository.countByAnalyzedAtAfter(since));
        stats.put("recentAlerts", alertRepository.findByCreatedAtAfterOrderByCreatedAtDesc(since).size());
        return stats;
    }
}
