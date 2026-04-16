"""
Tests for gap scoring module.
"""

import pytest
from src.models import TransitStop, Grievance, GrievanceCluster
from src.gap_scorer import GapScorer, score_accessibility_gaps
from src.utils import get_priority_level


@pytest.fixture
def sample_stop_accessible():
    """Fully accessible transit stop."""
    return TransitStop(
        id="STOP_001",
        name="Accessible Stop",
        latitude=40.7128,
        longitude=-74.0060,
        stop_type="bus_stop",
        has_ramp=True,
        has_audio_signals=True,
        has_tactile_pavement=True,
        has_seating=True,
        has_lighting=True,
        has_staff_assistance=True,
        has_restroom=True,
        has_information_board=True,
        accessible_entrance=True,
        level_platform=True,
    )


@pytest.fixture
def sample_stop_inaccessible():
    """Completely inaccessible transit stop."""
    return TransitStop(
        id="STOP_002",
        name="Inaccessible Stop",
        latitude=40.7200,
        longitude=-74.0100,
        stop_type="bus_stop",
        has_ramp=False,
        has_audio_signals=False,
        has_tactile_pavement=False,
        has_seating=False,
        has_lighting=False,
        has_staff_assistance=False,
        has_restroom=False,
        has_information_board=False,
        accessible_entrance=False,
        level_platform=False,
    )


@pytest.fixture
def sample_grievances():
    """Sample grievances for testing."""
    return [
        Grievance(id="G001", stop_id="STOP_002", text="No ramp at entrance", severity=4),
        Grievance(id="G002", stop_id="STOP_002", text="Audio signals not working", severity=5),
        Grievance(id="G003", stop_id="STOP_002", text="Very dark at night", severity=3),
    ]


def test_gap_scorer_accessible_stop(sample_stop_accessible):
    """Test gap scoring for accessible stop."""
    scorer = GapScorer()
    gap_score, missing_features, critical_gaps = scorer.calculate_gap_score(sample_stop_accessible)
    
    # Should have no gaps
    assert gap_score == 0.0
    assert len(missing_features) == 0
    assert len(critical_gaps) == 0


def test_gap_scorer_inaccessible_stop(sample_stop_inaccessible):
    """Test gap scoring for inaccessible stop."""
    scorer = GapScorer()
    gap_score, missing_features, critical_gaps = scorer.calculate_gap_score(sample_stop_inaccessible)
    
    # Should have maximum gaps
    assert gap_score == 100.0
    assert len(missing_features) > 0
    assert len(critical_gaps) > 0


def test_gap_scorer_with_grievances(sample_stop_inaccessible, sample_grievances):
    """Test gap scoring with grievance information."""
    scorer = GapScorer()
    
    # Without grievances
    gap_score1, _, _ = scorer.calculate_gap_score(sample_stop_inaccessible)
    
    # With grievances (should get slight boost)
    gap_score2, _, _ = scorer.calculate_gap_score(
        sample_stop_inaccessible,
        grievance_themes=["No ramp", "Audio signals"],
        grievance_count=3
    )
    
    # Gap score should be same or slightly higher with grievances
    assert gap_score2 >= gap_score1


def test_priority_level_assignment(sample_stop_accessible, sample_stop_inaccessible):
    """Test priority level assignment from gap scores."""
    # Accessible should be LOW
    assert get_priority_level(10) == "LOW"
    assert get_priority_level(39) == "LOW"
    
    # Mid-range
    assert get_priority_level(40) == "MEDIUM"
    assert get_priority_level(50) == "MEDIUM"
    assert get_priority_level(59) == "MEDIUM"
    
    # High
    assert get_priority_level(60) == "HIGH"
    assert get_priority_level(75) == "HIGH"
    assert get_priority_level(79) == "HIGH"
    
    # Critical
    assert get_priority_level(80) == "CRITICAL"
    assert get_priority_level(100) == "CRITICAL"


def test_score_multiple_stops():
    """Test scoring multiple stops."""
    stops = [
        TransitStop(
            id=f"STOP_{i:03d}",
            name=f"Stop {i}",
            latitude=40.71 + i*0.01,
            longitude=-74.00 - i*0.01,
            stop_type="bus_stop",
            has_ramp=i % 2 == 0,
            has_audio_signals=i % 3 == 0,
            has_seating=i % 2 == 0,
            has_lighting=True,
        )
        for i in range(5)
    ]
    
    grievances = []
    clusters = []
    
    scorer = GapScorer()
    scores = scorer.score_stops(stops, grievances, clusters)
    
    # Should score all stops
    assert len(scores) == len(stops)
    
    # Scores should be sorted by gap score descending
    assert scores[0].gap_score >= scores[-1].gap_score


def test_missing_features_identification():
    """Test correct identification of missing features."""
    stop = TransitStop(
        id="STOP_TEST",
        name="Test Stop",
        latitude=40.7128,
        longitude=-74.0060,
        stop_type="bus_stop",
        has_ramp=False,
        has_audio_signals=False,
        has_tactile_pavement=False,
        has_seating=True,
        has_lighting=True,
        has_staff_assistance=False,
        has_restroom=False,
        has_information_board=False,
        accessible_entrance=False,
        level_platform=False,
    )
    
    scorer = GapScorer()
    gap_score, missing_features, critical_gaps = scorer.calculate_gap_score(stop)
    
    # Should identify missing features
    assert "ramp" in missing_features
    assert "audio_signals" in missing_features
    assert "tactile_pavement" in missing_features
    assert "seating" not in missing_features  # This one is present


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
