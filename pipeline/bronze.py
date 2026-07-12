"""Bronze layer: stream export.xml into columnar Parquet.

Uses ElementTree.iterparse so memory stays constant regardless of export size
(a multi-year export is easily 250MB+ of XML). Everything is kept as strings —
bronze preserves what Apple exported; typing and validation happen in silver.

The <device> attribute is intentionally dropped: it is a ~200-char repeated
debug blob whose useful part (source) is already in sourceName.

Workouts need flattening: modern exports carry energy/distance in nested
<WorkoutStatistics> elements, not attributes on <Workout> itself.
"""
import logging
import xml.etree.ElementTree as ET
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from . import config

log = logging.getLogger(__name__)

BATCH_SIZE = 100_000

RECORD_SCHEMA = pa.schema(
    [
        ("type", pa.string()),
        ("source_name", pa.string()),
        ("unit", pa.string()),
        ("creation_date", pa.string()),
        ("start_date", pa.string()),
        ("end_date", pa.string()),
        ("value", pa.string()),
    ]
)

WORKOUT_SCHEMA = pa.schema(
    [
        ("activity_type", pa.string()),
        ("source_name", pa.string()),
        ("duration_min", pa.string()),
        ("start_date", pa.string()),
        ("end_date", pa.string()),
        ("active_energy_kcal", pa.string()),
        ("distance_km", pa.string()),
        ("indoor", pa.string()),
    ]
)

_RECORD_FIELDS = (
    ("type", "type"),
    ("source_name", "sourceName"),
    ("unit", "unit"),
    ("creation_date", "creationDate"),
    ("start_date", "startDate"),
    ("end_date", "endDate"),
    ("value", "value"),
)


class _BatchedWriter:
    """Accumulates dict-rows and flushes them to a ParquetWriter in batches."""

    def __init__(self, path: Path, schema: pa.Schema):
        self.schema = schema
        self.writer = pq.ParquetWriter(path, schema, compression="zstd")
        self.rows: list[dict] = []
        self.total = 0

    def append(self, row: dict) -> None:
        self.rows.append(row)
        if len(self.rows) >= BATCH_SIZE:
            self.flush()

    def flush(self) -> None:
        if self.rows:
            self.writer.write_table(pa.Table.from_pylist(self.rows, schema=self.schema))
            self.total += len(self.rows)
            self.rows = []

    def close(self) -> int:
        self.flush()
        self.writer.close()
        return self.total


def _parse_workout(elem: ET.Element) -> dict:
    """Flatten a <Workout> element, summing nested WorkoutStatistics."""
    energy = 0.0
    distance = 0.0
    indoor = None
    for child in elem:
        if child.tag == "WorkoutStatistics":
            stat_type = child.attrib.get("type", "")
            try:
                total = float(child.attrib.get("sum", ""))
            except ValueError:
                continue
            if stat_type == "HKQuantityTypeIdentifierActiveEnergyBurned":
                energy += total
            elif stat_type.startswith("HKQuantityTypeIdentifierDistance"):
                distance += total
        elif child.tag == "MetadataEntry" and child.attrib.get("key") == "HKIndoorWorkout":
            indoor = child.attrib.get("value")
    return {
        "activity_type": elem.attrib.get("workoutActivityType"),
        "source_name": elem.attrib.get("sourceName"),
        "duration_min": elem.attrib.get("duration"),
        "start_date": elem.attrib.get("startDate"),
        "end_date": elem.attrib.get("endDate"),
        "active_energy_kcal": str(energy) if energy else None,
        "distance_km": str(distance) if distance else None,
        "indoor": indoor,
    }


def ingest(xml_path: str | Path) -> dict:
    """Stream the export XML into bronze Parquet. Returns row counts."""
    xml_path = Path(xml_path)
    if not xml_path.exists():
        raise FileNotFoundError(f"export not found: {xml_path}")

    config.ensure_dirs()
    records = _BatchedWriter(config.BRONZE_RECORDS, RECORD_SCHEMA)
    workouts = _BatchedWriter(config.BRONZE_WORKOUTS, WORKOUT_SCHEMA)

    log.info("bronze: streaming %s", xml_path)
    context = ET.iterparse(str(xml_path), events=("start", "end"))
    _, root = next(context)  # grab root so we can clear processed children

    # Workout elements have Record-like children; only clear at their close.
    workout_depth = 0
    for event, elem in context:
        if event == "start":
            if elem.tag == "Workout":
                workout_depth += 1
            continue
        if elem.tag == "Workout":
            workout_depth -= 1
            workouts.append(_parse_workout(elem))
            elem.clear()
            root.clear()
        elif elem.tag == "Record" and workout_depth == 0:
            records.append({dst: elem.attrib.get(src) for dst, src in _RECORD_FIELDS})
            elem.clear()
            root.clear()

    counts = {"bronze_records": records.close(), "bronze_workouts": workouts.close()}
    log.info("bronze: wrote %(bronze_records)d records, %(bronze_workouts)d workouts", counts)
    return counts
