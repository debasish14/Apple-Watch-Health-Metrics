# ⌚ Apple Watch Health Metrics

A data-engineering pipeline + dashboard for Apple Health exports. A 279MB
`export.xml` goes from raw XML to pre-aggregated serving tables in ~3.5s,
queried by a thin Flask API and rendered in a React dashboard.

## Architecture

Medallion pipeline on **DuckDB + Parquet** — no Spark, no external database.
Personal-scale data (hundreds of MB) fits comfortably on one machine; the
engineering value is in the layering, not the cluster.

```
export.xml ──► BRONZE ──────► SILVER ─────────► GOLD ──────────► API ─► React
   279MB      raw XML to     typed, deduped,   pre-aggregated   read-only
              Parquet        validated,        daily rollups    DuckDB
              (streaming,    DQ-counted        in health.duckdb queries
              ~10MB)         (~3MB)
```

- **Bronze** (`pipeline/bronze.py`) — streams XML with `iterparse` (constant
  memory), preserves records as exported, flattens nested `WorkoutStatistics`
  (modern exports keep workout energy there, not in attributes).
- **Silver** (`pipeline/silver.py`) — pure DuckDB SQL: type casting, exact-
  duplicate removal, timestamp/value validation with per-reason reject
  counters, wall-clock `local_date` for day bucketing (exports carry local
  time + UTC offset).
- **Gold** (`pipeline/gold.py`) — serving tables: daily heart rate / resting
  HR / HRV / respiratory rate, sleep stages per night, VO2max, weight,
  workouts, and daily activity with **source dedup** (steps & energy arrive
  from both iPhone and Watch; per day we keep the largest single source
  instead of double counting).
- **Quality** (`pipeline/quality.py`) — every run emits a JSON data-quality
  report (row counts per stage, reject reasons, threshold checks) to
  `data/quality/`, also served at `/api/quality`.

Ingestion is decoupled from serving: the API only reads gold tables and
never touches XML at request time.

## Quick start

```bash
make setup                                   # venv + pip + npm install
make ingest EXPORT=path/to/export.xml        # run the pipeline
make serve                                   # Flask API on :5001
make frontend                                # Vite dev server on :5173 (proxies /api)
make test                                    # pytest suite (synthetic-XML e2e)
```

Get an export: iPhone Health app → profile picture → *Export All Health Data*.

## API

| Endpoint               | Returns                                        |
| ---------------------- | ---------------------------------------------- |
| `GET /api/health`      | liveness + whether gold data exists            |
| `GET /api/health-metrics` | dashboard bundle (summary, HR trend, weight, workouts) |
| `GET /api/metrics/<name>` | one gold table; unknown names list what's available |
| `GET /api/summary`     | one-row totals (workouts, kcal, avg HR, ...)   |
| `GET /api/quality`     | latest pipeline data-quality report            |
| `POST /api/upload`     | multipart `export.xml`; runs the full pipeline |

Metric names: `heart-rate`, `resting-hr`, `hrv`, `respiratory-rate`,
`vo2max`, `weight`, `activity`, `sleep`, `workouts`, `workout-summary`.

Config via env: `PORT`, `HEALTH_DATA_DIR`, `CORS_ORIGINS`, `MAX_UPLOAD_MB`.

## Deployment (AWS free tier)

**Backend — Elastic Beanstalk (Python platform):**

```bash
pip install awsebcli
eb init -p python-3.13 health-metrics --region ap-south-1
eb create health-metrics-env --single --instance-types t3.micro
eb setenv CORS_ORIGINS=https://<your-frontend-domain> HEALTH_DATA_DIR=/var/app/data
```

The `Procfile` starts gunicorn; EB routes to port 8000. A `Dockerfile` is
also included if you prefer EB's Docker platform or any container host.

**Frontend — S3 + CloudFront:**

```bash
cd frontend && npm run build
aws s3 sync dist/ s3://<bucket> --delete
# point a CloudFront distribution at the bucket; add a behavior forwarding
# /api/* to the Elastic Beanstalk environment URL
```

Data is personal — the repo ignores `apple_health_export/`, `data/`, and all
`*.xml`/`*.csv` so nothing sensitive can be committed.

## Layout

```
pipeline/     bronze.py silver.py gold.py quality.py run.py config.py
api/          app.py (Flask) queries.py (read-only DuckDB, whitelisted tables)
frontend/     Vite + React + Recharts dashboard
tests/        pytest: dedup, aggregation, DQ, API (synthetic XML fixture)
data/         (generated, gitignored) bronze/ silver/ gold/ quality/
```
