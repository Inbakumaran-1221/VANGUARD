"""
Data loaders for transit stops and grievances from various sources.
Supports: CSV files, GTFS feeds, mock data.
"""

import csv
from datetime import datetime
from pathlib import Path
from typing import List, Tuple, Dict, Optional
import logging
import zipfile
from io import StringIO

import pandas as pd

from src.models import TransitStop, Grievance
from src.utils import (
    get_logger, validate_lat_lon, validate_severity,
    EXPECTED_STOPS_HEADERS, EXPECTED_GRIEVANCES_HEADERS, validate_csv_headers
)

logger = get_logger(__name__)


class DataLoader:
    """Base data loader class."""
    
    def load_stops(self) -> List[TransitStop]:
        """Load transit stops."""
        raise NotImplementedError
    
    def load_grievances(self) -> List[Grievance]:
        """Load grievances."""
        raise NotImplementedError


class CSVDataLoader(DataLoader):
    """Load transit stops and grievances from CSV files."""
    
    def __init__(self, stops_csv_path: Optional[str] = None, grievances_csv_path: Optional[str] = None):
        """
        Initialize CSV data loader.
        
        Args:
            stops_csv_path: Path to stops CSV file
            grievances_csv_path: Path to grievances CSV file
        """
        self.stops_csv_path = stops_csv_path
        self.grievances_csv_path = grievances_csv_path
    
    def load_stops(self) -> List[TransitStop]:
        """
        Load stops from CSV file.
        
        Returns:
            List of TransitStop objects
        
        Raises:
            FileNotFoundError: If CSV file not found
            ValueError: If CSV format is invalid
        """
        if not self.stops_csv_path or not Path(self.stops_csv_path).exists():
            logger.warning(f"Stops CSV not found: {self.stops_csv_path}")
            return []
        
        stops = []
        
        try:
            df = pd.read_csv(self.stops_csv_path)
            
            # Validate headers
            actual_headers = set(df.columns)
            is_valid, missing = validate_csv_headers(
                actual_headers, EXPECTED_STOPS_HEADERS, "stops"
            )
            
            if not is_valid:
                logger.warning(f"Missing expected headers: {missing}")
                # Try to proceed with available headers
            
            for _, row in df.iterrows():
                try:
                    # Helper function to handle pandas NaN values
                    def safe_get(row_dict, key, default=None):
                        val = row_dict.get(key, default)
                        if pd.isna(val):
                            return default
                        return val
                    
                    # Parse route_ids (may be pipe-separated or comma-separated)
                    route_ids = []
                    routes_raw = safe_get(row, 'route_ids')
                    if routes_raw:
                        routes_str = str(routes_raw)
                        route_ids = [r.strip() for r in routes_str.replace('|', ',').split(',')]
                    
                    # Parse boolean fields
                    def parse_bool(val):
                        if isinstance(val, bool):
                            return val
                        if isinstance(val, str):
                            return val.lower() in ['true', '1', 'yes', 'y']
                        if pd.isna(val):
                            return False
                        return bool(val)
                    
                    # Validate coordinates
                    lat = float(row['latitude'])
                    lon = float(row['longitude'])
                    
                    if not validate_lat_lon(lat, lon):
                        logger.warning(f"Invalid coordinates for stop {row.get('id')}: ({lat}, {lon})")
                        continue
                    
                    stop = TransitStop(
                        id=str(row['id']),
                        name=str(row['name']),
                        latitude=lat,
                        longitude=lon,
                        stop_type=str(row.get('stop_type', 'bus_stop')).lower(),
                        route_ids=route_ids,
                        has_ramp=parse_bool(row.get('has_ramp', False)),
                        has_audio_signals=parse_bool(row.get('has_audio_signals', False)),
                        has_tactile_pavement=parse_bool(row.get('has_tactile_pavement', False)),
                        has_seating=parse_bool(row.get('has_seating', False)),
                        has_lighting=parse_bool(row.get('has_lighting', False)),
                        has_staff_assistance=parse_bool(row.get('has_staff_assistance', False)),
                        has_restroom=parse_bool(row.get('has_restroom', False)),
                        has_information_board=parse_bool(row.get('has_information_board', False)),
                        accessible_entrance=parse_bool(row.get('accessible_entrance', False)),
                        level_platform=parse_bool(row.get('level_platform', False)),
                        district=safe_get(row, 'district'),
                        notes=safe_get(row, 'notes'),
                    )
                    stops.append(stop)
                
                except (ValueError, KeyError) as e:
                    logger.warning(f"Error parsing stop row: {e}, row: {row}")
                    continue
            
            logger.info(f"Loaded {len(stops)} stops from {self.stops_csv_path}")
            return stops
        
        except Exception as e:
            logger.error(f"Error loading stops CSV: {e}")
            raise ValueError(f"Failed to load stops from CSV: {e}")
    
    def load_grievances(self) -> List[Grievance]:
        """
        Load grievances from CSV file.
        
        Returns:
            List of Grievance objects
        
        Raises:
            FileNotFoundError: If CSV file not found
            ValueError: If CSV format is invalid
        """
        if not self.grievances_csv_path or not Path(self.grievances_csv_path).exists():
            logger.warning(f"Grievances CSV not found: {self.grievances_csv_path}")
            return []
        
        grievances = []
        
        try:
            df = pd.read_csv(self.grievances_csv_path)
            
            # Validate headers
            actual_headers = set(df.columns)
            is_valid, missing = validate_csv_headers(
                actual_headers, EXPECTED_GRIEVANCES_HEADERS, "grievances"
            )
            
            if not is_valid:
                logger.warning(f"Missing expected headers: {missing}")
            
            for _, row in df.iterrows():
                try:
                    # Helper function to handle pandas NaN values
                    def safe_get(row_dict, key, default=None):
                        val = row_dict.get(key, default)
                        if pd.isna(val):
                            return default
                        return val
                    
                    severity = int(safe_get(row, 'severity', 3))
                    
                    if not validate_severity(severity):
                        severity = min(max(severity, 1), 5)  # Clamp to 1-5
                    
                    # Parse timestamp
                    timestamp_str = safe_get(row, 'timestamp', datetime.now().isoformat())
                    try:
                        timestamp = datetime.fromisoformat(str(timestamp_str))
                    except (ValueError, TypeError):
                        timestamp = datetime.now()
                    
                    grievance = Grievance(
                        id=str(row['id']),
                        stop_id=str(row['stop_id']),
                        text=str(row['text']),
                        category=safe_get(row, 'category'),
                        severity=severity,
                        timestamp=timestamp,
                        submitted_by=safe_get(row, 'submitted_by'),
                        resolved=str(safe_get(row, 'resolved', 'false') or 'false').lower() in ['true', '1', 'yes'],
                    )
                    grievances.append(grievance)
                
                except (ValueError, KeyError) as e:
                    logger.warning(f"Error parsing grievance row: {e}, row: {row}")
                    continue
            
            logger.info(f"Loaded {len(grievances)} grievances from {self.grievances_csv_path}")
            return grievances
        
        except Exception as e:
            logger.error(f"Error loading grievances CSV: {e}")
            raise ValueError(f"Failed to load grievances from CSV: {e}")


