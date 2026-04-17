"""
Utility functions: logging, constants, and helpers.
"""

import logging
import uuid
from datetime import datetime
from pathlib import Path

# Configure logging
def setup_logging(log_level=logging.INFO):
    """Setup logging configuration."""
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('logs/accessibility_auditor.log')
        ]
    )
    
    # Create logs directory if it doesn't exist
    Path('logs').mkdir(exist_ok=True)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance."""
    return logging.getLogger(name)


def generate_id() -> str:
    """Generate a unique ID."""
    return str(uuid.uuid4())[:8]


def generate_report_id() -> str:
    """Generate a report ID with timestamp."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_id = generate_id()
    return f"AUDIT_{timestamp}_{unique_id}"


# Constants
SUPPORTED_STOP_TYPES = ["bus_stop", "metro_station", "tram_stop", "train_station"]
MIN_GRIEVANCES_FOR_CLUSTERING = 5
DEFAULT_N_CLUSTERS = 8  # Start with 8 clusters, optimize via silhouette score
MAX_N_CLUSTERS = 15
MIN_SILHOUETTE_SCORE = 0.3  # Acceptable clustering quality

# Priority thresholds
PRIORITY_THRESHOLDS = {
    "CRITICAL": 80,   # gap_score >= 80
    "HIGH": 60,       # gap_score >= 60
    "MEDIUM": 40,     # gap_score >= 40
    "LOW": 0,         # gap_score < 40
}


def get_priority_level(gap_score: float) -> str:
    """Determine priority level from gap score."""
    if gap_score >= PRIORITY_THRESHOLDS["CRITICAL"]:
        return "CRITICAL"
    elif gap_score >= PRIORITY_THRESHOLDS["HIGH"]:
        return "HIGH"
    elif gap_score >= PRIORITY_THRESHOLDS["MEDIUM"]:
        return "MEDIUM"
    else:
        return "LOW"


def calculate_coverage_percent(total_stops: int, audited_stops: int) -> float:
    """Calculate coverage percentage."""
    if total_stops == 0:
        return 0.0
    return (audited_stops / total_stops) * 100


def format_duration(seconds: float) -> str:
    """Format duration in human-readable format."""
    if seconds < 60:
        return f"{seconds:.2f}s"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.2f}m"
    else:
        hours = seconds / 3600
        return f"{hours:.2f}h"


# Data validation
def validate_lat_lon(latitude: float, longitude: float) -> bool:
    """Validate latitude and longitude coordinates."""
    return -90 <= latitude <= 90 and -180 <= longitude <= 180


def validate_severity(severity: int) -> bool:
    """Validate grievance severity (1-5)."""
    return 1 <= severity <= 5


# CSV header expectations
EXPECTED_STOPS_HEADERS = {
    "id", "name", "latitude", "longitude", "stop_type",
    "has_ramp", "has_audio_signals", "has_tactile_pavement",
    "has_seating", "has_lighting", "has_staff_assistance",
    "has_restroom", "has_information_board", "accessible_entrance",
    "level_platform", "district"
}

EXPECTED_GRIEVANCES_HEADERS = {
    "id", "stop_id", "text", "severity", "timestamp"
}


def validate_csv_headers(headers: set, expected: set, csv_type: str) -> tuple[bool, list]:
    """
    Validate CSV headers.
    
    Args:
        headers: Actual headers from CSV
        expected: Expected headers
        csv_type: Type of CSV (e.g., "stops", "grievances")
    
    Returns:
        (is_valid, missing_headers)
    """
    missing = expected - headers
    extra = headers - expected
    
    # Require all expected headers
    is_valid = len(missing) == 0
    
    return is_valid, list(missing)
