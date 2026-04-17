# Architecture & System Design

## System Overview

The Accessibility Auditor is a modular, event-driven system that processes transit infrastructure data and citizen grievances to identify accessibility gaps. The system is designed for scalability, interpretability, and ease of integration with city planning tools.

### High-Level Data Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    DATA INGESTION LAYER                         │
├─────────────────────────────────────────────────────────────────┤
│  CSV Files  │  GTFS Feeds  │  API Endpoints  │  Mock Data       │
└────────────────┬──────────────────────────────────────────┬─────┘
                 │                                           │
                 ▼                                           ▼
        ┌────────────────────┐                  ┌──────────────────┐
        │  Stops CSV Loader  │                  │  Mock Data Gen   │
        └────────┬───────────┘                  └────────┬─────────┘
                 │                                       │
                 ├───────────────┬───────────────────────┤
                 ▼               ▼                       ▼
    ┌──────────────────┐  ┌─────────────────┐  ┌───────────────────┐
    │  Transit Stops   │  │  Grievances CSV │  │  Standards Data   │
    │  (50-10K records)│  │ (100-50K records)│  │  (WCAG/ADA)      │
    └─────────┬────────┘  └────────┬────────┘  └─────────┬─────────┘
              │                    │                      │
              └────────────────────┼──────────────────────┘
                                   │
                 ┌─────────────────▼──────────────────┐
                 │   DATA VALIDATION & PARSING       │
                 │  (CSV Schema Validation, Type     │
                 │   Conversion, Coordinate Check)   │
                 └──────────────┬─────────────────────┘
                                │
                ┌───────────────▼───────────────┐
                │ TEXT PROCESSING LAYER         │
                ├───────────────────────────────┤
                │ • Tokenization                │
                │ • Lemmatization               │
                │ • Stopword removal            │
                │ • Cleaning & normalization    │
                └───────────────┬───────────────┘
                                │
                ┌───────────────▼───────────────┐
                │ VECTORIZATION                 │
                ├───────────────────────────────┤
                │ TF-IDF or Embeddings          │
                │ (100D vectors typically)      │
                └───────────────┬───────────────┘
                                │
                ┌───────────────▼────────────────────┐
                │ CLUSTERING LAYER                   │
                ├────────────────────────────────────┤
                │ K-Means with Silhouette Score      │
                │ Optimal K: 3-15 clusters          │
                └───────────────┬────────────────────┘
                                │
            ┌───────────────────▼───────────────────────┐
            │ THEME LABELING                            │
            ├───────────────────────────────────────────┤
            │ Extract keywords per cluster              │
            │ Match to accessibility standards          │
            │ Generate theme names                      │
            └───────────────┬───────────────────────────┘
                            │
        ┌───────────────────▼───────────────────┐
        │  GAP SCORING LAYER                    │
        ├───────────────────────────────────────┤
        │ For each stop:                         │
        │  1. Identify missing features          │
        │  2. Weight by criticality              │
        │  3. Cross-reference with grievances   │
        │  4. Calculate gap_score (0-100)       │
        │  5. Assign priority level             │
        └───────────────┬───────────────────────┘
                        │
    ┌───────────────────▼──────────────────────┐
    │ AGGREGATION & REPORTING LAYER            │
    ├──────────────────────────────────────────┤
    │ • Summarize by priority level            │
    │ • Calculate network coverage %           │
    │ • Generate remediation recommendations   │
    │ • Estimate costs                         │
    └───────────────┬──────────────────────────┘
                    │
        ┌───────────▼────────────────┐
        │  REPORT GENERATION         │
        ├────────────────────────────┤
        │  JSON Report               │
        │  PDF Export                │
        │  Map Visualization Data    │
        └───────────────┬────────────┘
                        │
    ┌───────────────────▼──────────────────────┐
    │  PRESENTATION LAYER                      │
    ├──────────────────────────────────────────┤
    │  • Streamlit Dashboard                   │
    │  • FastAPI REST Endpoints                │
    │  • PDF Download                          │
    │  • Geospatial Mapping                    │
    └──────────────────────────────────────────┘