class MockDataLoader(DataLoader):
    """Load pre-generated mock/demo data."""
    
    def __init__(self, stops_count: int = 50, grievances_count: int = 300):
        """
        Initialize mock data loader.
        
        Args:
            stops_count: Number of mock stops to generate
            grievances_count: Number of mock grievances to generate
        """
        self.stops_count = stops_count
        self.grievances_count = grievances_count
        self._stops = None
        self._grievances = None
    
    def load_stops(self) -> List[TransitStop]:
        """Load mock stops."""
        if self._stops is None:
            from src.data_generator import generate_synthetic_stops
            self._stops = generate_synthetic_stops(count=self.stops_count)
        return self._stops
    
    def load_grievances(self) -> List[Grievance]:
        """Load mock grievances."""
        if self._grievances is None:
            from src.data_generator import generate_synthetic_grievances
            stops = self.load_stops()  # Ensure stops loaded first
            self._grievances = generate_synthetic_grievances(stops, count=self.grievances_count)
        return self._grievances


class GTFSDataLoader(DataLoader):
    """Load transit stops from a GTFS zip feed."""

    def __init__(self, gtfs_zip_path: str):
        self.gtfs_zip_path = gtfs_zip_path

    def _read_gtfs_table(self, archive: zipfile.ZipFile, filename: str) -> List[Dict[str, str]]:
        if filename not in archive.namelist():
            return []

        with archive.open(filename) as handle:
            content = handle.read().decode("utf-8", errors="ignore")
            reader = csv.DictReader(StringIO(content))
            return list(reader)

    @staticmethod
    def _parse_bool(value: Optional[str], default: bool = False) -> bool:
        if value is None:
            return default
        return str(value).strip().lower() in {"true", "1", "yes", "y"}

    def load_stops(self) -> List[TransitStop]:
        if not self.gtfs_zip_path or not Path(self.gtfs_zip_path).exists():
            logger.warning(f"GTFS zip not found: {self.gtfs_zip_path}")
            return []

        stops: List[TransitStop] = []

        try:
            with zipfile.ZipFile(self.gtfs_zip_path, "r") as archive:
                stops_rows = self._read_gtfs_table(archive, "stops.txt")
                trips_rows = self._read_gtfs_table(archive, "trips.txt")
                stop_times_rows = self._read_gtfs_table(archive, "stop_times.txt")

            if not stops_rows:
                raise ValueError("GTFS feed is missing stops.txt")

            route_by_trip: Dict[str, str] = {
                row.get("trip_id", ""): row.get("route_id", "") for row in trips_rows if row.get("trip_id")
            }

            routes_by_stop: Dict[str, set] = {}
            for row in stop_times_rows:
                stop_id = row.get("stop_id")
                trip_id = row.get("trip_id")
                if not stop_id or not trip_id:
                    continue
                route_id = route_by_trip.get(trip_id)
                if not route_id:
                    continue
                routes_by_stop.setdefault(stop_id, set()).add(route_id)

            for row in stops_rows:
                try:
                    stop_id = str(row.get("stop_id") or row.get("id") or "").strip()
                    if not stop_id:
                        continue

                    lat = float(row.get("stop_lat", row.get("latitude", 0)) or 0)
                    lon = float(row.get("stop_lon", row.get("longitude", 0)) or 0)
                    if not validate_lat_lon(lat, lon):
                        continue

                    wheelchair_boarding = str(row.get("wheelchair_boarding", "0"))
                    has_ramp = wheelchair_boarding in {"1", "2"}

                    stop = TransitStop(
                        id=stop_id,
                        name=str(row.get("stop_name") or row.get("name") or stop_id),
                        latitude=lat,
                        longitude=lon,
                        stop_type=str(row.get("location_type", "bus_stop") or "bus_stop"),
                        route_ids=sorted(routes_by_stop.get(stop_id, set())),
                        has_ramp=has_ramp,
                        has_audio_signals=self._parse_bool(row.get("has_audio_signals"), False),
                        has_tactile_pavement=self._parse_bool(row.get("has_tactile_pavement"), False),
                        has_seating=self._parse_bool(row.get("has_seating"), False),
                        has_lighting=self._parse_bool(row.get("has_lighting"), False),
                        has_staff_assistance=self._parse_bool(row.get("has_staff_assistance"), False),
                        has_restroom=self._parse_bool(row.get("has_restroom"), False),
                        has_information_board=self._parse_bool(row.get("has_information_board"), False),
                        accessible_entrance=has_ramp,
                        level_platform=has_ramp,
                        district=row.get("zone_id") or row.get("district"),
                        notes="Loaded from GTFS feed",
                    )
                    stops.append(stop)
                except (TypeError, ValueError):
                    continue

            logger.info(f"Loaded {len(stops)} stops from GTFS zip {self.gtfs_zip_path}")
            return stops
        except Exception as e:
            logger.error(f"Error loading GTFS zip: {e}")
            raise ValueError(f"Failed to load GTFS data: {e}")

    def load_grievances(self) -> List[Grievance]:
        # GTFS feeds do not include grievance text. This is loaded from CSV or left empty.
        return []


