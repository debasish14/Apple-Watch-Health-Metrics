"""Read-only DuckDB access to gold tables.

A short-lived read-only connection per request keeps things simple and lets
a pipeline run swap the database out underneath the API safely.
"""
import datetime
from contextlib import contextmanager

import duckdb

from pipeline import config

# Whitelist: metric name in the URL -> gold table. Never interpolate user
# input into SQL outside this mapping.
METRIC_TABLES = {
    "heart-rate": "gold_daily_heart_rate",
    "resting-hr": "gold_daily_resting_hr",
    "hrv": "gold_daily_hrv",
    "respiratory-rate": "gold_daily_respiratory_rate",
    "vo2max": "gold_vo2max",
    "weight": "gold_weight",
    "activity": "gold_daily_activity",
    "calendar": "gold_daily_calendar",
    "sleep": "gold_daily_sleep",
    "workouts": "gold_workouts",
    "workout-summary": "gold_workout_summary",
}


@contextmanager
def connection():
    con = duckdb.connect(str(config.GOLD_DB), read_only=True)
    try:
        yield con
    finally:
        con.close()


def _json_safe(value):
    """ISO-format dates so Flask doesn't emit HTTP-date strings."""
    if isinstance(value, (datetime.date, datetime.datetime)):
        return value.isoformat()
    return value


def _rows(con, sql: str) -> list[dict]:
    cur = con.execute(sql)
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, (_json_safe(v) for v in row))) for row in cur.fetchall()]


def gold_ready() -> bool:
    return config.GOLD_DB.exists()


def metric(name: str) -> list[dict] | None:
    """All rows of one gold metric table, or None for an unknown metric."""
    table = METRIC_TABLES.get(name)
    if table is None:
        return None
    with connection() as con:
        return _rows(con, f"SELECT * FROM {table}")


def summary() -> dict:
    with connection() as con:
        rows = _rows(con, "SELECT * FROM gold_summary")
    return rows[0] if rows else {}


def dashboard_payload() -> dict:
    """Bundle shaped for the React dashboard (single fetch)."""
    with connection() as con:
        return {
            "summary": _rows(con, "SELECT * FROM gold_summary")[0],
            "heartRate": _rows(
                con,
                "SELECT strftime(local_date, '%Y-%m-%d') AS date, avg_value AS value "
                "FROM gold_daily_heart_rate ORDER BY local_date",
            ),
            "weight": _rows(
                con,
                "SELECT strftime(local_date, '%Y-%m-%d') AS date, value "
                "FROM gold_weight ORDER BY local_date",
            ),
            "workouts": _rows(
                con,
                "SELECT activity AS name, n_workouts AS value, total_kcal "
                "FROM gold_workout_summary ORDER BY n_workouts DESC",
            ),
            "calendar": _rows(
                con,
                "SELECT strftime(local_date, '%Y-%m-%d') AS date, steps, "
                "active_kcal, distance_km, level_kcal, level_steps "
                "FROM gold_daily_calendar ORDER BY local_date",
            ),
        }
