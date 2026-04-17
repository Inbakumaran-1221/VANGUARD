"""
FastAPI backend for accessibility auditor.
Provides REST API endpoints for data upload, analysis, and reporting.
"""

import io
import logging
from typing import List, Optional
import tempfile
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks, Form
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src.models import UploadRequest, StopsResponse
from src.pipeline import run_audit_pipeline, AuditPipeline
from src.image_processor import ImageProcessor
from src.pdf_reporter import generate_pdf_report
from src.utils import get_logger, setup_logging

# Setup logging
setup_logging(logging.INFO)
logger = get_logger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Accessibility Auditor API",
    description="AI-Powered Accessibility Gap Detection System for Urban Public Transport",
    version="0.1.0",
)

# Enable CORS for frontend requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory cache for pipeline results (for demo)
_pipeline_cache: dict = {}


def _parse_stop_ids(raw_stop_ids: Optional[str], count: int) -> List[Optional[str]]:
    if not raw_stop_ids:
        return [None] * count

    parsed = [item.strip() or None for item in raw_stop_ids.split(",")]
    if len(parsed) < count:
        parsed.extend([None] * (count - len(parsed)))
    return parsed[:count]


@app.get("/")
async def root():
    """Root endpoint - health check."""
    return {
        "status": "operational",
        "service": "Accessibility Auditor API",
        "version": "0.1.0"
    }


