"""
Data generation for synthetic transit stops and grievances.
Used for demo and testing purposes.
"""

import csv
from datetime import datetime, timedelta
from pathlib import Path
import random
from typing import List

from src.models import TransitStop, Grievance
from src.utils import generate_id, SUPPORTED_STOP_TYPES


# Sample grievance templates
GRIEVANCE_TEMPLATES = [
    "No ramp at entrance, very difficult for wheelchair users",
    "Audio signals are not working at the crossing",
    "Tactile pavement is missing, blind users can't navigate",
    "Very dark at night, feels unsafe",
    "Only one bench, not enough seating for elderly users",
    "No information board about routes, very confusing",
    "Staff not available, I needed help with my walker",
    "Restroom is not accessible, door too narrow",
    "Platform is at an angle, difficult for mobility users",
    "No audio announcements, deaf users can't know route info",
    "Muddy area, tactile guide is covered",
    "Lighting is broken, can't see properly",
    "No seating in waiting area",
    "Broken wheelchair ramp, can't be used",
    "Audio alert is too quiet, can't hear it",
    "Steps at entrance, no alternative for disabled",
    "Crowded seating area, people with crutches can't sit",
    "Information board text is too small",
    "No staff during night shifts when I arrive",
    "Accessible restroom locked, I couldn't use it",
]

# Stop names and districts
STOP_NAMES = [
    "Central Station", "Main Square", "University Station", "Hospital Cross",
    "Market Plaza", "riverside", "North Terminal", "South Gate",
    "East End", "West Point", "Airport Connector", "Downtown Hub",
    "Commerce Center", "Civic Building", "Park Avenue", "Beach Street",
    "Library Stop", "Museum District", "Sports Arena", "Train Depot",
    "Transit Center", "Bus Terminal", "Metro Link", "Interchange",
    "Business Park", "Industrial Area", "Residential Zone", "Shopping Mall",
    "Community Center", "School District", "University Campus", "Government Plaza",
    "Medical Center", "Tech Park", "Cultural District", "Arts Quarter",
    "Waterfront", "Marina", "Botanical Garden", "Historic District",
]

DISTRICTS = ["North", "South", "East", "West", "Central", "Downtown", "Suburbs"]


def generate_synthetic_stops(count: int = 50, seed: int = 42) -> List[TransitStop]:
    """
    Generate synthetic transit stops.
    
    Args:
        count: Number of stops to generate
        seed: Random seed for reproducibility
    
    Returns:
        List of TransitStop objects
    """
    random.seed(seed)
    stops = []
    
    # Simulate a city grid (roughly 10km x 10km)
    center_lat, center_lon = 40.7128, -74.0060  # NYC coordinates as example
    
    for i in range(count):
        # Generate clustered locations (some in central area, some in suburbs)
        if random.random() < 0.6:  # 60% in central area
            lat = center_lat + random.uniform(-0.05, 0.05)  # ~5km radius
            lon = center_lon + random.uniform(-0.05, 0.05)
        else:  # 40% in suburbs
            lat = center_lat + random.uniform(-0.1, 0.1)
            lon = center_lon + random.uniform(-0.1, 0.1)
        
        # Randomly assign accessibility features (some stops better than others)
        has_ramp = random.random() < 0.5
        has_audio = random.random() < 0.35
        has_tactile = random.random() < 0.3
        has_seating = random.random() < 0.6
        has_lighting = random.random() < 0.5
        has_staff = random.random() < 0.2
        has_restroom = random.random() < 0.15
        has_info = random.random() < 0.4
        accessible_entrance = has_ramp and random.random() < 0.9
        level = has_ramp or random.random() < 0.4
        
        stop = TransitStop(
            id=f"STOP_{i+1:04d}",
            name=random.choice(STOP_NAMES),
            latitude=lat,
            longitude=lon,
            stop_type=random.choice(["bus_stop", "metro_station"]),
            route_ids=[f"R{random.randint(1, 30):02d}" for _ in range(random.randint(1, 3))],
            has_ramp=has_ramp,
            has_audio_signals=has_audio,
            has_tactile_pavement=has_tactile,
            has_seating=has_seating,
            has_lighting=has_lighting,
            has_staff_assistance=has_staff,
            has_restroom=has_restroom,
            has_information_board=has_info,
            accessible_entrance=accessible_entrance,
            level_platform=level,
            district=random.choice(DISTRICTS),
        )
        stops.append(stop)
    
    return stops


