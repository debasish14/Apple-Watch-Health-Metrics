"""Gold layer: pre-aggregated serving tables in a DuckDB database.

The API reads these tables verbatim — no aggregation happens at request
time. Rebuilt from scratch on every pipeline run (idempotent).

Double-counting note: cumulative metrics (steps, energy, distance) arrive
from both iPhone and Apple Watch for the same physical activity. Summing
everything would inflate totals ~2x. Per (type, day) we keep the one source
with the largest daily total — a pragmatic stand-in for Apple's proper
interval-overlap merge, and roughly the number the Fitness app shows.

DDL can't take prepared parameters in DuckDB; inlined values are trusted
config constants (see silver._sql_str).
"""
import logging

import duckdb

from . import config
from .silver import _sql_list, _sql_str

log = logging.getLogger(__name__)


def build() -> dict:
    """(Re)build all gold tables. Returns per-table row counts."""
    config.ensure_dirs()
    con = duckdb.connect(str(config.GOLD_DB))
    con.execute(
        f"CREATE OR REPLACE VIEW _silver AS SELECT * FROM read_parquet({_sql_str(config.SILVER_RECORDS)})"
    )
    con.execute(
        f"CREATE OR REPLACE VIEW _sleep AS SELECT * FROM read_parquet({_sql_str(config.SILVER_SLEEP)})"
    )
    con.execute(
        f"CREATE OR REPLACE VIEW _workouts AS SELECT * FROM read_parquet({_sql_str(config.SILVER_WORKOUTS)})"
    )

    # -- point-in-time metrics: daily avg/min/max ---------------------------
    for table, hk_type in [
        ("gold_daily_heart_rate", "HKQuantityTypeIdentifierHeartRate"),
        ("gold_daily_resting_hr", "HKQuantityTypeIdentifierRestingHeartRate"),
        ("gold_daily_hrv", "HKQuantityTypeIdentifierHeartRateVariabilitySDNN"),
        ("gold_daily_respiratory_rate", "HKQuantityTypeIdentifierRespiratoryRate"),
    ]:
        con.execute(
            f"""
            CREATE OR REPLACE TABLE {table} AS
            SELECT local_date,
                   round(avg(value), 1) AS avg_value,
                   round(min(value), 1) AS min_value,
                   round(max(value), 1) AS max_value,
                   count(*)             AS n_samples
            FROM _silver WHERE type = {_sql_str(hk_type)}
            GROUP BY local_date ORDER BY local_date
            """
        )

    # -- sparse measurements: one averaged reading per day --------------------
    for table, hk_type in [
        ("gold_vo2max", "HKQuantityTypeIdentifierVO2Max"),
        ("gold_weight", "HKQuantityTypeIdentifierBodyMass"),
    ]:
        con.execute(
            f"""
            CREATE OR REPLACE TABLE {table} AS
            SELECT local_date, round(avg(value), 2) AS value
            FROM _silver WHERE type = {_sql_str(hk_type)}
            GROUP BY local_date ORDER BY local_date
            """
        )

    # -- cumulative metrics: best-source-per-day (see module docstring) -------
    con.execute(
        f"""
        CREATE OR REPLACE TABLE gold_daily_activity AS
        WITH per_source AS (
            SELECT type, local_date, source_name, sum(value) AS total
            FROM _silver
            WHERE type IN {_sql_list(config.DEDUP_BY_SOURCE_TYPES)}
            GROUP BY ALL
        ),
        best AS (
            SELECT type, local_date, max(total) AS total
            FROM per_source GROUP BY type, local_date
        )
        SELECT local_date,
            round(max(total) FILTER (type = 'HKQuantityTypeIdentifierStepCount'))          AS steps,
            round(max(total) FILTER (type = 'HKQuantityTypeIdentifierActiveEnergyBurned')) AS active_kcal,
            round(max(total) FILTER (type = 'HKQuantityTypeIdentifierBasalEnergyBurned'))  AS basal_kcal,
            round(max(total) FILTER (type = 'HKQuantityTypeIdentifierDistanceWalkingRunning'), 2) AS distance_km
        FROM best
        GROUP BY local_date ORDER BY local_date
        """
    )

    # -- calendar heatmap: GitHub-style intensity levels -----------------------
    # Level 1-4 = quartile of the metric across the user's active (non-zero)
    # days, so colors are relative to their own typical day; 0 = no activity.
    # Precomputed here so the frontend never derives analytics client-side.
    con.execute(
        """
        CREATE OR REPLACE TABLE gold_daily_calendar AS
        WITH kcal_ranked AS (
            SELECT local_date, ntile(4) OVER (ORDER BY active_kcal) AS lvl
            FROM gold_daily_activity WHERE active_kcal > 0
        ),
        steps_ranked AS (
            SELECT local_date, ntile(4) OVER (ORDER BY steps) AS lvl
            FROM gold_daily_activity WHERE steps > 0
        )
        SELECT a.local_date, a.steps, a.active_kcal, a.distance_km,
               coalesce(k.lvl, 0) AS level_kcal,
               coalesce(s.lvl, 0) AS level_steps
        FROM gold_daily_activity a
        LEFT JOIN kcal_ranked k USING (local_date)
        LEFT JOIN steps_ranked s USING (local_date)
        ORDER BY local_date
        """
    )

    # -- sleep: minutes per stage per night ------------------------------------
    con.execute(
        f"""
        CREATE OR REPLACE TABLE gold_daily_sleep AS
        SELECT local_date,
               sum(minutes) FILTER (stage IN {_sql_list(config.ASLEEP_STAGES)}) AS asleep_min,
               sum(minutes) FILTER (stage = 'HKCategoryValueSleepAnalysisAsleepDeep') AS deep_min,
               sum(minutes) FILTER (stage = 'HKCategoryValueSleepAnalysisAsleepREM')  AS rem_min,
               sum(minutes) FILTER (stage = 'HKCategoryValueSleepAnalysisAwake')      AS awake_min
        FROM _sleep
        GROUP BY local_date
        HAVING asleep_min > 0
        ORDER BY local_date
        """
    )

    # -- workouts ----------------------------------------------------------------
    con.execute(
        """
        CREATE OR REPLACE TABLE gold_workouts AS
        SELECT activity, local_date, round(duration_min, 1) AS duration_min,
               round(active_energy_kcal, 1) AS active_energy_kcal,
               round(distance_km, 2) AS distance_km, indoor
        FROM _workouts ORDER BY ts_utc
        """
    )
    con.execute(
        """
        CREATE OR REPLACE TABLE gold_workout_summary AS
        SELECT activity,
               count(*)                          AS n_workouts,
               round(sum(duration_min), 1)       AS total_min,
               round(sum(active_energy_kcal), 1) AS total_kcal,
               round(sum(distance_km), 2)        AS total_km
        FROM _workouts GROUP BY activity ORDER BY n_workouts DESC
        """
    )

    # -- one-row dashboard summary ------------------------------------------------
    con.execute(
        """
        CREATE OR REPLACE TABLE gold_summary AS
        SELECT
            (SELECT count(*) FROM gold_workouts)                             AS total_workouts,
            (SELECT round(sum(total_kcal)) FROM gold_workout_summary)        AS workout_kcal,
            (SELECT round(avg(avg_value)) FROM gold_daily_heart_rate)        AS avg_heart_rate,
            (SELECT value FROM gold_weight ORDER BY local_date DESC LIMIT 1) AS latest_weight,
            (SELECT round(avg(steps)) FROM gold_daily_activity)              AS avg_daily_steps,
            (SELECT min(local_date) FROM gold_daily_heart_rate)              AS first_date,
            (SELECT max(local_date) FROM gold_daily_heart_rate)              AS last_date
        """
    )

    tables = [r[0] for r in con.execute("SHOW TABLES").fetchall() if r[0].startswith("gold_")]
    counts = {t: con.execute(f"SELECT count(*) FROM {t}").fetchone()[0] for t in tables}
    con.close()
    log.info("gold: %s", counts)
    return counts
