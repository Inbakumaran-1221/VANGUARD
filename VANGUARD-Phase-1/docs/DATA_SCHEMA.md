# Data Schema & Format Specifications

## CSV Input Formats

### stops.csv

Transit stop/station data. One record per stop.

**Required Columns:**

| Column | Type | Description | Example |
|--------|------|-------------|---------|
| `id` | string | Unique stop identifier | `STOP_0001` |
| `name` | string | Stop/station name | `Main Street Station` |
| `latitude` | float | GPS latitude (-90 to 90) | `40.7128` |
| `longitude` | float | GPS longitude (-180 to 180) | `-74.0060` |
| `stop_type` | string | Type of stop (bus_stop, metro_station, tram_stop, train_station) | `metro_station` |

**Optional Columns (Accessibility Features):**

All boolean (true/false):

| Column | Description | Default |
|--------|-------------|---------|
| `has_ramp` | Wheelchair ramp or level platform present | false |
| `has_audio_signals` | Audio signals at crossing/platform | false |
| `has_tactile_pavement` | Tactile guidance pavement for blind users | false |
| `has_seating` | Benches or seating area available | false |
| `has_lighting` | Adequate lighting (≥50 lux) | false |
| `has_staff_assistance` | Staff available for assistance | false |
| `has_restroom` | Accessible restroom facility | false |
| `has_information_board` | Accessible route information board | false |
| `accessible_entrance` | Clear, accessible main entrance | false |
| `level_platform` | Platform level with vehicle (no steep steps) | false |
| `district` | Administrative district/area | null |
| `route_ids` | Pipe or comma-separated route IDs (e.g., "R01\|R02\|R03") | "" |
| `notes` | Additional notes or comments | null |

**Example:**

```csv
id,name,latitude,longitude,stop_type,route_ids,has_ramp,has_audio_signals,has_tactile_pavement,has_seating,has_lighting,has_staff_assistance,has_restroom,has_information_board,accessible_entrance,level_platform,district,notes
STOP_0001,Central Station,40.7128,-74.0060,metro_station,"R01|R02|R03",true,true,true,true,true,true,true,true,true,true,Central,"Recently renovated"
STOP_0002,Market Plaza,40.7200,-74.0100,bus_stop,"R05|R12",false,false,true,false,true,false,false,false,false,false,Downtown,"Pending accessibility upgrade"
STOP_0003,University Ave,40.7100,-74.0080,bus_stop,"R08",true,true,false,true,false,false,false,true,true,false,North,"Staff on weekdays only"
```

### grievances.csv

Citizen complaints about accessibility. One record per complaint.

**Required Columns:**

| Column | Type | Description | Example |
|--------|------|-------------|---------|
| `id` | string | Unique grievance identifier | `GRIEVANCE_00001` |
| `stop_id` | string | ID of affected stop (must match stops.csv) | `STOP_0001` |
| `text` | string | Complaint text (preferably >20 characters) | `No ramp at entrance, very difficult for wheelchair users` |
| `severity` | integer | Severity level 1-5 (1=minor, 5=critical) | `4` |
| `timestamp` | string (ISO 8601) | When complaint was submitted | `2025-10-15T14:30:00` or `2025-10-15 14:30:00` |

**Optional Columns:**

| Column | Type | Description | Default |
|--------|------|-------------|---------|
| `category` | string | Pre-categorized issue type | null |
| `submitted_by` | string | Anonymized user ID | null |
| `resolved` | boolean | Whether issue was addressed | false |

**Example:**

```csv
id,stop_id,text,category,severity,timestamp,submitted_by,resolved
GRIEVANCE_00001,STOP_0001,"No ramp at entrance, very difficult for wheelchair users",,4,2025-10-15T14:30:00,USER_1234,false
GRIEVANCE_00002,STOP_0001,"Audio signals are not working at the crossing",,5,2025-10-16T09:15:00,USER_5678,false
GRIEVANCE_00003,STOP_0002,"Very dark at night, no lighting in waiting area",,3,2025-10-17T20:45:00,USER_9012,true
GRIEVANCE_00004,STOP_0003,"Only one bench, not enough seating for elderly people",,2,2025-10-18T11:22:00,USER_3456,false
```

## JSON Output Formats

### Report Summary (GET /report/{job_id})

