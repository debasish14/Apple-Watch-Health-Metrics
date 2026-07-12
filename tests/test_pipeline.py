"""End-to-end assertions over the synthetic export (see conftest.py for
the traits deliberately baked into the fixture)."""
import duckdb
import pytest


@pytest.fixture(scope="session")
def gold(pipeline_env):
    con = duckdb.connect(str(pipeline_env["config"].GOLD_DB), read_only=True)
    yield con
    con.close()


def one(con, sql):
    return con.execute(sql).fetchone()


class TestBronze:
    def test_all_record_types_preserved(self, pipeline_env, gold):
        # bronze keeps types silver doesn't promote (audio exposure)
        path = str(pipeline_env["config"].BRONZE_RECORDS)
        n = one(gold, f"SELECT count(*) FROM read_parquet('{path}') "
                      "WHERE type = 'HKQuantityTypeIdentifierHeadphoneAudioExposure'")[0]
        assert n == 1

    def test_workout_statistics_flattened(self, gold):
        kcal, km = one(gold, "SELECT active_energy_kcal, distance_km FROM gold_workouts "
                             "WHERE activity = 'Walking'")
        assert kcal == 150.5
        assert km == 2.5


class TestSilver:
    def test_exact_duplicates_collapsed(self, pipeline_env, gold):
        path = str(pipeline_env["config"].SILVER_RECORDS)
        n = one(gold, f"SELECT count(*) FROM read_parquet('{path}') "
                      "WHERE type = 'HKQuantityTypeIdentifierHeartRate' "
                      "AND local_date = DATE '2025-12-01'")[0]
        assert n == 2  # 3 rows in bronze, one is an exact duplicate

    def test_non_numeric_value_dropped_and_counted(self, pipeline_env, gold):
        assert pipeline_env["report"]["counters"]["invalid_numeric_value"] == 1
        path = str(pipeline_env["config"].SILVER_RECORDS)
        n = one(gold, f"SELECT count(*) FROM read_parquet('{path}') WHERE value IS NULL")[0]
        assert n == 0

    def test_local_date_uses_wall_clock(self, pipeline_env, gold):
        # 2025-12-01 08:00 +0530 is 2025-11-30 in UTC; local_date must stay Dec 1
        path = str(pipeline_env["config"].SILVER_RECORDS)
        lo = one(gold, f"SELECT min(local_date) FROM read_parquet('{path}')")[0]
        assert str(lo) == "2025-12-01"


class TestGold:
    def test_daily_heart_rate_aggregation(self, gold):
        avg, mn, mx, n = one(gold, "SELECT avg_value, min_value, max_value, n_samples "
                                   "FROM gold_daily_heart_rate WHERE local_date = DATE '2025-12-01'")
        assert (avg, mn, mx, n) == (70.0, 60.0, 80.0, 2)  # (60+80)/2, dup removed

    def test_steps_not_double_counted(self, gold):
        steps = one(gold, "SELECT steps FROM gold_daily_activity "
                          "WHERE local_date = DATE '2025-12-01'")[0]
        assert steps == 1000  # max(Watch 1000, iPhone 900), not 1900

    def test_sleep_stages_summed_awake_excluded(self, gold):
        asleep, deep, awake = one(gold, "SELECT asleep_min, deep_min, awake_min "
                                        "FROM gold_daily_sleep WHERE local_date = DATE '2025-12-02'")
        assert asleep == 150  # 120 core + 30 deep
        assert deep == 30
        assert awake == 10

    def test_workout_summary(self, gold):
        n, kcal = one(gold, "SELECT n_workouts, total_kcal FROM gold_workout_summary "
                            "WHERE activity = 'Walking'")
        assert (n, kcal) == (1, 150.5)
        total = one(gold, "SELECT total_workouts, workout_kcal FROM gold_summary")
        assert total == (2, 250.0)  # 150.5 + 99.5

    def test_weight(self, gold):
        w = one(gold, "SELECT latest_weight FROM gold_summary")[0]
        assert w == 81.5

    def test_calendar_levels(self, gold):
        # 2025-12-01 has the only step count (1000): a single active day
        # lands in ntile bucket 1; no ActiveEnergyBurned records -> level 0.
        steps, lvl_steps, lvl_kcal = one(
            gold, "SELECT steps, level_steps, level_kcal FROM gold_daily_calendar "
                  "WHERE local_date = DATE '2025-12-01'")
        assert steps == 1000
        assert lvl_steps == 1
        assert lvl_kcal == 0
        # levels always within the GitHub 0-4 palette range
        bad = one(gold, "SELECT count(*) FROM gold_daily_calendar "
                        "WHERE level_steps NOT BETWEEN 0 AND 4 "
                        "   OR level_kcal NOT BETWEEN 0 AND 4")[0]
        assert bad == 0


class TestQuality:
    def test_checks_evaluated(self, pipeline_env):
        report = pipeline_env["report"]
        statuses = {c["check"]: c["status"] for c in report["checks"]}
        assert statuses["records survived silver"] == "pass"
        assert statuses["workouts survived silver"] == "pass"
        # 1 bogus value out of 13 bronze rows is 7.7% > the 1% threshold:
        # the tiny fixture SHOULD trip the invalid-value warning.
        assert "invalid numeric values below 1% of bronze" in report["warnings"]

    def test_report_persisted(self, pipeline_env):
        latest = pipeline_env["config"].QUALITY_DIR / "latest.json"
        assert latest.exists()


@pytest.fixture()
def client(pipeline_env):
    from api.app import app

    app.config["TESTING"] = True
    return app.test_client()


class TestAPI:

    def test_health(self, client):
        body = client.get("/api/health").get_json()
        assert body == {"status": "ok", "data_ready": True}

    def test_dashboard_bundle(self, client):
        body = client.get("/api/health-metrics").get_json()
        assert body["summary"]["total_workouts"] == 2
        assert body["heartRate"][0] == {"date": "2025-12-01", "value": 70.0}
        assert {w["name"] for w in body["workouts"]} == {"Walking", "Cycling"}
        assert body["calendar"][0]["date"] == "2025-12-01"
        assert body["calendar"][0]["level_steps"] == 1

    def test_metric_endpoint_and_whitelist(self, client):
        rows = client.get("/api/metrics/activity").get_json()
        assert rows[0]["steps"] == 1000
        resp = client.get("/api/metrics/evil")
        assert resp.status_code == 404
        assert "available" in resp.get_json()
