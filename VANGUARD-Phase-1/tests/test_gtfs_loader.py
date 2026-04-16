"""Tests for GTFS data loader support."""

import csv
import tempfile
import zipfile
from pathlib import Path

from src.data_loaders import load_data


def _write_csv_to_zip(archive: zipfile.ZipFile, name: str, rows, fieldnames):
    from io import StringIO

    buffer = StringIO()
    writer = csv.DictWriter(buffer, fieldnames=fieldnames)
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    archive.writestr(name, buffer.getvalue())


def test_gtfs_loader_reads_stops_and_routes():
    temp_dir = Path(tempfile.mkdtemp())
    gtfs_zip = temp_dir / "feed.zip"

    with zipfile.ZipFile(gtfs_zip, "w") as archive:
        _write_csv_to_zip(
            archive,
            "stops.txt",
            [
                {"stop_id": "STOP_A", "stop_name": "Alpha", "stop_lat": "40.1", "stop_lon": "-73.9", "wheelchair_boarding": "1"},
                {"stop_id": "STOP_B", "stop_name": "Beta", "stop_lat": "40.2", "stop_lon": "-74.0", "wheelchair_boarding": "0"},
            ],
            ["stop_id", "stop_name", "stop_lat", "stop_lon", "wheelchair_boarding"],
        )
        _write_csv_to_zip(
            archive,
            "trips.txt",
            [
                {"route_id": "R1", "service_id": "WK", "trip_id": "T1"},
                {"route_id": "R2", "service_id": "WK", "trip_id": "T2"},
            ],
            ["route_id", "service_id", "trip_id"],
        )
        _write_csv_to_zip(
            archive,
            "stop_times.txt",
            [
                {"trip_id": "T1", "arrival_time": "08:00:00", "departure_time": "08:00:00", "stop_id": "STOP_A", "stop_sequence": "1"},
                {"trip_id": "T2", "arrival_time": "08:10:00", "departure_time": "08:10:00", "stop_id": "STOP_B", "stop_sequence": "1"},
            ],
            ["trip_id", "arrival_time", "departure_time", "stop_id", "stop_sequence"],
        )

    stops, grievances = load_data(gtfs_source=str(gtfs_zip))

    assert len(stops) == 2
    assert len(grievances) == 0
    assert any(s.id == "STOP_A" and "R1" in s.route_ids for s in stops)
