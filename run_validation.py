
"""
YottaFlex Validation CLI Orchestrator.
Executes the 10-dimension validation engine, prints a human-readable summary,
and writes exports/validation_summary.json.
"""

import argparse
import sys
from pathlib import Path

from src.validator import SystemValidator, export_validation_report


def main():
    parser = argparse.ArgumentParser(description="YottaFlex 10-Dimension System Validation Runner")
    parser.add_argument(
        "--db",
        type=str,
        default="yottaflex.db",
        help="Target SQLite database file. Default: yottaflex.db",
    )
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parent
    db_path = project_root / args.db
    export_json = project_root / "exports" / "validation_summary.json"

    if not db_path.exists():
        print(f"[FATAL ERROR] Target database not found at {db_path}")
        sys.exit(1)

    print("=" * 70)
    print("YottaFlex 10-Dimension Data Validation & Integrity Engine")
    print(f"Target Database : {db_path.name}")
    print("=" * 70)

    validator = SystemValidator(db_path)
    summary = validator.run_all_validations()

    # Export machine-readable JSON
    export_validation_report(summary, export_json)

    # Print Human-Readable Summary
    print(f"\n[*] Audit Timestamp : {summary['timestamp']}")
    print(f"[*] Total Findings  : {summary['total_findings']}")
    print(f"    - Baseline Schema / Data Defects : {summary['baseline_defects_count']}")
    print(f"    - Labelled Injected Anomalies    : {summary['injected_anomalies_detected']}")

    print("\n[*] Enterprise Calculated Rates (Safe Zero-Denominator Handling):")
    for k, v in summary["metrics"].items():
        print(f"    - {k:<30}: {v}")

    print("\n[*] Injected Anomaly Breakdown (Matches Ground Truth):")
    injected = [f for f in summary["findings"] if f["is_injected_anomaly"]]
    for f in injected[:10]:
        print(f"    - [{f['severity']:<8}] {f['rule_id']:<34} | Record: {f['record_id']}")
    if len(injected) > 10:
        print(f"    ... and {len(injected) - 10} more injected anomalies.")

    print("\n" + "=" * 70)
    if summary["baseline_defects_count"] == 0:
        print(f"[PASS] 0 unintentional baseline defects. All {len(injected)} anomalies accounted for.")
        print(f"[+] Machine-readable audit exported: {export_json.resolve()}")
        print("=" * 70 + "\n")
        sys.exit(0)
    else:
        print(f"[FAIL] Detected {summary['baseline_defects_count']} unintentional baseline defects!")
        print("=" * 70 + "\n")
        sys.exit(1)


if __name__ == "__main__":
    main()