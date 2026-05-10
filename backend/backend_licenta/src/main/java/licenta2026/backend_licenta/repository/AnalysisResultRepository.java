package licenta2026.backend_licenta.repository;

import licenta2026.backend_licenta.entity.AnalysisResult;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.time.LocalDateTime;
import java.util.List;

@Repository
public interface AnalysisResultRepository extends JpaRepository<AnalysisResult, Long> {
    List<AnalysisResult> findByAnomalyTrueOrderByAnalyzedAtDesc();
    List<AnalysisResult> findByAnalyzedAtAfterOrderByAnalyzedAtDesc(LocalDateTime since);
    long countByAnomalyTrue();
    long countByAnalyzedAtAfter(LocalDateTime since);
}