```json
{
  "report_id": "AUDIT_20261015_abc123",
  "city": "Sample City",
  "generated_at": "2025-10-15T20:30:45.123456",
  "total_stops_audited": 100,
  "total_grievances_analyzed": 500,
  "coverage_percent": 95.5,
  "stops_by_priority": {
    "CRITICAL": 15,
    "HIGH": 28,
    "MEDIUM": 42,
    "LOW": 15
  },
  "avg_gap_score": 45.3,
  "key_findings": [
    "15 stops have CRITICAL accessibility gaps requiring immediate intervention",
    "Average accessibility gap score is 45.3/100, indicating moderate citywide accessibility challenges",
    "Most common accessibility issue: 'Missing Ramp' (127 complaints)"
  ],
  "recommendations": [
    "Prioritize remediation of stops with CRITICAL gaps",
    "Focus on top accessibility issues identified in grievance analysis",
    "Implement staff training and 24/7 assistance programs at key hubs"
  ],
  "generation_time_seconds": 22.5
}
```

### Stops List (GET /stops/{job_id})

```json
{
  "total_count": 100,
  "skip": 0,
  "limit": 20,
  "stops": [
    {
      "stop_id": "STOP_0001",
      "stop_name": "Central Station",
      "latitude": 40.7128,
      "longitude": -74.0060,
      "gap_score": 85.5,
      "priority_level": "CRITICAL",
      "grievance_count": 23,
      "top_themes": [
        "Missing Ramp",
        "No Audio Signals",
        "Poor Lighting"
      ],
      "recommendations": [
        "Install wheelchair ramp complying with local standards",
        "Install audio signal system at crossing"
      ],
      "remediation_cost": "High ($20K-$60K)"
    },
    {
      "stop_id": "STOP_0002",
      "stop_name": "Market Plaza",
      "latitude": 40.7200,
      "longitude": -74.0100,
      "gap_score": 42.1,
      "priority_level": "MEDIUM",
      "grievance_count": 8,
      "top_themes": [
        "Poor Lighting"
      ],
      "recommendations": [
        "Upgrade to LED lighting (≥50 lux minimum)"
      ],
      "remediation_cost": "Medium ($5K-$20K)"
    }
  ]
}
```

### Grievance Themes (GET /themes/{job_id})

```json
{
  "total_clusters": 6,
  "themes": [
    {
      "cluster_id": 0,
      "theme": "Missing Ramp",
      "count": 127,
      "top_keywords": ["ramp", "wheelchair", "access", "stairs", "level"],
      "silhouette_score": 0.42
    },
    {
      "cluster_id": 1,
      "theme": "No Audio Signals",
      "count": 94,
      "top_keywords": ["audio", "signal", "deaf", "hear", "announcement"],
      "silhouette_score": 0.38
    },
    {
      "cluster_id": 2,
      "theme": "Poor Lighting",
      "count": 87,
      "top_keywords": ["light", "dark", "brightness", "shadow", "visibility"],
      "silhouette_score": 0.45
    }
  ]
}
```

### Priority Map (GET /priority-map/{job_id})

```json
{
  "map_data": {
    "CRITICAL": [
      {
        "stop_id": "STOP_0001",
        "stop_name": "Central Station",
        "latitude": 40.7128,
        "longitude": -74.0060,
        "gap_score": 85.5,
        "grievances": 23
      },
      {
        "stop_id": "STOP_0010",
        "stop_name": "North Terminal",
        "latitude": 40.7300,
        "longitude": -74.0200,
        "gap_score": 82.1,
        "grievances": 19
      }
    ],
    "HIGH": [
      {
        "stop_id": "STOP_0002",
        "stop_name": "Market Plaza",
        "latitude": 40.7200,
        "longitude": -74.0100,
        "gap_score": 72.3,
        "grievances": 15
      }
    ],
    "MEDIUM": [...],
    "LOW": [...]
  },
  "total_stops": 100,
  "center_latitude": 40.7200,
  "center_longitude": -74.0100
}
```

## Accessibility Standards Reference

### Stop Type: bus_stop

Features and weights (total = 100):

