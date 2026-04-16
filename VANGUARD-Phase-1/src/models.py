"""
Pydantic data models for transit stops, grievances, and accessibility scores.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field


class PriorityLevel(str, Enum):
    """Accessibility priority levels."""
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class TransitStop(BaseModel):
    """Transit stop/station data model."""
    id: str = Field(..., description="Unique stop identifier")
    name: str = Field(..., description="Stop/station name")
    latitude: float = Field(..., description="Geographic latitude")
    longitude: float = Field(..., description="Geographic longitude")
    stop_type: str = Field(default="bus", description="Type: bus, metro, tram, etc.")
    route_ids: List[str] = Field(default_factory=list, description="Route IDs serving this stop")
    
    # Accessibility features present
    has_ramp: bool = Field(default=False, description="Wheelchair ramp present")
    has_audio_signals: bool = Field(default=False, description="Audio signals for crossing")
    has_tactile_pavement: bool = Field(default=False, description="Tactile guidance pavement")
    has_seating: bool = Field(default=False, description="Benches/seating area")
    has_lighting: bool = Field(default=False, description="Adequate lighting")
    has_staff_assistance: bool = Field(default=False, description="Staff available to assist")
    has_restroom: bool = Field(default=False, description="Accessible restroom")
    has_information_board: bool = Field(default=False, description="Accessible info board")
    
    accessible_entrance: bool = Field(default=False, description="Accessible entrance")
    level_platform: bool = Field(default=False, description="Level platform (no steep steps)")
    
    district: Optional[str] = Field(default=None, description="Administrative district")
    notes: Optional[str] = Field(default=None, description="Additional notes")


class Grievance(BaseModel):
    """Citizen grievance/complaint data model."""
    id: str = Field(..., description="Unique grievance identifier")
    stop_id: str = Field(..., description="ID of transit stop")
    text: str = Field(..., description="Complaint text")
    category: Optional[str] = Field(default=None, description="Manual category (optional)")
    severity: int = Field(default=3, ge=1, le=5, description="Severity 1-5")
    timestamp: datetime = Field(default_factory=datetime.now, description="When submitted")
    submitted_by: Optional[str] = Field(default=None, description="Anonymized user ID")
    resolved: bool = Field(default=False, description="Whether complaint was resolved")


class AccessibilityGap(BaseModel):
    """Accessibility gap for a single feature."""
    feature: str = Field(..., description="Feature name (e.g., 'ramp')")
    present: bool = Field(..., description="Is feature present?")
    criticality: str = Field(..., description="CRITICAL, IMPORTANT, or NICE_TO_HAVE")
    grievance_count: int = Field(default=0, description="Number of grievances mentioning this")


class ImageDetection(BaseModel):
    """Single object detection from an accessibility image."""
    label: str = Field(..., description="Detected class label")
    confidence: float = Field(..., ge=0, le=1, description="Detection confidence")
    bbox: Optional[List[float]] = Field(default=None, description="Bounding box [x1, y1, x2, y2]")
    source: Optional[str] = Field(default=None, description="Model or heuristic source")


class ImageAuditSummary(BaseModel):
    """Summary of accessibility findings from a single image."""
    image_id: str = Field(..., description="Unique image identifier")
    image_name: str = Field(..., description="Original image filename")
    source_path: str = Field(..., description="Stored image path")
    stop_id: Optional[str] = Field(default=None, description="Stop ID mapped to this image")
    detector: str = Field(default="demo_fallback", description="Detector name or mode")
    image_width: Optional[int] = Field(default=None, description="Image width in pixels")
    image_height: Optional[int] = Field(default=None, description="Image height in pixels")
    detections: List[ImageDetection] = Field(default_factory=list, description="Detected objects")
    inferred_features: Dict[str, bool] = Field(default_factory=dict, description="Feature flags inferred from the image")
    overall_signal: Optional[str] = Field(default=None, description="Net accessibility signal")
    overall_confidence: float = Field(default=0.0, description="Overall confidence score")


class AccessibilityScore(BaseModel):
    """Accessibility audit score for a transit stop."""
    stop_id: str = Field(..., description="Transit stop ID")
    stop_name: str = Field(..., description="Stop name")
    latitude: float = Field(..., description="Latitude")
    longitude: float = Field(..., description="Longitude")
    
    gap_score: float = Field(..., ge=0, le=100, description="Gap score 0-100 (higher = more gaps)")
    priority_level: PriorityLevel = Field(..., description="Priority for intervention")
    
    missing_features: List[str] = Field(default_factory=list, description="Missing accessibility features")
    critical_gaps: List[AccessibilityGap] = Field(default_factory=list, description="Critical gaps")
    
    grievance_count: int = Field(default=0, description="Total grievances for this stop")
    top_themes: List[str] = Field(default_factory=list, description="Top grievance themes")
    image_findings: List[str] = Field(default_factory=list, description="Image-derived accessibility findings")
    image_detection_confidence: Optional[float] = Field(default=None, description="Average image detection confidence")
    
    remediation_cost_estimate: Optional[str] = Field(default=None, description="Rough cost category")
    recommendations: List[str] = Field(default_factory=list, description="Improvement recommendations")
    
    audit_timestamp: datetime = Field(default_factory=datetime.now, description="When audit was performed")


class GrievanceCluster(BaseModel):
    """A cluster of related grievances."""
    cluster_id: int = Field(..., description="Cluster index")
    theme: str = Field(..., description="Inferred theme/topic")
    grievance_ids: List[str] = Field(..., description="IDs of grievances in cluster")
    count: int = Field(..., description="Number of grievances")
    top_keywords: List[str] = Field(default_factory=list, description="Top keywords")
    silhouette_score: Optional[float] = Field(default=None, description="Cluster cohesion score")


class AuditReport(BaseModel):
    """Complete accessibility audit report."""
    report_id: str = Field(..., description="Unique report ID")
    city: str = Field(..., description="City name")
    generated_at: datetime = Field(default_factory=datetime.now, description="Report timestamp")
    
    total_stops_audited: int = Field(..., description="Total stops in audit")
    total_grievances_analyzed: int = Field(..., description="Total grievances processed")
    coverage_percent: float = Field(..., ge=0, le=100, description="% of network covered")
    
    stops_by_priority: Dict[str, int] = Field(..., description="Count of stops per priority level")
    avg_gap_score: float = Field(..., description="Average gap score across network")
    
    grievance_themes: List[GrievanceCluster] = Field(..., description="Top grievance themes")
    top_priority_stops: List[AccessibilityScore] = Field(..., description="Top 10 priority stops")
    data_source: str = Field(default="csv", description="Primary data source: mock/csv/gtfs")
    image_analysis_enabled: bool = Field(default=False, description="Whether images were analyzed")
    image_count: int = Field(default=0, description="Number of images analyzed")
    image_detector_mode: Optional[str] = Field(default=None, description="Detector mode used for image inference")
    image_findings_summary: List[ImageAuditSummary] = Field(default_factory=list, description="Image audit summaries")
    evaluation_metrics: Dict[str, float] = Field(default_factory=dict, description="Evaluation metrics including precision/recall/F1")
    
    key_findings: List[str] = Field(default_factory=list, description="Main findings")
    recommendations: List[str] = Field(default_factory=list, description="Strategic recommendations")
    
    generation_time_seconds: float = Field(..., description="Report generation time")


class UploadRequest(BaseModel):
    """Request model for data upload."""
    stops_file: Optional[str] = Field(default=None, description="Path or content of stops CSV")
    grievances_file: Optional[str] = Field(default=None, description="Path or content of grievances CSV")
    image_files: Optional[List[str]] = Field(default=None, description="Optional image paths or names")
    image_stop_ids: Optional[List[str]] = Field(default=None, description="Optional stop IDs aligned with image files")
    city_name: str = Field(default="Sample City", description="City identifier")


class StopsResponse(BaseModel):
    """Response model for stops query."""
    total_count: int = Field(..., description="Total stops")
    stops: List[AccessibilityScore] = Field(..., description="Stop audit scores")
    summary_stats: Dict[str, Any] = Field(..., description="Summary statistics")