```

## Module Architecture

### Layer 1: Data Models & Validation (`models.py`)

**Responsibilities:**
- Define Pydantic models for type safety
- Validate incoming data
- Ensure data consistency

**Key Classes:**
- `TransitStop`: Core infrastructure entity
- `Grievance`: Citizen complaint entity
- `AccessibilityScore`: Gap assessment output
- `GrievanceCluster`: Grouped complaints with theme
- `AuditReport`: Comprehensive audit summary

**Benefits:**
- Type hints for IDE support
- Runtime validation
- Automatic serialization/deserialization (JSON)

### Layer 2: Data Ingestion (`data_loaders.py`)

**Responsibilities:**
- Load data from multiple sources
- Handle format variations
- Validate data quality
- Provide unified interface

**Supported Sources:**
- CSV files (primary)
- Mock data generator
- Extensible for GTFS, APIs

**Key Classes:**
- `DataLoader`: Base class
- `CSVDataLoader`: CSV file parsing
- `MockDataLoader`: Synthetic data generation

### Layer 3: NLP Processing (`text_processing.py`)

**Responsibilities:**
- Clean and normalize text
- Extract meaningful tokens
- Vectorize text for clustering

**Pipeline:**
1. **Clean:** Remove URLs, special chars, normalize
2. **Tokenize:** Split into words
3. **Lemmatize:** Normalize word forms
4. **Filter:** Remove stopwords and short words
5. **Vectorize:** TF-IDF or embeddings

**Configuration Options:**
- Language selection (currently English)
- TF-IDF max_features (default: 100)
- Min/max document frequency thresholds

### Layer 4: Clustering (`clustering.py`)

**Responsibilities:**
- Group similar grievances
- Identify accessibility themes
- Assess clustering quality

**Algorithm:**
```
1. Vectorize texts → [n_docs × n_features]
2. For K=3 to 15:
   a. Fit K-means (n_init=10)
   b. Calculate silhouette_score
   c. Track best K
3. Final clustering with optimal K
4. Label clusters with themes
```

**Quality Metrics:**
- **Silhouette Score:** -1 to +1 (higher is better)
  - ≥ 0.5: Strong structure
  - 0.3-0.5: Acceptable
  - < 0.3: Weak (default minimum)

### Layer 5: Gap Scoring (`gap_scorer.py`)

**Responsibilities:**
- Calculate accessibility gaps per stop
- Prioritize stops for intervention
- Generate remediation recommendations

**Gap Score Formula:**
```
gap_score = (Σ(missing_feature_weight)) / (Σ(total_weights)) × 100