| Feature | Description | Weight | Criticality |
|---------|-------------|--------|-------------|
| `ramp` | Wheelchair ramp or level platform at entry | 20 | CRITICAL |
| `accessible_entrance` | Clear, accessible entrance | 15 | CRITICAL |
| `audio_signals` | Audio signals for crossing | 15 | CRITICAL |
| `information_board` | Accessible route information | 12 | IMPORTANT |
| `tactile_pavement` | Tactile guidance pavement | 12 | IMPORTANT |
| `seating` | Benches/seating areas (min 2) | 10 | IMPORTANT |
| `lighting` | Adequate lighting (≥50 lux) | 10 | IMPORTANT |
| `staff_assistance` | Staff availability | 8 | NICE_TO_HAVE |
| `restroom` | Accessible restroom within 100m | 8 | NICE_TO_HAVE |

### Stop Type: metro_station

| Feature | Description | Weight | Criticality |
|---------|-------------|--------|-------------|
| `ramp` | Elevator or ramp to platform | 20 | CRITICAL |
| `accessible_entrance` | Level entrance to station | 15 | CRITICAL |
| `audio_signals` | Audio announcements & signals | 15 | CRITICAL |
| `information_board` | Accessible service information | 12 | IMPORTANT |
| `tactile_pavement` | Tactile guidance on platforms | 12 | IMPORTANT |
| `seating` | Benches/seating in station | 10 | IMPORTANT |
| `lighting` | Platform/tunnel lighting | 10 | IMPORTANT |
| `staff_assistance` | Staff at key locations | 8 | NICE_TO_HAVE |
| `restroom` | Accessible restroom | 8 | NICE_TO_HAVE |

## Gap Score Calculation

### Formula

```
gap_score = (missing_weight / total_weight) × 100 + grievance_boost

Where:
- missing_weight = sum of weights for features NOT present
- total_weight = sum of all feature weights for stop type
- grievance_boost = min(grievance_count × 2, 10)
- Final score clamped to 0-100
```

### Example

**Bus Stop: Central Station**

Features present: ramp (20), audio_signals (15), seating (10), lighting (10), staff (8) = 63/100

```
gap_score = (37 / 100) × 100 + (23 × 2 capped at 10)
          = 37 + 10
          = 47 (MEDIUM priority)
```

## Priority Level Thresholds

| Priority | Gap Score | Intervention Timeline | Action Type |
|----------|-----------|----------------------|-------------|
| CRITICAL | ≥ 80 | Immediate (0-2 weeks) | Emergency remediation |
| HIGH | 60-79 | Urgent (1-3 months) | Planned intervention |
| MEDIUM | 40-59 | Planned (3-6 months) | Schedule remediation |
| LOW | < 40 | Monitor | Annual review |

## Remediation Cost Estimates

Based on typical accessibility improvements:

| Feature | Typical Cost | Notes |
|---------|-------------|-------|
| Ramp | $5K-$15K | Medium |
| Audio Signals | $10K-$30K | High (complex electrical) |
| Tactile Pavement | $8K-$20K | Medium |
| Seating | $1K-$3K | Low (simple furniture) |
| Lighting | $3K-$10K | Medium |
| Staff Training | $2K-$5K/year | Low (recurring) |
| Restroom | $30K-$100K | Very High (construction) |
| Info Board | $2K-$8K | Low |
| Accessible Entrance | $15K-$50K | High (construction/design) |

**Overall Estimation:**
- Low: $1K-$5K (typically: seating, info boards)
- Medium: $5K-$20K (typically: ramp, lighting, tactile)
- High: $20K-$60K (typically: audio, entrance, multiple items)
- Very High: $60K+ (typically: restroom + structural work)

## Data Quality Considerations

### Validation Rules

**Coordinates:**
- Latitude: -90 ≤ value ≤ 90
- Longitude: -180 ≤ value ≤ 180

**Severity:**
- Must be integer: 1, 2, 3, 4, or 5

**Timestamp:**
- ISO 8601 format: YYYY-MM-DDTHH:MM:SS or YYYY-MM-DD HH:MM:SS

**Text Fields:**
- Minimum 5 characters (after cleaning)
- Maximum 2000 characters

### Missing Data Handling

| Field | Handling |
|-------|----------|
| Optional boolean | Default: false |
| Optional string | Default: null |
| route_ids | Default: empty list |
| Timestamp (grievance) | Default: current datetime |

### Data Issues Detected

System logs warnings for:
- Missing required columns
- Out-of-range values
- Duplicate IDs
- Orphaned grievances (stop_id not in stops list)
- Text too short/long

Continues processing, skips problematic records.

---

**Last Updated:** April 2026  
**Version:** 0.1.0
