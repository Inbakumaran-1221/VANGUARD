# Quick Start Guide

## 1-Minute Setup

### Installation

```bash
# Navigate to project
cd d:\KSR

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -e .
```

### Run Demo

```bash
# Generate sample data
python -m src.data_generator

# Launch dashboard
streamlit run src/dashboard.py
```

Then open http://localhost:8501 in your browser.

---

## 5-Minute Workflow

### Step 1: Prepare Your Data

**Create `stops.csv`:**
```csv
id,name,latitude,longitude,stop_type,has_ramp,has_audio_signals,has_seating,has_lighting,district
STOP_001,Main Station,40.7128,-74.0060,metro_station,true,false,true,true,Central
STOP_002,Market Plaza,40.7200,-74.0100,bus_stop,false,false,false,true,Downtown
```

**Create `grievances.csv`:**
```csv
id,stop_id,text,severity,timestamp
GRV_001,STOP_001,No audio signals - deaf users can't hear announcements,5,2025-10-15T14:30:00
GRV_002,STOP_002,Very dark at night - safety concern,4,2025-10-16T20:45:00
```

### Step 2: Run Analysis

**Option A: Via Dashboard**
1. Launch: `streamlit run src/dashboard.py`
2. Click "Upload Data" tab
3. Select "Upload CSV Files"
4. Choose your CSV files
5. Click "▶ Run Audit Analysis"
6. Wait for results (typically 15-30 seconds)

**Option B: Programmatically**
```python
from src.pipeline import run_audit_pipeline

report, pipeline = run_audit_pipeline(
    city_name="My City",
    stops_source="stops.csv",
    grievances_source="grievances.csv"
)

print(f"Gap Scores: {[s.gap_score for s in pipeline.scores]}")
print(f"Average: {report.avg_gap_score:.1f}/100")
```

### Step 3: Explore Results

**Dashboard tabs:**
- **Overview:** Key metrics and charts
- **Map:** See where problems are (red = critical, orange = high)
- **Stops:** Detailed analysis for each location
- **Themes:** What are the main complaints?
- **Report:** Download PDF for sharing

### Step 4: Export & Share

Click **"Download PDF Report"** to get:
- Executive summary
- Priority breakdown
- Top 10 stops needing work
- Recommendations
- Cost estimates

---

## Common Use Cases

### Use Case 1: Audit a Single City

```python
from src.pipeline import run_audit_pipeline
from src.pdf_reporter import generate_pdf_report

# Run audit
report, pipeline = run_audit_pipeline(
    city_name="Portland",
    stops_source="portland_stops.csv",
    grievances_source="portland_complaints.csv",
    clustering_method='tfidf'  # Fast
)

# Generate PDF
pdf_bytes = generate_pdf_report(report)
with open("portland_audit_report.pdf", "wb") as f:
    f.write(pdf_bytes)

# Print summary
print(f"✓ Audited {report.total_stops_audited} stops")
print(f"✓ Analyzed {report.total_grievances_analyzed} grievances")
print(f"✓ Found {report.stops_by_priority['CRITICAL']} CRITICAL stops")
```

### Use Case 2: Identify Ramp Accessibility Gaps

```python
from src.gap_scorer import GapScorer
from src.data_loaders import load_data

# Load data
stops, grievances = load_data(
    stops_source="stops.csv",
    grievances_source="grievances.csv"
)

# Score gaps
scorer = GapScorer()
gaps = []
for stop in stops:
    gap_score, missing, critical = scorer.calculate_gap_score(stop)
    if "ramp" in missing:
        gaps.append({
            'stop': stop.name,
            'gap_score': gap_score,
            'location': (stop.latitude, stop.longitude)
        })

# Sort by gap score
gaps.sort(key=lambda x: x['gap_score'], reverse=True)
for g in gaps[:10]:
    print(f"{g['stop']}: {g['gap_score']:.1f}/100")
```

### Use Case 3: API Integration

```bash
# Start server
python -m uvicorn src.main:app --host 0.0.0.0 --port 8000
```

Then from any application:
```bash
# Upload data
curl -X POST http://localhost:8000/upload \
  -F city_name="San Francisco" \
  -F stops_file=@stops.csv \
  -F grievances_file=@grievances.csv

# Response:
# {
#   "job_id": "AUDIT_20261015_abc123",
#   "status": "completed",
#   "stops_analyzed": 500,
#   "clusters_identified": 8
# }

# Get results
curl http://localhost:8000/report/AUDIT_20261015_abc123

# Get map data for visualization
curl http://localhost:8000/priority-map/AUDIT_20261015_abc123
```

### Use Case 4: Multi-Language Support

Currently supports English. To add another language:

1. Update stopwords in `text_processing.py`:
```python
processor = TextProcessor(language='spanish')
```

2. Update grievance themes in `standards.py`:
```python
GRIEVANCE_THEMES = {
    "Rampa Faltante": ["rampa", "rampla", "acceso", "silla"],
    "Sin Señales de Audio": ["audio", "señal", "sordo", "anuncio"],
    # ...
}
```

---

## Troubleshooting

### Problem: "ModuleNotFoundError: No module named 'src'"

**Solution:**
```bash
# Make sure you're in the project root
cd d:\KSR

# Install in development mode
pip install -e .
```

### Problem: Dashboard doesn't load