Where:
- Feature weights come from accessibility standards
- Critical features (e.g., ramp) weighted higher
- Grievance mentions boost score by max 10 points
- Final score: 0-100 (0=fully accessible, 100=severe gaps)
```

**Priority Levels:**
- **CRITICAL:** gap_score ≥ 80 (immediate action needed)
- **HIGH:** 60-79 (action within 3 months)
- **MEDIUM:** 40-59 (plan remediation)
- **LOW:** <40 (monitor)

### Layer 6: Pipeline Orchestration (`pipeline.py`)

**Responsibilities:**
- Coordinate all analysis steps
- Manage data flow
- Handle error propagation
- Track execution metrics

**Execution Flow:**
```python
pipeline = AuditPipeline(city_name="My City")
report = pipeline.run(
    stops_source="stops.csv",
    grievances_source="grievances.csv",
    clustering_method="tfidf"
)
```

**Steps:**
1. Load data
2. Cluster grievances
3. Score gaps
4. Generate report

**Caching:** Results cached in pipeline object for API reuse

### Layer 7: Report Generation (`pdf_reporter.py`)

**Responsibilities:**
- Create professional PDF documents
- Generate charts and visualizations
- Structure findings and recommendations

**Report Sections:**
1. Title page (city, date, coverage %)
2. Executive summary
3. Key findings
4. Priority distribution (table & chart)
5. Grievance themes analysis
6. Top 10 priority stops (detailed)
7. Strategic recommendations
8. Footer with metadata

### Layer 8: REST API (`main.py`)

**Responsibilities:**
- Expose analysis via HTTP
- Handle concurrent requests
- Cache results
- Stream file downloads

**API Used:**
- FastAPI for the REST backend
- Uvicorn as the ASGI server
- Swagger/OpenAPI documentation at `/docs`
- ReDoc documentation at `/redoc`

See [docs/API_REFERENCE.txt](docs/API_REFERENCE.txt) for a plain-text endpoint summary.

**Endpoints:**
```
POST   /upload              - Start audit analysis
GET    /report/{job_id}     - Get JSON report
GET    /report/{job_id}/pdf - Download PDF
GET    /stops/{job_id}      - List stops with scores
GET    /themes/{job_id}     - Get grievance themes
GET    /priority-map/{job_id} - Geospatial data
GET    /health              - Health check
```

**In-Memory Cache:**
```python
_pipeline_cache = {
    "AUDIT_20261201_abc123": {
        "report": AuditReport(...),
        "pipeline": AuditPipeline(...),
        "stops": [...],
        "grievances": [...],
        "clusters": [...],
        "scores": [...]
    }
}
```

### Layer 9: Dashboard UI (`dashboard.py`)

**Responsibilities:**
- Provide interactive web interface
- Visualize findings
- Enable data exploration

**Tabs:**
1. **Overview:** Key metrics and charts
2. **Map:** Geospatial priority visualization
3. **Stops:** Detailed stop analysis with filters
4. **Themes:** Grievance clustering breakdown
5. **Report:** PDF download
6. **Info:** About and documentation

**Technology:**
- Streamlit: Web framework
- Folium: Interactive maps
- Plotly: Charts and graphs
- Pandas: DataFrames for tables

## Data Structures

### TransitStop

```python
TransitStop(
    id: str,                           # Unique identifier
    name: str,                         # Human-readable name
    latitude: float,                   # GPS latitude
    longitude: float,                  # GPS longitude
    stop_type: str,                    # "bus_stop", "metro_station", etc.
    route_ids: List[str],              # Lines serving this stop
    
    # Accessibility features (boolean flags)
    has_ramp: bool,                    # Wheelchair access
    has_audio_signals: bool,           # Audio for visually impaired
    has_tactile_pavement: bool,        # Tactile paths
    has_seating: bool,                 # Rest areas
    has_lighting: bool,                # Adequate illumination
    has_staff_assistance: bool,        # Staff availability
    has_restroom: bool,                # Toilet facilities
    has_information_board: bool,       # Accessible info
    accessible_entrance: bool,         # Level entry
    level_platform: bool,              # No steep steps
    
    district: Optional[str],           # Administrative area
    notes: Optional[str],              # Additional info
)
```

### AccessibilityScore

```python
AccessibilityScore(
    stop_id: str,
    stop_name: str,
    latitude: float,
    longitude: float,
    
    gap_score: float,                  # 0-100
    priority_level: PriorityLevel,     # CRITICAL/HIGH/MEDIUM/LOW
    
    missing_features: List[str],       # Features not present
    critical_gaps: List[AccessibilityGap],  # Critical missing items
    
    grievance_count: int,              # Number of complaints
    top_themes: List[str],             # Top complaint categories
    
    remediation_cost_estimate: str,    # "Low", "Medium", "High", "Very High"
    recommendations: List[str],        # Actionable items
    
    audit_timestamp: datetime,         # When scored
)
```

## Configuration & Extensibility

### Adding a New Stop Type

1. Add criteria to `standards.py`:
```python
ACCESSIBILITY_STANDARDS["tram_stop"] = {
    "ramp": ("Wheelchair ramp", Criticality.CRITICAL, 20),
    # ... more criteria
}
```

2. Gap scorer auto-detects via `stop.stop_type`

### Adding a New Data Source

1. Create loader in `data_loaders.py`:
```python
class MyCustomLoader(DataLoader):
    def load_stops(self) -> List[TransitStop]:
        # Your loading logic
        return stops
    
    def load_grievances(self) -> List[Grievance]:
        # Your loading logic
        return grievances