@app.post("/upload")
async def upload_data(
    city_name: str = "Sample City",
    stops_file: Optional[UploadFile] = File(None),
    gtfs_file: Optional[UploadFile] = File(None),
    grievances_file: Optional[UploadFile] = File(None),
    ground_truth_file: Optional[UploadFile] = File(None),
    image_files: Optional[List[UploadFile]] = File(None),
    image_stop_ids: Optional[str] = Form(None),
    detector_mode: str = Form("auto"),
    detector_model_path: Optional[str] = Form(None),
):
    """
    Upload transit stops and grievance data.
    
    Args:
        city_name: Name of city
        stops_file: CSV file with transit stops
        grievances_file: CSV file with citizen grievances
    
    Returns:
        Job ID and status
    """
    logger.info(f"Upload request for {city_name}")
    
    # Create temp directory for uploaded files
    temp_dir = Path(tempfile.mkdtemp())
    image_dir = temp_dir / "images"
    
    stops_path = None
    gtfs_path = None
    grievances_path = None
    ground_truth_path = None
    image_paths: List[str] = []
    
    try:
        # Save uploaded files
        if stops_file:
            stops_path = temp_dir / "stops.csv"
            with open(stops_path, "wb") as f:
                f.write(await stops_file.read())
            logger.info(f"Saved stops file: {stops_path}")

        if gtfs_file:
            gtfs_path = temp_dir / "gtfs_feed.zip"
            with open(gtfs_path, "wb") as f:
                f.write(await gtfs_file.read())
            logger.info(f"Saved GTFS file: {gtfs_path}")
        
        if grievances_file:
            grievances_path = temp_dir / "grievances.csv"
            with open(grievances_path, "wb") as f:
                f.write(await grievances_file.read())
            logger.info(f"Saved grievances file: {grievances_path}")

        if ground_truth_file:
            ground_truth_path = temp_dir / "ground_truth.csv"
            with open(ground_truth_path, "wb") as f:
                f.write(await ground_truth_file.read())
            logger.info(f"Saved ground truth file: {ground_truth_path}")

        if image_files:
            processor = ImageProcessor()
            stop_id_list = _parse_stop_ids(image_stop_ids, len(image_files))
            prepared_images = await processor.prepare_uploads(image_files, image_dir, stop_id_list)
            image_paths = [image.stored_path for image in prepared_images]
            logger.info(f"Saved {len(prepared_images)} image(s) for visual analysis")
        
        # Run audit pipeline
        report, pipeline = run_audit_pipeline(
            city_name=city_name,
            stops_source=str(stops_path) if stops_path else None,
            grievances_source=str(grievances_path) if grievances_path else None,
            gtfs_source=str(gtfs_path) if gtfs_path else None,
            ground_truth_source=str(ground_truth_path) if ground_truth_path else None,
            use_mock=not stops_file and not grievances_file and not gtfs_file,  # Use mock if no files
            clustering_method='tfidf'
            ,
            image_paths=image_paths or None,
            image_stop_ids=_parse_stop_ids(image_stop_ids, len(image_paths)) if image_paths else None,
            detector_mode=detector_mode,
            detector_model_path=detector_model_path,
        )
        
        # Cache results
        job_id = report.report_id
        _pipeline_cache[job_id] = {
            'report': report,
            'pipeline': pipeline,
            'stops': pipeline.stops,
            'grievances': pipeline.grievances,
            'clusters': pipeline.clusters,
            'scores': pipeline.scores,
            'image_findings': pipeline.image_findings,
            'evaluation_metrics': pipeline.evaluation_metrics,
        }
        
        logger.info(f"Audit complete: {job_id}")
        
        return {
            "job_id": job_id,
            "status": "completed",
            "city": city_name,
            "stops_analyzed": len(pipeline.stops),
            "grievances_analyzed": len(pipeline.grievances),
            "clusters_identified": len(pipeline.clusters),
            "images_analyzed": len(pipeline.image_findings),
            "data_source": pipeline.data_source,
            "evaluation_metrics": pipeline.evaluation_metrics,
        }
    
    except Exception as e:
        logger.error(f"Upload failed: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))
    
    finally:
        # Note: Files are kept in temp directory; in production, would clean up appropriately
        pass


@app.get("/report/{job_id}")
async def get_report(job_id: str):
    """
    Get audit report (JSON format).
    
    Args:
        job_id: Report ID from upload response
    
    Returns:
        JSON audit report
    """
    if job_id not in _pipeline_cache:
        raise HTTPException(status_code=404, detail=f"Report not found: {job_id}")
    
    cached = _pipeline_cache[job_id]
    report = cached['report']
    
    return {
        "report_id": report.report_id,
        "city": report.city,
        "generated_at": report.generated_at.isoformat(),
        "total_stops_audited": report.total_stops_audited,
        "total_grievances_analyzed": report.total_grievances_analyzed,
        "coverage_percent": report.coverage_percent,
        "stops_by_priority": report.stops_by_priority,
        "avg_gap_score": report.avg_gap_score,
        "key_findings": report.key_findings,
        "recommendations": report.recommendations,
        "generation_time_seconds": report.generation_time_seconds,
        "data_source": report.data_source,
        "image_analysis_enabled": report.image_analysis_enabled,
        "image_count": report.image_count,
        "image_detector_mode": report.image_detector_mode,
        "evaluation_metrics": report.evaluation_metrics,
    }


@app.get("/report/{job_id}/pdf")
async def get_report_pdf(job_id: str):
    """
    Get audit report in PDF format.
    
    Args:
        job_id: Report ID
    
    Returns:
        PDF file
    """
    if job_id not in _pipeline_cache:
        raise HTTPException(status_code=404, detail=f"Report not found: {job_id}")
    
    cached = _pipeline_cache[job_id]
    report = cached['report']
    
    try:
        pdf_bytes = generate_pdf_report(report)
        
        return StreamingResponse(
            io.BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={report.report_id}.pdf"}
        )
    
    except Exception as e:
        logger.error(f"PDF generation failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate PDF")


@app.get("/images/{job_id}")
async def get_image_findings(job_id: str):
    """Get image analysis results for a completed audit."""
    if job_id not in _pipeline_cache:
        raise HTTPException(status_code=404, detail=f"Report not found: {job_id}")

    cached = _pipeline_cache[job_id]
    findings = cached.get('image_findings', [])

    return {
        "total_images": len(findings),
        "images": [finding.model_dump() if hasattr(finding, "model_dump") else finding.dict() for finding in findings],
    }


@app.get("/stops/{job_id}")
async def get_stops(job_id: str, skip: int = 0, limit: int = 20):
    """
    Get all stops with accessibility scores.
    
    Args:
        job_id: Report ID
        skip: Pagination offset
        limit: Pagination limit
    
    Returns:
        List of stops with scores
    """
    if job_id not in _pipeline_cache:
        raise HTTPException(status_code=404, detail=f"Report not found: {job_id}")
    
    cached = _pipeline_cache[job_id]
    scores = cached['scores']
    
    paginated_scores = scores[skip:skip + limit]
    
    return {
        "total_count": len(scores),
        "skip": skip,
        "limit": limit,
        "stops": [
            {
                "stop_id": s.stop_id,
                "stop_name": s.stop_name,
                "latitude": s.latitude,
                "longitude": s.longitude,
                "gap_score": s.gap_score,
                "priority_level": s.priority_level.value,
                "grievance_count": s.grievance_count,
                "top_themes": s.top_themes,
                "recommendations": s.recommendations[:2],
                "remediation_cost": s.remediation_cost_estimate,
            }
            for s in paginated_scores
        ]
    }


@app.get("/themes/{job_id}")
async def get_themes(job_id: str):
    """
    Get grievance clusters and themes.
    
    Args:
        job_id: Report ID
    
    Returns:
        List of grievance themes/clusters
    """
    if job_id not in _pipeline_cache:
        raise HTTPException(status_code=404, detail=f"Report not found: {job_id}")
    
    cached = _pipeline_cache[job_id]
    clusters = cached['clusters']
    
    return {
        "total_clusters": len(clusters),
        "themes": [
            {
                "cluster_id": c.cluster_id,
                "theme": c.theme,
                "count": c.count,
                "top_keywords": c.top_keywords,
                "silhouette_score": c.silhouette_score,
            }
            for c in sorted(clusters, key=lambda c: c.count, reverse=True)
        ]
    }


@app.get("/priority-map/{job_id}")
async def get_priority_map(job_id: str):
    """
    Get geospatial priority data for map visualization.
    
    Args:
        job_id: Report ID
    
    Returns:
        List of stops with location and priority info
    """
    if job_id not in _pipeline_cache:
        raise HTTPException(status_code=404, detail=f"Report not found: {job_id}")
    
    cached = _pipeline_cache[job_id]
    scores = cached['scores']
    
    # Group by priority level
    by_priority = {}
    for score in scores:
        priority = score.priority_level.value
        if priority not in by_priority:
            by_priority[priority] = []
        
        by_priority[priority].append({
            "stop_id": score.stop_id,
            "stop_name": score.stop_name,
            "latitude": score.latitude,
            "longitude": score.longitude,
            "gap_score": score.gap_score,
            "grievances": score.grievance_count,
        })
    
    return {
        "map_data": by_priority,
        "total_stops": len(scores),
        "center_latitude": sum(s.latitude for s in scores) / len(scores) if scores else 0,
        "center_longitude": sum(s.longitude for s in scores) / len(scores) if scores else 0,
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    
    logger.info("Starting Accessibility Auditor API server")
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
