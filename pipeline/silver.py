"""Silver layer: typed, deduplicated, validated tables from bronze Parquet.

All transforms run as DuckDB SQL over the bronze files — nothing is loaded
into Python memory. Decisions made here:

* Timestamps: Apple exports local wall-clock time with a UTC offset
  ("2025-11-12 17:58:31 +0530"). Day-level analytics should bucket by the
  user's local day, so `local_date` is taken from the wall-clock portion,
  and the full instant is kept as `ts_utc` for anything finer-grained.
* Dedup: exact duplicates on (type, start, end, value, source) collapse to
  one row — re-imported/merged exports commonly contain them.
* Validation: quantity records must have a parseable numeric value and a
  parseable timestamp; violations are counted (data-quality report) and
  dropped, never silently coerced to defaults.

DDL statements (CREATE/COPY) can't take prepared parameters in DuckDB, so
paths and type lists — all trusted config constants — are inlined as SQL
literals via _sql_str / _sql_list.
"""
import logging

import duckdb

from . import config

log = logging.getLogger(__name__)

_TS = "'%Y-%m-%d %H:%M:%S %z'"  # Apple export timestamp format


def _sql_str(value: str) -> str:
    return "'" + str(value).replace("'", "''") + "'"


def _sql_list(values) -> str:
    return "(" + ", ".join(_sql_str(v) for v in values) + ")"


def transform() -> dict:
    """Build silver Parquet from bronze. Returns data-quality counters."""
    config.ensure_dirs()
    con = duckdb.connect()
    bronze_records = _sql_str(config.BRONZE_RECORDS)
    bronze_workouts = _sql_str(config.BRONZE_WORKOUTS)
    quantity_types = _sql_list(config.QUANTITY_TYPES)

    # --- DQ: rows silver will reject, by reason ----------------------------
    bad_value, bad_ts = con.execute(
        f"""
        SELECT
            count(*) FILTER (WHERE TRY_CAST(value AS DOUBLE) IS NULL),
            count(*) FILTER (WHERE TRY_STRPTIME(start_date, {_TS}) IS NULL)
        FROM read_parquet({bronze_records})
        WHERE type IN {quantity_types}
        """
    ).fetchone()

    # --- Quantity records ---------------------------------------------------
    con.execute(
        f"""
        COPY (
            SELECT DISTINCT
                type,
                source_name,
                unit,
                TRY_CAST(value AS DOUBLE)               AS value,
                TRY_STRPTIME(start_date, {_TS})         AS ts_utc,
                CAST(substr(start_date, 1, 10) AS DATE) AS local_date
            FROM read_parquet({bronze_records})
            WHERE type IN {quantity_types}
              AND TRY_CAST(value AS DOUBLE) IS NOT NULL
              AND TRY_STRPTIME(start_date, {_TS}) IS NOT NULL
        ) TO {_sql_str(config.SILVER_RECORDS)} (FORMAT PARQUET, COMPRESSION ZSTD)
        """
    )

    # --- Sleep (category records: value is a stage name) ---------------------
    con.execute(
        f"""
        COPY (
            SELECT DISTINCT
                value                                 AS stage,
                source_name,
                TRY_STRPTIME(start_date, {_TS})       AS start_utc,
                TRY_STRPTIME(end_date, {_TS})         AS end_utc,
                -- attribute a sleep interval to the day you wake up on
                CAST(substr(end_date, 1, 10) AS DATE) AS local_date,
                date_diff('minute',
                    TRY_STRPTIME(start_date, {_TS}),
                    TRY_STRPTIME(end_date, {_TS}))    AS minutes
            FROM read_parquet({bronze_records})
            WHERE type = {_sql_str(config.SLEEP_TYPE)}
              AND TRY_STRPTIME(start_date, {_TS}) IS NOT NULL
              AND TRY_STRPTIME(end_date, {_TS}) IS NOT NULL
        ) TO {_sql_str(config.SILVER_SLEEP)} (FORMAT PARQUET, COMPRESSION ZSTD)
        """
    )

    # --- Workouts -------------------------------------------------------------
    con.execute(
        f"""
        COPY (
            SELECT DISTINCT
                replace(activity_type, 'HKWorkoutActivityType', '') AS activity,
                source_name,
                TRY_CAST(duration_min AS DOUBLE)        AS duration_min,
                TRY_CAST(active_energy_kcal AS DOUBLE)  AS active_energy_kcal,
                TRY_CAST(distance_km AS DOUBLE)         AS distance_km,
                indoor = '1'                            AS indoor,
                TRY_STRPTIME(start_date, {_TS})         AS ts_utc,
                CAST(substr(start_date, 1, 10) AS DATE) AS local_date
            FROM read_parquet({bronze_workouts})
            WHERE activity_type IS NOT NULL
              AND TRY_STRPTIME(start_date, {_TS}) IS NOT NULL
        ) TO {_sql_str(config.SILVER_WORKOUTS)} (FORMAT PARQUET, COMPRESSION ZSTD)
        """
    )

    # --- Counters for the DQ report -------------------------------------------
    def _count(path) -> int:
        return con.execute(f"SELECT count(*) FROM read_parquet({_sql_str(path)})").fetchone()[0]

    date_lo, date_hi = con.execute(
        f"SELECT min(local_date), max(local_date) FROM read_parquet({_sql_str(config.SILVER_RECORDS)})"
    ).fetchone()

    counters = {
        "bronze_records": _count(config.BRONZE_RECORDS),
        "silver_records": _count(config.SILVER_RECORDS),
        "silver_sleep_intervals": _count(config.SILVER_SLEEP),
        "silver_workouts": _count(config.SILVER_WORKOUTS),
        "date_range": [str(date_lo), str(date_hi)],
        "invalid_numeric_value": bad_value,
        "invalid_timestamp": bad_ts,
    }
    con.close()
    log.info("silver: %s", counters)
    return counters
