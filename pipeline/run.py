"""Pipeline orchestrator: bronze -> silver -> gold -> quality report.

    python -m pipeline.run --input apple_health_export/export.xml
"""
import argparse
import logging
import time

from . import bronze, gold, quality, silver

log = logging.getLogger("pipeline")


def run(xml_path: str) -> dict:
    counters: dict = {}
    for name, step in [
        ("bronze", lambda: bronze.ingest(xml_path)),
        ("silver", silver.transform),
        ("gold", gold.build),
    ]:
        t0 = time.perf_counter()
        counters.update(step())
        log.info("%s finished in %.1fs", name, time.perf_counter() - t0)

    report = quality.build_report(counters)
    quality.write_report(report)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Apple Health data pipeline")
    parser.add_argument("--input", required=True, help="path to export.xml")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )

    report = run(args.input)

    print("\n=== data quality ===")
    for check in report["checks"]:
        print(f"  [{check['status']:>7}] {check['check']}: {check['value']}")
    print("\n=== counters ===")
    for key, value in report["counters"].items():
        print(f"  {key}: {value}")


if __name__ == "__main__":
    main()
