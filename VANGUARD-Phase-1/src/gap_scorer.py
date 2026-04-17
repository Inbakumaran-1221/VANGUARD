"""
Accessibility gap scoring for transit stops.
Calculates gap scores based on missing features and grievances.
"""

import logging
from typing import List, Dict, Tuple, Optional
from collections import Counter

from src.models import TransitStop, Grievance, AccessibilityScore, AccessibilityGap, PriorityLevel
from src.standards import (
    get_standards_for_stop_type, calculate_feature_weights, 
    recommend_remediations, estimate_remediation_cost, Criticality
)
from src.clustering import GrievanceCluster
from src.utils import get_logger, get_priority_level

logger = get_logger(__name__)


class GapScorer:
    """Score accessibility gaps for transit stops."""
    
    def __init__(self):
        """Initialize gap scorer."""
        pass
    
    def _get_features_from_stop(self, stop: TransitStop) -> Dict[str, bool]:
        """
        Extract accessibility features from stop.
        
        Returns:
            Dict mapping feature_name -> is_present
        """
        return {
            "ramp": stop.has_ramp,
            "audio_signals": stop.has_audio_signals,
            "tactile_pavement": stop.has_tactile_pavement,
            "seating": stop.has_seating,
            "lighting": stop.has_lighting,
            "staff_assistance": stop.has_staff_assistance,
            "restroom": stop.has_restroom,
            "information_board": stop.has_information_board,
            "accessible_entrance": stop.accessible_entrance,
            "level_platform": stop.level_platform,
        }
    
    def _get_stop_type_key(self, stop: TransitStop) -> str:
        """Get standards key for stop type."""
        stop_type = stop.stop_type.lower()
        if "metro" in stop_type or "station" in stop_type:
            return "metro_station"
        else:
            return "bus_stop"
    
    def calculate_gap_score(
        self,
        stop: TransitStop,
        grievance_themes: List[str] = None,
        grievance_count: int = 0
    ) -> Tuple[float, List[str], List[AccessibilityGap]]:
        """
        Calculate accessibility gap score for a stop.
        
        Args:
            stop: TransitStop object
            grievance_themes: List of top grievance themes for this stop
            grievance_count: Number of grievances for this stop
        
        Returns:
            Tuple of (gap_score: float, missing_features: list, critical_gaps: list)
        """
        if grievance_themes is None:
            grievance_themes = []
        
        # Get standards and weights
        stop_type_key = self._get_stop_type_key(stop)
        standards = get_standards_for_stop_type(stop_type_key)
        weights = calculate_feature_weights(stop_type_key)
        
        # Get actual features
        actual_features = self._get_features_from_stop(stop)
        
        # Calculate gap score
        total_weight = 0
        gap_weight = 0
        critical_gaps = []
        missing_features = []
        
        for feature_name, (description, criticality, _) in standards.items():
            feature_present = actual_features.get(feature_name, False)
            feature_weight = weights.get(feature_name, 0)
            total_weight += feature_weight
            
            if not feature_present:
                gap_weight += feature_weight
                missing_features.append(feature_name)
                
                # Track critical gaps
                gap = AccessibilityGap(
                    feature=feature_name,
                    present=False,
                    criticality=criticality.value,
                    grievance_count=0,  # Will update below
                )
                
                # Check if this feature is mentioned in grievance themes
                if grievance_themes:
                    for theme in grievance_themes:
                        if feature_name.replace("_", " ").lower() in theme.lower():
                            gap.grievance_count += grievance_count
                
                if criticality == Criticality.CRITICAL:
                    critical_gaps.append(gap)
        
        # Calculate normalized gap score (0-100)
        if total_weight > 0:
            gap_score = (gap_weight / total_weight) * 100
        else:
            gap_score = 0.0
        
        # Boost score slightly if there are many grievances
        grievance_boost = min(grievance_count * 2, 10)  # Max 10 point boost
        gap_score = min(gap_score + grievance_boost, 100)
        
        return gap_score, missing_features, critical_gaps
    
    def score_stops(
        self,
        stops: List[TransitStop],
        grievances: List[Grievance],
        clusters: List[GrievanceCluster]
    ) -> List[AccessibilityScore]:
        """
        Score all stops for accessibility gaps.
        
        Args:
            stops: List of TransitStop objects
            grievances: List of Grievance objects
            clusters: List of GrievanceCluster objects
        
        Returns:
            List of AccessibilityScore objects, sorted by gap_score descending
        """
        logger.info(f"Scoring {len(stops)} stops for accessibility gaps")
        
        # Create grievance map: stop_id -> list of grievances
        grievances_by_stop: Dict[str, List[Grievance]] = {}
        for grievance in grievances:
            if grievance.stop_id not in grievances_by_stop:
                grievances_by_stop[grievance.stop_id] = []
            grievances_by_stop[grievance.stop_id].append(grievance)
        
        # Create cluster map for theme lookup: grievance_id -> cluster_id
        grievance_to_cluster: Dict[str, int] = {}
        cluster_themes: Dict[int, str] = {}
        
        for cluster in clusters:
            cluster_themes[cluster.cluster_id] = cluster.theme
            for gid in cluster.grievance_ids:
                grievance_to_cluster[gid] = cluster.cluster_id
        
        scores = []
        
        for stop in stops:
            # Get grievances for this stop
            stop_grievances = grievances_by_stop.get(stop.id, [])
            stop_grievance_ids = [g.id for g in stop_grievances]
            
            # Get grievance themes for this stop
            grievance_themes = []
            for gid in stop_grievance_ids:
                cluster_id = grievance_to_cluster.get(gid)
                if cluster_id is not None:
                    theme = cluster_themes.get(cluster_id)
                    if theme:
                        grievance_themes.append(theme)
            
            # Remove duplicates while preserving frequency
            theme_counter = Counter(grievance_themes)
            top_themes = [theme for theme, _ in theme_counter.most_common(3)]
            
            # Calculate gap score
            gap_score, missing_features, critical_gaps = self.calculate_gap_score(
                stop,
                grievance_themes=top_themes,
                grievance_count=len(stop_grievances)
            )
            
            # Determine priority
            priority_level = PriorityLevel(get_priority_level(gap_score))
            
            # Generate recommendations
            recommendations = recommend_remediations(missing_features)
            cost_estimate = estimate_remediation_cost(missing_features)
            
            # Create score object
            score = AccessibilityScore(
                stop_id=stop.id,
                stop_name=stop.name,
                latitude=stop.latitude,
                longitude=stop.longitude,
                gap_score=round(gap_score, 2),
                priority_level=priority_level,
                missing_features=missing_features,
                critical_gaps=critical_gaps,
                grievance_count=len(stop_grievances),
                top_themes=top_themes,
                remediation_cost_estimate=cost_estimate,
                recommendations=recommendations,
            )
            scores.append(score)
        
        # Sort by gap score descending
        scores.sort(key=lambda s: s.gap_score, reverse=True)
        
        logger.info(f"Scored {len(scores)} stops")
        logger.info(f"CRITICAL: {sum(1 for s in scores if s.priority_level == PriorityLevel.CRITICAL)}")
        logger.info(f"HIGH: {sum(1 for s in scores if s.priority_level == PriorityLevel.HIGH)}")
        logger.info(f"MEDIUM: {sum(1 for s in scores if s.priority_level == PriorityLevel.MEDIUM)}")
        logger.info(f"LOW: {sum(1 for s in scores if s.priority_level == PriorityLevel.LOW)}")
        
        return scores


def score_accessibility_gaps(
    stops: List[TransitStop],
    grievances: List[Grievance],
    clusters: List[GrievanceCluster]
) -> List[AccessibilityScore]:
    """
    Score all stops for accessibility gaps.
    
    Args:
        stops: List of TransitStop objects
        grievances: List of Grievance objects
        clusters: List of GrievanceCluster objects
    
    Returns:
        List of AccessibilityScore objects (sorted by gap_score descending)
    """
    scorer = GapScorer()
    return scorer.score_stops(stops, grievances, clusters)
