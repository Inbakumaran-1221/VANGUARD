"""
End-to-end audit pipeline orchestration.
Coordinates data loading, clustering, scoring, and report generation.
"""

import logging
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple

from src.models import (
    TransitStop, Grievance, AccessibilityScore, GrievanceCluster, AuditReport, PriorityLevel
)
from src.data_loaders import load_data, CSVDataLoader, MockDataLoader
from src.clustering import cluster_grievances
from src.gap_scorer import score_accessibility_gaps
from src.utils import get_logger, generate_report_id, calculate_coverage_percent, get_priority_level
from src.evaluation import evaluate_gap_detection_precision
from src.image_processor import PreparedImage
from src.object_detection import AccessibilityObjectDetector, ImageDetectionResult

logger = get_logger(__name__)


class AuditPipeline:
    """End-to-end accessibility audit pipeline."""
    
    def __init__(self, city_name: str = "Sample City"):
        """
        Initialize audit pipeline.
        
        Args:
            city_name: Name of city being audited
        """
        self.city_name = city_name
        self.stops: List[TransitStop] = []
        self.grievances: List[Grievance] = []
        self.clusters: List[GrievanceCluster] = []
        self.scores: List[AccessibilityScore] = []
        self.image_findings: List[ImageDetectionResult] = []
        self.evaluation_metrics: Dict[str, float] = {}
        self.data_source: str = "csv"
        self.image_detector_mode: Optional[str] = None
        self.execution_time = 0.0
    
    def load_data(
        self,
        stops_source: Optional[str] = None,
        grievances_source: Optional[str] = None,
        gtfs_source: Optional[str] = None,
        use_mock: bool = False
    ) -> Tuple[List[TransitStop], List[Grievance]]:
        """
        Load transit and grievance data.
        
        Args:
            stops_source: Path to stops CSV or 'mock'
            grievances_source: Path to grievances CSV or 'mock'
            use_mock: Force use of mock data
        
        Returns:
            Tuple of (stops, grievances)
        """
        logger.info(f"Loading data for {self.city_name}...")

        if use_mock:
            self.data_source = "mock"
        elif gtfs_source:
            self.data_source = "gtfs"
        else:
            self.data_source = "csv"
        
        self.stops, self.grievances = load_data(
            stops_source=stops_source,
            grievances_source=grievances_source,
            gtfs_source=gtfs_source,
            use_mock=use_mock
        )
        
        logger.info(f"Loaded {len(self.stops)} stops and {len(self.grievances)} grievances")
        return self.stops, self.grievances
    
    def cluster_grievances(self, method: str = 'tfidf') -> List[GrievanceCluster]:
        """
        Cluster grievances into themes.
        
        Args:
            method: 'tfidf' or 'embedding'
        
        Returns:
            List of GrievanceCluster objects
        """
        if len(self.grievances) == 0:
            logger.warning("No grievances to cluster")
            self.clusters = []
            return self.clusters
        
        logger.info("Clustering grievances...")
        self.clusters = cluster_grievances(self.grievances, method=method, label_clusters=True)
        
        logger.info(f"Created {len(self.clusters)} clusters")
        for cluster in self.clusters:
            logger.debug(f"  {cluster.theme}: {cluster.count} grievances, silhouette={cluster.silhouette_score:.3f}")
        
        return self.clusters
    
    def score_gaps(self) -> List[AccessibilityScore]:
        """
        Score accessibility gaps for all stops.
        
        Returns:
            List of AccessibilityScore objects (sorted by gap_score descending)
        """
        if len(self.stops) == 0:
            logger.warning("No stops to score")
            self.scores = []
            return self.scores
        
        logger.info("Scoring accessibility gaps...")
        self.scores = score_accessibility_gaps(self.stops, self.grievances, self.clusters)
        
        return self.scores

    def analyze_images(
        self,
        image_paths: Optional[List[str]] = None,
        image_stop_ids: Optional[List[Optional[str]]] = None,
        detector_model_path: Optional[str] = None,
        detector_mode: str = "auto",
    ) -> List[ImageDetectionResult]:
        """Analyze optional accessibility images and cache the results."""
        self.image_findings = []

        if not image_paths:
            return self.image_findings

        detector = AccessibilityObjectDetector(model_path=detector_model_path, detector_mode=detector_mode)
        self.image_detector_mode = detector.mode
        for index, image_path in enumerate(image_paths):
            if not image_path:
                continue

            prepared = PreparedImage(
                image_id=Path(image_path).stem,
                original_name=Path(image_path).name,
                stored_path=image_path,
                stop_id=image_stop_ids[index] if image_stop_ids and index < len(image_stop_ids) else None,
                width=0,
                height=0,
                format=Path(image_path).suffix.lstrip(".") or "unknown",
                size_bytes=Path(image_path).stat().st_size if Path(image_path).exists() else 0,
            )
            self.image_findings.append(detector.predict(prepared))

        return self.image_findings

    def apply_image_signals(self) -> List[AccessibilityScore]:
        """Adjust scores using image-derived accessibility signals."""
        if not self.scores or not self.image_findings:
            return self.scores

        positive_weights = {
            "ramp": -12,
            "handrail": -6,
            "tactile_paving": -8,
            "curb_cut": -8,
            "low_floor_bus": -10,
            "priority_seating": -4,
        }
        negative_weights = {
            "obstruction": 14,
            "blocked_entrance": 16,
            "poor_lighting": 8,
            "broken_path": 10,
            "crowding": 8,
        }

        scores_by_stop = {score.stop_id: score for score in self.scores}
        for finding in self.image_findings:
            if not finding.stop_id or finding.stop_id not in scores_by_stop:
                continue

            score = scores_by_stop[finding.stop_id]
            adjustment = 0.0
            image_findings = []

            for detection in finding.detections:
                label = detection.label.lower()
                if label in positive_weights:
                    adjustment += positive_weights[label] * detection.confidence
                    image_findings.append(f"{label} present ({detection.confidence:.2f})")
                elif label in negative_weights:
                    adjustment += negative_weights[label] * detection.confidence
                    image_findings.append(f"{label} detected ({detection.confidence:.2f})")

            if image_findings:
                score.image_findings = sorted(set(score.image_findings + image_findings))
                score.image_detection_confidence = round(
                    sum(d.confidence for d in finding.detections) / len(finding.detections), 3
                )

            if adjustment:
                score.gap_score = max(0, min(100, score.gap_score + adjustment))
                score.priority_level = PriorityLevel(get_priority_level(score.gap_score))
                score.recommendations = list(
                    dict.fromkeys(
                        score.recommendations
                        + ["Review image evidence for the stop and verify accessibility conditions on site."]
                    )
                )

        self.scores.sort(key=lambda s: s.gap_score, reverse=True)
        return self.scores

    def evaluate_predictions(self, ground_truth_source: Optional[str] = None) -> Dict[str, float]:
        """Evaluate gap detection precision/recall/F1 using optional ground truth CSV."""
        self.evaluation_metrics = {}
        if not ground_truth_source:
            return self.evaluation_metrics

        self.evaluation_metrics = evaluate_gap_detection_precision(self.scores, ground_truth_source)
        return self.evaluation_metrics
    
    def generate_report(self) -> AuditReport:
        """
        Generate comprehensive audit report.
        
        Returns:
            AuditReport object
        """
        logger.info("Generating audit report...")
        
        # Calculate statistics
        total_stops = len(self.stops)
        audited_stops = len(self.scores)
        coverage_percent = calculate_coverage_percent(total_stops, audited_stops)
        
        # Gap score distribution
        gap_scores = [s.gap_score for s in self.scores]
        avg_gap_score = sum(gap_scores) / len(gap_scores) if gap_scores else 0
        
        # Count stops by priority
        from collections import Counter
        priority_counts = Counter(s.priority_level.value for s in self.scores)
        stops_by_priority = {
            "CRITICAL": priority_counts.get("CRITICAL", 0),
            "HIGH": priority_counts.get("HIGH", 0),
            "MEDIUM": priority_counts.get("MEDIUM", 0),
            "LOW": priority_counts.get("LOW", 0),
        }
        
        # Top 10 priority stops
        top_priority_stops = self.scores[:10]
        
        # Key findings
        key_findings = []
        if stops_by_priority["CRITICAL"] > 0:
            key_findings.append(
                f"{stops_by_priority['CRITICAL']} stops have CRITICAL accessibility gaps requiring immediate intervention"
            )
        if avg_gap_score > 50:
            key_findings.append(
                f"Average accessibility gap score is {avg_gap_score:.1f}/100, indicating significant citywide accessibility challenges"
            )
        if len(self.clusters) > 0:
            top_theme = max(self.clusters, key=lambda c: c.count)
            key_findings.append(
                f"Most common accessibility issue: '{top_theme.theme}' ({top_theme.count} complaints)"
            )
        if self.image_findings:
            key_findings.append(
                f"Analyzed {len(self.image_findings)} accessibility images for visual evidence of ramps, obstructions, and related features"
            )
        if self.evaluation_metrics:
            key_findings.append(
                f"Gap detection precision={self.evaluation_metrics.get('precision', 0):.2f}, recall={self.evaluation_metrics.get('recall', 0):.2f}, F1={self.evaluation_metrics.get('f1_score', 0):.2f}"
            )
        
        # Strategic recommendations
        recommendations = [
            "Prioritize remediation of stops with CRITICAL gaps",
            "Focus on top accessibility issues identified in grievance analysis",
            "Implement staff training and 24/7 assistance programs at key hubs",
            "Establish feedback mechanism to track improvement progress",
        ]
        
        report = AuditReport(
            report_id=generate_report_id(),
            city=self.city_name,
            total_stops_audited=audited_stops,
            total_grievances_analyzed=len(self.grievances),
            coverage_percent=coverage_percent,
            stops_by_priority=stops_by_priority,
            avg_gap_score=round(avg_gap_score, 2),
            grievance_themes=self.clusters,
            top_priority_stops=top_priority_stops,
            data_source=self.data_source,
            image_analysis_enabled=bool(self.image_findings),
            image_count=len(self.image_findings),
            image_detector_mode=self.image_detector_mode,
            image_findings_summary=[finding.to_summary(finding.source_path) for finding in self.image_findings],
            evaluation_metrics=self.evaluation_metrics,
            key_findings=key_findings,
            recommendations=recommendations,
            generation_time_seconds=round(self.execution_time, 2),
        )
        
        logger.info(f"Report generated: {report.report_id}")
        return report
    
    def run(
        self,
        stops_source: Optional[str] = None,
        grievances_source: Optional[str] = None,
        gtfs_source: Optional[str] = None,
        ground_truth_source: Optional[str] = None,
        use_mock: bool = False,
        clustering_method: str = 'tfidf',
        image_paths: Optional[List[str]] = None,
        image_stop_ids: Optional[List[Optional[str]]] = None,
        detector_model_path: Optional[str] = None,
        detector_mode: str = "auto",
    ) -> AuditReport:
        """
        Run complete audit pipeline.
        
        Args:
            stops_source: Path to stops CSV or 'mock'
            grievances_source: Path to grievances CSV or 'mock'
            use_mock: Force use of mock data
            clustering_method: 'tfidf' or 'embedding'
        
        Returns:
            AuditReport object
        """
        start_time = time.time()
        logger.info("=" * 80)
        logger.info(f"Starting accessibility audit pipeline for {self.city_name}")
        logger.info("=" * 80)
        
        try:
            # Step 1: Load data
            self.load_data(stops_source, grievances_source, gtfs_source, use_mock)
            
            # Step 2: Cluster grievances
            self.cluster_grievances(method=clustering_method)
            
            # Step 3: Score gaps
            self.score_gaps()

            # Step 3b: Optional image analysis and score adjustment
            self.analyze_images(
                image_paths=image_paths,
                image_stop_ids=image_stop_ids,
                detector_model_path=detector_model_path,
                detector_mode=detector_mode,
            )
            self.apply_image_signals()

            # Step 3c: Optional evaluation against ground truth
            self.evaluate_predictions(ground_truth_source=ground_truth_source)
            
            # Step 4: Generate report
            report = self.generate_report()
            
            self.execution_time = time.time() - start_time
            report.generation_time_seconds = round(self.execution_time, 2)
            
            logger.info("=" * 80)
            logger.info(f"Audit pipeline completed in {self.execution_time:.2f}s")
            logger.info("=" * 80)
            
            return report
        
        except Exception as e:
            logger.error(f"Pipeline failed: {e}", exc_info=True)
            self.execution_time = time.time() - start_time
            raise


