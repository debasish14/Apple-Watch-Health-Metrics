"""Data-quality report: collects stage counters, runs sanity checks,
and persists a JSON report per pipeline run."""
import json
import logging
from datetime import datetime, timezone

from . import config

log = logging.getLogger(__name__)

# Each check gets (value, all_counters); a failure flags the report, never drops data.
CHECKS = [
    ("silver_records", "records survived silver", lambda v, ctx: v > 0),
    ("silver_workouts", "workouts survived silver", lambda v, ctx: v > 0),
    ("invalid_numeric_value", "invalid numeric values below 1% of bronze",
     lambda v, ctx: v < max(1, ctx.get("bronze_records", 0) * 0.01)),
    ("invalid_timestamp", "invalid timestamps below 1% of bronze",
     lambda v, ctx: v < max(1, ctx.get("bronze_records", 0) * 0.01)),
]


def build_report(stage_counters: dict) -> dict:
    """Evaluate checks against merged counters from all stages."""
    checks = []
    for key, label, fn in CHECKS:
        value = stage_counters.get(key)
        if value is None:
            status = "skipped"
        else:
            status = "pass" if fn(value, stage_counters) else "warn"
        checks.append({"check": label, "value": value, "status": status})

    report = {
        "run_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "counters": stage_counters,
        "checks": checks,
        "warnings": [c["check"] for c in checks if c["status"] == "warn"],
    }
    return report


def write_report(report: dict) -> str:
    config.ensure_dirs()
    stamp = report["run_at"].replace(":", "-")
    path = config.QUALITY_DIR / f"dq_{stamp}.json"
    path.write_text(json.dumps(report, indent=2, default=str))
    # stable pointer to the latest report for the API / quick inspection
    (config.QUALITY_DIR / "latest.json").write_text(
        json.dumps(report, indent=2, default=str)
    )
    log.info("quality: report written to %s", path)
    return str(path)