**Solution:**
```bash
# Clear Streamlit cache
streamlit cache clear

# Try again
streamlit run src/dashboard.py
```

### Problem: Low clustering quality (silhouette score < 0.3)

**Solution 1:** Use embedding method (slower but better):
```python
run_audit_pipeline(..., clustering_method='embedding')
```

**Solution 2:** Increase grievance quality:
- Remove very short complaints (< 20 chars)
- Ensure complaints describe actual accessibility issues
- Use consistent terminology

### Problem: "No such file or directory: stops.csv"

**Solution:**
```python
# Use absolute path
from pathlib import Path

stops_file = Path("d:/KSR/data/stops.csv").absolute()
grievances_file = Path("d:/KSR/data/grievances.csv").absolute()

run_audit_pipeline(
    stops_source=str(stops_file),
    grievances_source=str(grievances_file)
)
```

### Problem: PDF generation fails

**Solution:**
```bash
# Reinstall reportlab with extras
pip install --force-reinstall reportlab weasyprint
```

---

## Performance Tips

### Speed Up Analysis

```python
# Faster clustering (less accurate)
run_audit_pipeline(
    ...,
    clustering_method='tfidf',  # Not 'embedding'
)

# Reduce features for faster vectorization
# Edit text_processing.py, line ~100:
tfidf_matrix = self.vectorizer.fit_transform(
    texts,
    max_features=50  # Was 100
)
```

### Handle Large Datasets (10K+ stops)

```bash
# 1. Pre-process data to remove duplicates
python -c "
import pandas as pd
df = pd.read_csv('stops.csv')
df = df.drop_duplicates(subset=['id'])
df.to_csv('stops_clean.csv', index=False)
"

# 2. Use mock clustering for testing
from src.clustering import cluster_grievances
clusters = cluster_grievances(grievances[:1000])  # First 1000

# 3. Cache results
pipeline.scores  # Results are in memory, re-use without re-computing
```

### Monitor Performance

```python
import time
from src.pipeline import run_audit_pipeline

start = time.time()
report, pipeline = run_audit_pipeline(..., use_mock=True)
elapsed = time.time() - start

print(f"Total time: {elapsed:.2f}s")
print(f"Stops: {len(pipeline.stops)} ({len(pipeline.stops)/elapsed:.0f} stops/sec)")
print(f"Clustering time: {elapsed - report.generation_time_seconds:.2f}s")
```

---

## Advanced Configuration

### Custom Accessibility Standards

Edit `src/standards.py`:

```python
ACCESSIBILITY_STANDARDS["custom_stop_type"] = {
    "feature_name": ("Human-readable description", Criticality.CRITICAL, 20),
    # Weight should sum to ~100 across all features
}
```

### Custom Grievance Themes

Edit `src/standards.py`:

```python
GRIEVANCE_THEMES = {
    "My Custom Theme": [
        "keyword1", "keyword2", "related_word",
        # These keywords identify the theme
    ],
    # ...
}
```

### Custom Gap Scoring Formula

Edit `src/gap_scorer.py`, method `calculate_gap_score()`:

```python
# Current formula:
gap_score = (gap_weight / total_weight) * 100 + grievance_boost

# Custom formula example (exponential):
gap_score = min(100, (gap_weight / total_weight) ** 1.2 * 100)
```

### Customize Dashboard

Edit `src/dashboard.py`:

```python
# Change app name and icon
st.set_page_config(
    page_title="My Accessibility Tool",
    page_icon="🏢",
    layout="wide",
)

# Add custom sections
st.markdown("""
    ### Custom Analysis Section
    Your content here
""")
```

---

## Data Privacy & Security

### Anonymization

Grievance data may contain personal information. Best practices:

```python
# Remove user IDs before sharing
from src.data_loaders import load_data

stops, grievances = load_data(...)

# Anonymize
for grievance in grievances:
    grievance.submitted_by = None  # Remove user info

# Or in CSV, use random IDs instead of real ones
```

### API Rate Limiting

For production deployment, add rate limiting:

```python
# In src/main.py
from slowapi import Limiter
limiter = Limiter(key_func=lambda: "global")

@app.post("/upload")
@limiter.limit("10/minute")
async def upload_data(...):
    # Max 10 uploads per minute
    pass
```

---

## Getting Help

### Check Logs

```bash
# View application logs
tail -f logs/accessibility_auditor.log

# Windows
Get-Content -Path logs/accessibility_auditor.log -Tail 20 -Wait
```

### Run Tests

```bash
# Run all tests
pytest tests/ -v

# Run specific test
pytest tests/test_gap_scorer.py::test_gap_scorer_accessible_stop -v

# With coverage
pytest tests/ --cov=src --cov-report=html
```

### Check API Health

```bash
curl http://localhost:8000/health
# Expected response: {"status": "healthy"}
```

### Review Documentation

- `README.md` - Project overview
- `docs/ARCHITECTURE.md` - System design
- `docs/DATA_SCHEMA.md` - Data formats
- This file - Quick start

---

## Next Steps

1. **Prepare your data** using the CSV formats from Data Schema
2. **Run a test audit** with demo data first
3. **Explore the dashboard** to understand capabilities
4. **Export PDF reports** for stakeholders
5. **Integrate with your systems** via REST API
6. **Tune clustering** if needed for better results

**Questions?** Check the docs folder or review source code comments.

---

**Version:** 0.1.0  
**Last Updated:** April 2026