def run_audit_pipeline(
    city_name: str = "Sample City",
    stops_source: Optional[str] = None,
    grievances_source: Optional[str] = None,
    gtfs_source: Optional[str] = None,
    ground_truth_source: Optional[str] = None,
    use_mock: bool = False,
    clustering_method: str = 'tfidf',
    image_paths: Optional[List[str]] = None,
    image_stop_ids: Optional[List[Optional[str]]] = None,
    detector_model_path: Optional[str] = None,
    detector_mode: str = "auto",
) -> Tuple[AuditReport, AuditPipeline]:
    """
    Convenience function to run complete audit pipeline.
    
    Args:
        city_name: City name
        stops_source: Path to stops CSV
        grievances_source: Path to grievances CSV
        use_mock: Use mock data
        clustering_method: Clustering method
    
    Returns:
        Tuple of (report, pipeline_instance)
    """
    pipeline = AuditPipeline(city_name=city_name)
    report = pipeline.run(
        stops_source=stops_source,
        grievances_source=grievances_source,
        gtfs_source=gtfs_source,
        ground_truth_source=ground_truth_source,
        use_mock=use_mock,
        clustering_method=clustering_method
        ,
        image_paths=image_paths,
        image_stop_ids=image_stop_ids,
        detector_model_path=detector_model_path,
        detector_mode=detector_mode,
    )
    return report, pipeline
