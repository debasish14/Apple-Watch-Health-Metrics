"""Central configuration for the health data pipeline.

All artifacts live under DATA_DIR (default ./data, override with env var):

    data/
      bronze/   raw-but-columnar Parquet, stringly typed, straight from XML
      silver/   typed, deduplicated, validated Parquet
      gold/     health.duckdb with pre-aggregated serving tables
      quality/  per-run data-quality reports (JSON)
"""
import os
from pathlib import Path

DATA_DIR = Path(os.environ.get("HEALTH_DATA_DIR", "data"))

BRONZE_DIR = DATA_DIR / "bronze"
SILVER_DIR = DATA_DIR / "silver"
GOLD_DIR = DATA_DIR / "gold"
QUALITY_DIR = DATA_DIR / "quality"

BRONZE_RECORDS = BRONZE_DIR / "records.parquet"
BRONZE_WORKOUTS = BRONZE_DIR / "workouts.parquet"

SILVER_RECORDS = SILVER_DIR / "records.parquet"
SILVER_SLEEP = SILVER_DIR / "sleep.parquet"
SILVER_WORKOUTS = SILVER_DIR / "workouts.parquet"

GOLD_DB = GOLD_DIR / "health.duckdb"

# Quantity record types promoted to silver/gold. Everything else still lands
# in bronze so widening coverage later is a silver/gold change only.
QUANTITY_TYPES = {
    "HKQuantityTypeIdentifierHeartRate": "heart_rate",
    "HKQuantityTypeIdentifierRestingHeartRate": "resting_heart_rate",
    "HKQuantityTypeIdentifierHeartRateVariabilitySDNN": "hrv_sdnn",
    "HKQuantityTypeIdentifierVO2Max": "vo2max",
    "HKQuantityTypeIdentifierBodyMass": "body_mass",
    "HKQuantityTypeIdentifierStepCount": "step_count",
    "HKQuantityTypeIdentifierActiveEnergyBurned": "active_energy",
    "HKQuantityTypeIdentifierBasalEnergyBurned": "basal_energy",
    "HKQuantityTypeIdentifierDistanceWalkingRunning": "distance_walking_running",
    "HKQuantityTypeIdentifierAppleExerciseTime": "exercise_minutes",
    "HKQuantityTypeIdentifierRespiratoryRate": "respiratory_rate",
    "HKQuantityTypeIdentifierTimeInDaylight": "time_in_daylight",
}

SLEEP_TYPE = "HKCategoryTypeIdentifierSleepAnalysis"

# Sleep stages that count as actually asleep (vs InBed / Awake).
ASLEEP_STAGES = (
    "HKCategoryValueSleepAnalysisAsleepCore",
    "HKCategoryValueSleepAnalysisAsleepDeep",
    "HKCategoryValueSleepAnalysisAsleepREM",
    "HKCategoryValueSleepAnalysisAsleepUnspecified",
)

# Cumulative metrics are reported by both iPhone and Apple Watch for the same
# activity; summing across sources double counts. Per day we keep the single
# source with the largest total (a simplification of Apple's interval merge).
DEDUP_BY_SOURCE_TYPES = (
    "HKQuantityTypeIdentifierStepCount",
    "HKQuantityTypeIdentifierActiveEnergyBurned",
    "HKQuantityTypeIdentifierBasalEnergyBurned",
    "HKQuantityTypeIdentifierDistanceWalkingRunning",
)


def ensure_dirs() -> None:
    for d in (BRONZE_DIR, SILVER_DIR, GOLD_DIR, QUALITY_DIR):
        d.mkdir(parents=True, exist_ok=True)
