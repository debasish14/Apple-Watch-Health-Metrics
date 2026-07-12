"""Shared fixture: a synthetic export.xml with hand-checkable values,
run through the full pipeline into a temp DATA_DIR."""
import textwrap

import pytest

# Deliberate traits baked into the fixture:
#  * heart-rate duplicate row      -> silver dedup must collapse it
#  * a "bogus" non-numeric value   -> silver must drop + count it
#  * steps from Watch AND iPhone   -> gold must not double count (keeps max: 1000)
#  * workout kcal only in nested   -> bronze must read WorkoutStatistics
#  * two sleep stages in one night -> gold must sum asleep, exclude awake
SYNTHETIC_XML = textwrap.dedent("""\
    <?xml version="1.0" encoding="UTF-8"?>
    <HealthData locale="en_IN">
     <ExportDate value="2025-12-25 10:00:00 +0530"/>
     <Record type="HKQuantityTypeIdentifierHeartRate" sourceName="Watch" unit="count/min" creationDate="2025-12-01 08:00:00 +0530" startDate="2025-12-01 08:00:00 +0530" endDate="2025-12-01 08:00:00 +0530" value="60"/>
     <Record type="HKQuantityTypeIdentifierHeartRate" sourceName="Watch" unit="count/min" creationDate="2025-12-01 08:00:00 +0530" startDate="2025-12-01 08:00:00 +0530" endDate="2025-12-01 08:00:00 +0530" value="60"/>
     <Record type="HKQuantityTypeIdentifierHeartRate" sourceName="Watch" unit="count/min" creationDate="2025-12-01 09:00:00 +0530" startDate="2025-12-01 09:00:00 +0530" endDate="2025-12-01 09:00:00 +0530" value="80"/>
     <Record type="HKQuantityTypeIdentifierHeartRate" sourceName="Watch" unit="count/min" creationDate="2025-12-02 08:00:00 +0530" startDate="2025-12-02 08:00:00 +0530" endDate="2025-12-02 08:00:00 +0530" value="100"/>
     <Record type="HKQuantityTypeIdentifierHeartRate" sourceName="Watch" unit="count/min" creationDate="2025-12-02 08:30:00 +0530" startDate="2025-12-02 08:30:00 +0530" endDate="2025-12-02 08:30:00 +0530" value="bogus"/>
     <Record type="HKQuantityTypeIdentifierStepCount" sourceName="Watch" unit="count" creationDate="2025-12-01 10:00:00 +0530" startDate="2025-12-01 10:00:00 +0530" endDate="2025-12-01 10:10:00 +0530" value="1000"/>
     <Record type="HKQuantityTypeIdentifierStepCount" sourceName="iPhone" unit="count" creationDate="2025-12-01 10:00:00 +0530" startDate="2025-12-01 10:00:00 +0530" endDate="2025-12-01 10:10:00 +0530" value="900"/>
     <Record type="HKQuantityTypeIdentifierBodyMass" sourceName="iPhone" unit="kg" creationDate="2025-12-01 07:00:00 +0530" startDate="2025-12-01 07:00:00 +0530" endDate="2025-12-01 07:00:00 +0530" value="81.5"/>
     <Record type="HKCategoryTypeIdentifierSleepAnalysis" sourceName="Watch" creationDate="2025-12-02 07:00:00 +0530" startDate="2025-12-01 23:00:00 +0530" endDate="2025-12-02 01:00:00 +0530" value="HKCategoryValueSleepAnalysisAsleepCore"/>
     <Record type="HKCategoryTypeIdentifierSleepAnalysis" sourceName="Watch" creationDate="2025-12-02 07:00:00 +0530" startDate="2025-12-02 01:00:00 +0530" endDate="2025-12-02 01:30:00 +0530" value="HKCategoryValueSleepAnalysisAsleepDeep"/>
     <Record type="HKCategoryTypeIdentifierSleepAnalysis" sourceName="Watch" creationDate="2025-12-02 07:00:00 +0530" startDate="2025-12-02 01:30:00 +0530" endDate="2025-12-02 01:40:00 +0530" value="HKCategoryValueSleepAnalysisAwake"/>
     <Record type="HKQuantityTypeIdentifierHeadphoneAudioExposure" sourceName="iPhone" unit="dBASPL" creationDate="2025-12-01 12:00:00 +0530" startDate="2025-12-01 12:00:00 +0530" endDate="2025-12-01 12:30:00 +0530" value="70"/>
     <Workout workoutActivityType="HKWorkoutActivityTypeWalking" duration="30.5" durationUnit="min" sourceName="Watch" startDate="2025-12-01 18:00:00 +0530" endDate="2025-12-01 18:30:30 +0530">
      <MetadataEntry key="HKIndoorWorkout" value="0"/>
      <WorkoutEvent type="HKWorkoutEventTypePause" date="2025-12-01 18:10:00 +0530"/>
      <WorkoutStatistics type="HKQuantityTypeIdentifierActiveEnergyBurned" startDate="2025-12-01 18:00:00 +0530" endDate="2025-12-01 18:30:30 +0530" sum="150.5" unit="kcal"/>
      <WorkoutStatistics type="HKQuantityTypeIdentifierDistanceWalkingRunning" startDate="2025-12-01 18:00:00 +0530" endDate="2025-12-01 18:30:30 +0530" sum="2.5" unit="km"/>
     </Workout>
     <Workout workoutActivityType="HKWorkoutActivityTypeCycling" duration="20.0" durationUnit="min" sourceName="Watch" startDate="2025-12-02 18:00:00 +0530" endDate="2025-12-02 18:20:00 +0530">
      <WorkoutStatistics type="HKQuantityTypeIdentifierActiveEnergyBurned" startDate="2025-12-02 18:00:00 +0530" endDate="2025-12-02 18:20:00 +0530" sum="99.5" unit="kcal"/>
     </Workout>
    </HealthData>
""")


@pytest.fixture(scope="session")
def pipeline_env(tmp_path_factory):
    """Run the whole pipeline once over the synthetic export."""
    data_dir = tmp_path_factory.mktemp("data")
    xml_path = tmp_path_factory.mktemp("input") / "export.xml"
    xml_path.write_text(SYNTHETIC_XML)

    import pipeline.config as config

    config.DATA_DIR = data_dir  # rebase all derived paths onto the temp dir
    for name in ("BRONZE_DIR", "SILVER_DIR", "GOLD_DIR", "QUALITY_DIR"):
        setattr(config, name, data_dir / name.split("_")[0].lower())
    config.BRONZE_RECORDS = config.BRONZE_DIR / "records.parquet"
    config.BRONZE_WORKOUTS = config.BRONZE_DIR / "workouts.parquet"
    config.SILVER_RECORDS = config.SILVER_DIR / "records.parquet"
    config.SILVER_SLEEP = config.SILVER_DIR / "sleep.parquet"
    config.SILVER_WORKOUTS = config.SILVER_DIR / "workouts.parquet"
    config.GOLD_DB = config.GOLD_DIR / "health.duckdb"

    from pipeline import run as pipeline_run

    report = pipeline_run.run(str(xml_path))
    return {"config": config, "report": report}