```

2. Use in pipeline:
```python
loader = MyCustomLoader(...)
stops = loader.load_stops()
```

### Switching Clustering Methods

**Current:**
```python
run_audit_pipeline(..., clustering_method='tfidf')
```

**Alternative:**
```python
run_audit_pipeline(..., clustering_method='embedding')
```

**Custom:**
- Extend `GrievanceClustering` class in `clustering.py`
- Implement custom vectorization logic
- Update `cluster_grievances()` function

## Performance Characteristics

### Time Complexity

| Operation | Input Size | Time | Notes |
|-----------|-----------|------|-------|
| Data loading | 10K records | 5s | I/O bound |
| Text preprocessing | 5K texts | 3s | Tokenization, lemmatization |
| TF-IDF vectorization | 5K texts | 2s | Vectorizer fit |
| K-means clustering | 5K vectors | 5s | K=8, n_init=10 |
| Theme labeling | 8 clusters | 1s | Keyword extraction |
| Gap scoring | 1K stops | 2s | Per-stop calculation |
| Report generation | Full audit | 1s | Aggregation |
| PDF rendering | Full report | 3s | ReportLab |
| **Total** | **1K stops + 5K grievances** | **~22s** | **Typical run** |

### Space Complexity

| Component | Memory | Notes |
|-----------|--------|-------|
| Stops (1K) | 50 MB | ~50KB per stop |
| Grievances (5K) | 100 MB | ~20KB per grievance |
| TF-IDF vectors (5K × 100) | 10 MB | Sparse matrix |
| K-means model | 5 MB | Cluster centers |
| Report objects | 20 MB | Full audit data |
| **Total** | **~185 MB** | **Single audit** |

### Scaling

**Horizontal (Multiple Cities):**
- Each city gets separate pipeline instance
- Results cached independently
- No shared state between audits

**Vertical (Single Large City):**
- Optimize clustering: reduce max_features, skip embedding
- Cache intermediate results
- Use database instead of in-memory cache
- Implement async processing

## Error Handling & Recovery

### Data Validation

**Input validation:**
- CSV schema validation
- Coordinate range checks (-90 to 90, -180 to 180)
- Severity range validation (1-5)

**Error responses:**
```python
# Invalid CSV format
HTTPException(400, "Missing required columns: ['id', 'name']")

# Invalid coordinates
HTTPException(400, "Invalid latitude: 150.0 (must be -90 to 90)")
```

### Graceful Degradation

**Insufficient data:**
- < 5 grievances: Skip clustering, treat each as separate "cluster"
- Empty grievances: Gap scores based on features only
- Missing fields: Use defaults (False for boolean flags)

**Clustering failures:**
- Low silhouette score: Still produces clusters, warns in log
- K-means non-convergence: Validates and returns best K found

## Testing Strategy

### Unit Tests

```
tests/
├── test_clustering.py         # Clustering algorithm
├── test_gap_scorer.py         # Gap scoring logic
├── test_pipeline.py           # Full pipeline
└── test_data_loaders.py       # Data ingestion (optional)
```

**Target Coverage:** 80%+ of core modules

### Integration Tests

- End-to-end pipeline with synthetic data
- CSV file upload and processing
- PDF generation

### Performance Tests

- Benchmarks for 1K-10K stops
- Clustering quality (silhouette score)
- API response times

## Future Architecture Improvements

1. **Microservices:** Decouple NLP, clustering, scoring into separate services
2. **Message Queue:** Use Celery/RabbitMQ for async processing
3. **Database:** Replace in-memory cache with PostgreSQL
4. **Caching:** Redis for result caching and rate limiting
5. **Monitoring:** Prometheus metrics and Grafana dashboards
6. **Vision Module:** FastAPI service for image analysis (Phase 2)
7. **GraphQL API:** Alternative to REST for flexible queries
8. **Multi-tenancy:** Support multiple cities per deployment

---

**Last Updated:** April 2026  
**Version:** 0.1.0
