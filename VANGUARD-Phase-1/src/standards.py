"""
Accessibility standards checklist and criteria definitions.
References: WCAG 2.1, ADA Accessibility Guidelines, Universal Design Principles.
"""

from typing import List, Dict, Tuple
from enum import Enum


class Criticality(str, Enum):
    """Feature criticality levels."""
    CRITICAL = "CRITICAL"
    IMPORTANT = "IMPORTANT"
    NICE_TO_HAVE = "NICE_TO_HAVE"


# Standard accessibility features checklist
ACCESSIBILITY_STANDARDS = {
    "bus_stop": {
        "ramp": ("Wheelchair ramp or level platform at entry", Criticality.CRITICAL, 20),
        "audio_signals": ("Audio signals for visually impaired at crossing", Criticality.CRITICAL, 15),
        "tactile_pavement": ("Tactile guidance pavement for blind/low-vision", Criticality.IMPORTANT, 12),
        "seating": ("Benches/seating areas (min 2)", Criticality.IMPORTANT, 10),
        "lighting": ("Adequate lighting (≥50 lux)", Criticality.IMPORTANT, 10),
        "staff_assistance": ("Staff availability for assistance", Criticality.NICE_TO_HAVE, 8),
        "restroom": ("Accessible restroom within 100m", Criticality.NICE_TO_HAVE, 8),
        "information_board": ("Accessible route information board", Criticality.IMPORTANT, 12),
        "accessible_entrance": ("Clear, accessible entrance", Criticality.CRITICAL, 15),
    },
    "metro_station": {
        "ramp": ("Elevator or wheelchair ramp to platform", Criticality.CRITICAL, 20),
        "audio_signals": ("Audio announcements and signals", Criticality.CRITICAL, 15),
        "tactile_pavement": ("Tactile guidance on platforms", Criticality.IMPORTANT, 12),
        "seating": ("Benches/seating in station", Criticality.IMPORTANT, 10),
        "lighting": ("Adequate platform/tunnel lighting", Criticality.IMPORTANT, 10),
        "staff_assistance": ("Staff at key locations", Criticality.NICE_TO_HAVE, 8),
        "restroom": ("Accessible restroom", Criticality.NICE_TO_HAVE, 8),
        "information_board": ("Accessible service information", Criticality.IMPORTANT, 12),
        "accessible_entrance": ("Level entrance to station", Criticality.CRITICAL, 15),
    },
}


# Grievance themes and keyword patterns
GRIEVANCE_THEMES = {
    "Missing Ramp": [
        "ramp", "wheelchair", "steps", "no access", "steep",
        "can't get up", "level access", "incline"
    ],
    "No Audio Signals": [
        "audio", "sound", "signal", "announcement", "deaf", "hearing",
        "blind", "visual", "no alert"
    ],
    "Tactile Issues": [
        "tactile", "braille", "guide", "path", "guidance",
        "blind", "low vision", "navigation"
    ],
    "Poor Lighting": [
        "light", "dark", "brightness", "visibility", "shadow",
        "unsafe", "scary"
    ],
    "No Seating": [
        "seat", "bench", "rest", "stand", "tired", "elderly"
    ],
    "Restroom Issues": [
        "restroom", "toilet", "bathroom", "WC", "facility",
        "private", "accessible"
    ],
    "Staff/Assistance": [
        "staff", "help", "assistance", "attendant", "support",
        "someone", "available"
    ],
    "Information/Navigation": [
        "sign", "information", "map", "direction", "route",
        "unclear", "confusing", "readable", "font"
    ],
    "Safety/Maintenance": [
        "safety", "dangerous", "broken", "dirty", "damage",
        "hazard", "obstruct", "repair", "clean"
    ],
    "General Accessibility": [
        "accessible", "accessibility", "disability", "impaired",
        "mobility", "chronic", "pain", "condition"
    ],
}


def get_standards_for_stop_type(stop_type: str) -> Dict[str, Tuple[str, Criticality, float]]:
    """
    Get accessibility standards for a specific stop type.
    
    Args:
        stop_type: 'bus_stop' or 'metro_station'
    
    Returns:
        Dict mapping feature -> (description, criticality, weight)
    """
    return ACCESSIBILITY_STANDARDS.get(
        stop_type.lower(),
        ACCESSIBILITY_STANDARDS["bus_stop"]  # default
    )


