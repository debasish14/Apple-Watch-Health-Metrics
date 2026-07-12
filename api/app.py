"""Flask API serving pre-aggregated gold tables.

The API never parses XML at request time except via /api/upload, which
re-runs the pipeline and swaps the gold database atomically enough for a
single-user app. Production entrypoint:

    gunicorn -w 2 -b 0.0.0.0:$PORT api.app:app
"""
import json
import logging
import os
import tempfile
from pathlib import Path

from flask import Flask, jsonify, request
from flask_cors import CORS

from pipeline import config, run as pipeline_run
from . import queries

MAX_UPLOAD_MB = int(os.environ.get("MAX_UPLOAD_MB", "500"))

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_MB * 1024 * 1024

# Lock CORS to the deployed frontend; localhost vite proxies during dev so
# this only matters when the frontend is served from another origin.
cors_origins = os.environ.get("CORS_ORIGINS", "")
if cors_origins:
    CORS(app, origins=cors_origins.split(","))

log = logging.getLogger(__name__)


@app.get("/")
def index():
    """People open the printed server URL; point them somewhere useful."""
    return jsonify({
        "service": "apple-watch-health-metrics API",
        "dashboard": "run `make frontend` and open http://localhost:5173",
        "endpoints": ["/api/health", "/api/health-metrics", "/api/summary",
                      "/api/quality", "/api/metrics/<name>", "POST /api/upload"],
        "metrics": sorted(queries.METRIC_TABLES),
    })


@app.get("/api/health")
def health():
    return jsonify({"status": "ok", "data_ready": queries.gold_ready()})


@app.get("/api/health-metrics")
def health_metrics():
    """Single-fetch bundle for the dashboard."""
    if not queries.gold_ready():
        return jsonify({"error": "no data ingested yet"}), 404
    return jsonify(queries.dashboard_payload())


@app.get("/api/metrics/<name>")
def metric(name: str):
    if not queries.gold_ready():
        return jsonify({"error": "no data ingested yet"}), 404
    rows = queries.metric(name)
    if rows is None:
        return jsonify({"error": f"unknown metric '{name}'",
                        "available": sorted(queries.METRIC_TABLES)}), 404
    return jsonify(rows)


@app.get("/api/summary")
def summary():
    if not queries.gold_ready():
        return jsonify({"error": "no data ingested yet"}), 404
    return jsonify(queries.summary())


@app.get("/api/quality")
def quality():
    """Latest pipeline data-quality report."""
    latest = config.QUALITY_DIR / "latest.json"
    if not latest.exists():
        return jsonify({"error": "no pipeline run yet"}), 404
    return jsonify(json.loads(latest.read_text()))


@app.post("/api/upload")
def upload():
    """Accept an export.xml and run the full pipeline on it."""
    file = request.files.get("file")
    if file is None or not file.filename:
        return jsonify({"error": "no file provided"}), 400

    # Uploads go to a temp file, not persistent storage: only the derived
    # bronze/silver/gold artifacts are kept.
    with tempfile.NamedTemporaryFile(suffix=".xml", delete=False) as tmp:
        file.save(tmp.name)
        tmp_path = Path(tmp.name)
    try:
        report = pipeline_run.run(str(tmp_path))
    except Exception as exc:  # surface pipeline failures to the client
        log.exception("pipeline failed")
        return jsonify({"error": f"pipeline failed: {exc}"}), 500
    finally:
        tmp_path.unlink(missing_ok=True)

    return jsonify({
        "message": "pipeline completed",
        "counters": report["counters"],
        "warnings": report["warnings"],
    })


if __name__ == "__main__":
    app.run(port=int(os.environ.get("PORT", "5001")),
            debug=os.environ.get("FLASK_DEBUG") == "1")
