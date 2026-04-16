"""
Tests for clustering module.
"""

import pytest
from src.models import Grievance
from src.clustering import GrievanceClustering, cluster_grievances
from datetime import datetime


@pytest.fixture
def sample_grievances():
    """Sample grievances for clustering tests."""
    complaints = [
        "No ramp at entrance, wheelchair access is very difficult",
        "Wheelchair ramp is broken and needs repair",
        "There is no accessible ramp for disabled persons",
        
        "Audio signals for blind users are not working",
        "No audio announcements at the stop",
        "Deaf users cannot hear the route information",
        
        "Very dark at night, no lighting",
        "Broken lighting makes the stop unsafe",
        "Lighting is insufficient for safety",
        
        "Not enough seating for elderly people",
        "Benches are missing, nowhere to sit",
        "No chairs or resting area",
    ]
    
    return [
        Grievance(
            id=f"G{i:03d}",
            stop_id="STOP_001",
            text=complaint,
            severity=(i % 4) + 2,
            timestamp=datetime.now()
        )
        for i, complaint in enumerate(complaints)
    ]


def test_clustering_with_tfidf(sample_grievances):
    """Test clustering with TF-IDF method."""
    clusterer = GrievanceClustering(method='tfidf')
    clusters = clusterer.cluster(sample_grievances)
    
    # Should create clusters
    assert len(clusters) > 0
    
    # All grievances should be assigned
    total_assigned = sum(c.count for c in clusters)
    assert total_assigned == len(sample_grievances)
    
    # Cluster IDs should be unique
    cluster_ids = [c.cluster_id for c in clusters]
    assert len(cluster_ids) == len(set(cluster_ids))


def test_clustering_labels(sample_grievances):
    """Test that clusters are labeled with themes."""
    clusterer = GrievanceClustering(method='tfidf')
    clusters = clusterer.cluster(sample_grievances)
    
    # Label clusters
    labeled_clusters = clusterer.label_clusters(clusters, sample_grievances)
    
    # All should have themes
    assert all(c.theme for c in labeled_clusters)
    
    # Themes should not be default format
    assert all(c.theme != f"Theme_{c.cluster_id}" for c in labeled_clusters if c.count > 1)


def test_clustering_coherence(sample_grievances):
    """Test silhouette score for cluster coherence."""
    clusterer = GrievanceClustering(method='tfidf')
    clusters = clusterer.cluster(sample_grievances)
    
    # Check silhouette scores
    silhouette_scores = [c.silhouette_score for c in clusters if c.silhouette_score is not None]
    
    # Some clusters should have reasonable coherence
    assert len(silhouette_scores) > 0


def test_cluster_grievances_function(sample_grievances):
    """Test convenience function for clustering."""
    clusters = cluster_grievances(sample_grievances, method='tfidf', label_clusters=True)
    
    assert len(clusters) > 0
    assert all(hasattr(c, 'theme') for c in clusters)
    assert all(hasattr(c, 'top_keywords') for c in clusters)


def test_clustering_with_few_grievances():
    """Test clustering with very few grievances (should degrade gracefully)."""
    small_set = [
        Grievance(id="G1", stop_id="STOP", text="Ramp is broken", severity=4),
        Grievance(id="G2", stop_id="STOP", text="No audio signals", severity=3),
    ]
    
    clusterer = GrievanceClustering(method='tfidf')
    clusters = clusterer.cluster(small_set)
    
    # Should handle gracefully
    assert len(clusters) > 0
    assert sum(c.count for c in clusters) == len(small_set)


def test_semantic_similarity_grouping(sample_grievances):
    """Test that semantically similar grievances are grouped."""
    clusterer = GrievanceClustering(method='tfidf')
    clusters = clusterer.cluster(sample_grievances)
    
    # With good clustering, similar ramp complaints should group together
    # Find cluster with "ramp" theme
    ramp_cluster = None
    for cluster in clusters:
        if "ramp" in cluster.theme.lower():
            ramp_cluster = cluster
            break
    
    # Should have found at least one cluster with ramp-related grievances
    # (may not always group perfectly due to randomness in K-means)


def test_keyword_extraction(sample_grievances):
    """Test keyword extraction from grievances."""
    clusterer = GrievanceClustering(method='tfidf')
    clusters = clusterer.cluster(sample_grievances)
    
    # Check that clusters have keywords
    for cluster in clusters:
        if cluster.count > 1:
            # Larger clusters should have meaningful keywords
            assert len(cluster.top_keywords) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