def get_feature_keywords(theme: str) -> List[str]:
    """
    Get keywords associated with a grievance theme.
    
    Args:
        theme: Theme name
    
    Returns:
        List of keywords
    """
    return GRIEVANCE_THEMES.get(theme, [])


def calculate_feature_weights(stop_type: str) -> Dict[str, float]:
    """
    Calculate normalized weights for all features (sum = 100).
    
    Args:
        stop_type: Stop type
    
    Returns:
        Dict mapping feature -> normalized weight (0-100)
    """
    standards = get_standards_for_stop_type(stop_type)
    total_weight = sum(weight for _, _, weight in standards.values())
    
    return {
        feature: (weight / total_weight) * 100
        for feature, (_, _, weight) in standards.items()
    }


def get_all_themes() -> List[str]:
    """Get all defined grievance themes."""
    return list(GRIEVANCE_THEMES.keys())


def recommend_remediations(missing_features: List[str]) -> List[str]:
    """
    Generate remediation recommendations for missing features.
    
    Args:
        missing_features: List of missing feature names
    
    Returns:
        List of recommendations
    """
    recommendations = []
    
    recommendations_map = {
        "ramp": [
            "Install wheelchair ramp complying with local standards",
            "Create level platform at main entrance",
            "Add portable ramp for temporary accessibility"
        ],
        "audio_signals": [
            "Install audio signal system at road crossing",
            "Add audio announcements for route information",
            "Implement vibration alerts for deaf users"
        ],
        "tactile_pavement": [
            "Install tactile guide paths on platform",
            "Add braille markers and signage",
            "Mark hazard areas with tactile warning tiles"
        ],
        "seating": [
            "Install weather-protected seating (min 2 benches)",
            "Provide seat backs and armrests for elderly users",
            "Add priority seating for elderly/disabled"
        ],
        "lighting": [
            "Upgrade to LED lighting (≥50 lux minimum)",
            "Install motion sensors for 24/7 safety",
            "Improve lighting on stairs and platforms"
        ],
        "staff_assistance": [
            "Schedule staff during peak hours",
            "Train staff on disability accessibility",
            "Provide emergency assistance button/phone"
        ],
        "restroom": [
            "Add accessible restroom within 100m",
            "Ensure wheelchair-accessible stall (1.5m width)",
            "Install grab bars and baby change table"
        ],
        "information_board": [
            "Install large-print information board",
            "Add QR codes linking to audio/digital info",
            "Provide information in multiple formats"
        ],
        "accessible_entrance": [
            "Remove barriers to main entrance",
            "Ensure level access (no > 1:20 slope)",
            "Install clear signage for accessible routes"
        ],
    }
    
    for feature in missing_features:
        feature_key = feature.lower().replace(" ", "_")
        recs = recommendations_map.get(feature_key, [f"Address missing {feature}"])
        recommendations.extend(recs[:1])  # Take first recommendation
    
    return recommendations


# Example cost estimates for remediations
REMEDIATION_COSTS = {
    "ramp": "Medium ($5K-$15K)",
    "audio_signals": "High ($10K-$30K)",
    "tactile_pavement": "Medium ($8K-$20K)",
    "seating": "Low ($1K-$3K)",
    "lighting": "Medium ($3K-$10K)",
    "staff_assistance": "Low ($2K-$5K/year)",
    "restroom": "Very High ($30K-$100K)",
    "information_board": "Low ($2K-$8K)",
    "accessible_entrance": "High ($15K-$50K)",
}


def estimate_remediation_cost(missing_features: List[str]) -> str:
    """
    Estimate total remediation cost category.
    
    Args:
        missing_features: List of missing features
    
    Returns:
        Cost category string
    """
    if not missing_features:
        return "None ($0)"
    
    total_cost_values = {"Low": 1, "Medium": 2, "High": 3, "Very High": 4}
    costs = []
    
    for feature in missing_features:
        feature_key = feature.lower().replace(" ", "_")
        cost_str = REMEDIATION_COSTS.get(feature_key, "Medium ($5K-$15K)")
        cost_category = cost_str.split()[0]  # Extract "Low", "Medium", etc.
        costs.append(total_cost_values.get(cost_category, 2))
    
    avg_cost_level = sum(costs) / len(costs)
    
    if avg_cost_level < 1.5:
        return "Low ($1K-$5K)"
    elif avg_cost_level < 2.5:
        return "Medium ($5K-$20K)"
    elif avg_cost_level < 3.5:
        return "High ($20K-$60K)"
    else:
        return "Very High ($60K+)"