def generate_synthetic_grievances(stops: List[TransitStop], count: int = 300, seed: int = 42) -> List[Grievance]:
    """
    Generate synthetic grievances associated with stops.
    
    Args:
        stops: List of TransitStop objects
        count: Number of grievances to generate
        seed: Random seed
    
    Returns:
        List of Grievance objects
    """
    random.seed(seed)
    grievances = []
    
    # Generate grievances spanning the last 180 days
    start_date = datetime.now() - timedelta(days=180)
    
    for i in range(count):
        stop = random.choice(stops)
        
        # Bias: stops with fewer accessibility features get more grievances
        accessible_features_count = sum([
            stop.has_ramp,
            stop.has_audio_signals,
            stop.has_tactile_pavement,
            stop.has_seating,
            stop.has_lighting,
            stop.has_staff_assistance,
            stop.has_restroom,
            stop.has_information_board,
        ])
        
        # Higher probability of grievance for inaccessible stops
        grievance_prob = 1.0 - (accessible_features_count / 8.0)
        
        # Don't always generate for every stop; skip some
        if random.random() > grievance_prob * 1.5:
            continue
        
        timestamp = start_date + timedelta(
            days=random.randint(0, 180),
            hours=random.randint(0, 23),
            minutes=random.randint(0, 59)
        )
        
        grievance = Grievance(
            id=f"GRIEVANCE_{i+1:05d}",
            stop_id=stop.id,
            text=random.choice(GRIEVANCE_TEMPLATES),
            severity=random.choice([2, 3, 4, 5, 5, 5]),  # Bias towards higher severity
            timestamp=timestamp,
            submitted_by=f"USER_{random.randint(1000, 9999)}",
            resolved=random.random() < 0.2,  # 20% resolved
        )
        grievances.append(grievance)
    
    return grievances


def save_stops_to_csv(stops: List[TransitStop], filepath: str) -> None:
    """
    Save TransitStop objects to CSV.
    
    Args:
        stops: List of TransitStop objects
        filepath: Output CSV filepath
    """
    Path(filepath).parent.mkdir(parents=True, exist_ok=True)
    
    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        fieldnames = [
            'id', 'name', 'latitude', 'longitude', 'stop_type',
            'route_ids', 'has_ramp', 'has_audio_signals', 'has_tactile_pavement',
            'has_seating', 'has_lighting', 'has_staff_assistance',
            'has_restroom', 'has_information_board', 'accessible_entrance',
            'level_platform', 'district', 'notes'
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        
        for stop in stops:
            writer.writerow({
                'id': stop.id,
                'name': stop.name,
                'latitude': stop.latitude,
                'longitude': stop.longitude,
                'stop_type': stop.stop_type,
                'route_ids': '|'.join(stop.route_ids),
                'has_ramp': stop.has_ramp,
                'has_audio_signals': stop.has_audio_signals,
                'has_tactile_pavement': stop.has_tactile_pavement,
                'has_seating': stop.has_seating,
                'has_lighting': stop.has_lighting,
                'has_staff_assistance': stop.has_staff_assistance,
                'has_restroom': stop.has_restroom,
                'has_information_board': stop.has_information_board,
                'accessible_entrance': stop.accessible_entrance,
                'level_platform': stop.level_platform,
                'district': stop.district,
                'notes': stop.notes or '',
            })


def save_grievances_to_csv(grievances: List[Grievance], filepath: str) -> None:
    """
    Save Grievance objects to CSV.
    
    Args:
        grievances: List of Grievance objects
        filepath: Output CSV filepath
    """
    Path(filepath).parent.mkdir(parents=True, exist_ok=True)
    
    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        fieldnames = ['id', 'stop_id', 'text', 'category', 'severity', 'timestamp', 'submitted_by', 'resolved']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        
        for grievance in grievances:
            writer.writerow({
                'id': grievance.id,
                'stop_id': grievance.stop_id,
                'text': grievance.text,
                'category': grievance.category or '',
                'severity': grievance.severity,
                'timestamp': grievance.timestamp.isoformat(),
                'submitted_by': grievance.submitted_by or '',
                'resolved': grievance.resolved,
            })


if __name__ == "__main__":
    # Generate demo data
    stops = generate_synthetic_stops(count=50)
    grievances = generate_synthetic_grievances(stops, count=300)
    
    # Save to CSV
    save_stops_to_csv(stops, 'data/demo_stops.csv')
    save_grievances_to_csv(grievances, 'data/demo_grievances.csv')
    
    print(f"Generated {len(stops)} stops and {len(grievances)} grievances")
    print("Saved to data/demo_stops.csv and data/demo_grievances.csv")