def load_data(
    stops_source: Optional[str] = None,
    grievances_source: Optional[str] = None,
    gtfs_source: Optional[str] = None,
    use_mock: bool = False,
) -> Tuple[List[TransitStop], List[Grievance]]:
    """
    Load transit stops and grievances data.
    
    Args:
        stops_source: Path to stops CSV or 'mock'
        grievances_source: Path to grievances CSV or 'mock'
        use_mock: If True, use mock data generator
    
    Returns:
        Tuple of (stops_list, grievances_list)
    
    Raises:
        ValueError: If loading fails
    """
    if use_mock or stops_source == 'mock':
        logger.info("Using mock data loader")
        loader = MockDataLoader()
        stops = loader.load_stops()
        grievances = loader.load_grievances()
    elif gtfs_source:
        logger.info(f"Using GTFS data loader (gtfs: {gtfs_source})")
        gtfs_loader = GTFSDataLoader(gtfs_source)
        stops = gtfs_loader.load_stops()

        if grievances_source:
            grievances_loader = CSVDataLoader(stops_csv_path=None, grievances_csv_path=grievances_source)
            grievances = grievances_loader.load_grievances()
        else:
            grievances = []
    else:
        logger.info(f"Using CSV data loader (stops: {stops_source}, grievances: {grievances_source})")
        loader = CSVDataLoader(stops_source, grievances_source)

        stops = loader.load_stops()
        grievances = loader.load_grievances()
    
    logger.info(f"Loaded {len(stops)} stops and {len(grievances)} grievances")
    
    return stops, grievances
