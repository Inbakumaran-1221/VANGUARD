"""
Tests for the complete audit pipeline.
"""

import pytest
import tempfile
from pathlib import Path
from PIL import Image
from src.pipeline import run_audit_pipeline, AuditPipeline
from src.data_generator import generate_synthetic_stops, generate_synthetic_grievances, save_stops_to_csv, save_grievances_to_csv


@pytest.fixture
def temp_csv_files():
    """Create temporary CSV files for testing."""
    temp_dir = Path(tempfile.mkdtemp())
    
    # Generate and save demo data
    stops = generate_synthetic_stops(count=20)
    grievances = generate_synthetic_grievances(stops, count=100)
    
    stops_path = temp_dir / "test_stops.csv"
    grievances_path = temp_dir / "test_grievances.csv"
    
    save_stops_to_csv(stops, str(stops_path))
    save_grievances_to_csv(grievances, str(grievances_path))
    
    yield stops_path, grievances_path
    
    # Cleanup
    import shutil
    shutil.rmtree(temp_dir)


def test_pipeline_with_mock_data():
    """Test complete pipeline with mock data."""
    report, pipeline = run_audit_pipeline(
        city_name="Test City",
        use_mock=True,
        clustering_method='tfidf'
    )
    
    # Check report was generated
    assert report is not None
    assert report.report_id.startswith("AUDIT_")
    assert report.city == "Test City"
    
    # Check pipeline results
    assert len(pipeline.stops) > 0
    assert len(pipeline.grievances) > 0
    assert len(pipeline.clusters) > 0
    assert len(pipeline.scores) > 0
    
    # Check metrics
    assert report.total_stops_audited > 0
    assert report.total_grievances_analyzed > 0
    assert 0 <= report.avg_gap_score <= 100
    assert 0 <= report.coverage_percent <= 100


def test_pipeline_with_csv_files(temp_csv_files):
    """Test pipeline with CSV file inputs."""
    stops_path, grievances_path = temp_csv_files
    
    report, pipeline = run_audit_pipeline(
        city_name="CSV Test City",
        stops_source=str(stops_path),
        grievances_source=str(grievances_path),
        clustering_method='tfidf'
    )
    
    assert report is not None
    assert len(pipeline.stops) == 20
    # The synthetic generator may produce fewer grievances than requested based on stop accessibility.
    assert len(pipeline.grievances) > 0
    assert len(pipeline.grievances) <= 100


def test_pipeline_priority_distribution():
    """Test that stops are correctly prioritized."""
    report, pipeline = run_audit_pipeline(
        city_name="Priority Test",
        use_mock=True,
        clustering_method='tfidf'
    )
    
    # Check priority distribution
    priorities = report.stops_by_priority
    total = sum(priorities.values())
    
    assert total == report.total_stops_audited
    assert all(count >= 0 for count in priorities.values())


def test_pipeline_top_priority_stops():
    """Test that top priority stops are correctly identified."""
    report, pipeline = run_audit_pipeline(
        city_name="Top Priority Test",
        use_mock=True,
        clustering_method='tfidf'
    )
    
    # Check top priority stops
    assert len(report.top_priority_stops) > 0
    assert len(report.top_priority_stops) <= 10
    
    # Should be sorted by gap score descending
    scores = [s.gap_score for s in report.top_priority_stops]
    assert scores == sorted(scores, reverse=True)


def test_pipeline_clustering_quality():
    """Test that clustering produces reasonable results."""
    report, pipeline = run_audit_pipeline(
        city_name="Clustering Test",
        use_mock=True,
        clustering_method='tfidf'
    )
    
    # Check clusters
    assert len(pipeline.clusters) > 0
    
    # Each cluster should have grievances
    for cluster in pipeline.clusters:
        assert cluster.count > 0
        assert len(cluster.grievance_ids) == cluster.count
        
    # Total grievances should match
    total_clustered = sum(c.count for c in pipeline.clusters)
    assert total_clustered == len(pipeline.grievances)


def test_pipeline_recommendations():
    """Test that recommendations are generated."""
    report, pipeline = run_audit_pipeline(
        city_name="Recommendations Test",
        use_mock=True,
        clustering_method='tfidf'
    )
    
    # Check top priority stops have recommendations
    for stop in report.top_priority_stops[:5]:
        if stop.gap_score > 0:
            assert len(stop.recommendations) > 0
            assert stop.remediation_cost_estimate is not None


def test_pipeline_execution_time():
    """Test that pipeline executes within reasonable time."""
    import time
    
    start = time.time()
    report, pipeline = run_audit_pipeline(
        city_name="Performance Test",
        use_mock=True,
        clustering_method='tfidf'
    )
    elapsed = time.time() - start
    
    # Should complete in reasonable time
    assert elapsed < 60  # Less than 60 seconds
    assert report.generation_time_seconds > 0


def test_pipeline_handles_no_grievances():
    """Test pipeline with no grievances."""
    pipeline = AuditPipeline(city_name="No Grievances Test")
    
    # Load only stops, no grievances
    stops = generate_synthetic_stops(count=10)
    pipeline.stops = stops
    pipeline.grievances = []
    
    # Cluster (should handle empty grievances)
    clusters = pipeline.cluster_grievances()
    assert len(clusters) == 0
    
    # Score (should still work)
    scores = pipeline.score_gaps()
    assert len(scores) == len(stops)


def test_pipeline_edge_cases():
    """Test pipeline with edge case data."""
    # Very small dataset
    report, pipeline = run_audit_pipeline(
        city_name="Edge Case Test",
        use_mock=True,
        clustering_method='tfidf'
    )
    
    # Should still produce valid output
    assert report is not None
    assert pipeline is not None


def test_pipeline_with_image_inputs():
    """Test pipeline with image inputs mapped to a stop."""
    temp_dir = Path(tempfile.mkdtemp())
    image_path = temp_dir / "STOP_0001_ramp.jpg"

    image = Image.new("RGB", (640, 480), color=(180, 180, 180))
    image.save(image_path)

    report, pipeline = run_audit_pipeline(
        city_name="Image Test City",
        use_mock=True,
        clustering_method='tfidf',
        image_paths=[str(image_path)],
        image_stop_ids=["STOP_0001"],
    )

    assert report is not None
    assert report.image_analysis_enabled is True
    assert report.image_count == 1
    assert len(pipeline.image_findings) == 1
    assert pipeline.image_findings[0].stop_id == "STOP_0001"
    assert report.image_findings_summary[0].stop_id == "STOP_0001"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])