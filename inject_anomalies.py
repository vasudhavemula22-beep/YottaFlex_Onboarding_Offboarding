
"""
YottaFlex Anomaly Injection CLI Orchestrator.
Injects labelled negative test cases into SQLite and exports ground truth ledgers.
"""

import argparse
import sqlite3
import sys
import time
from pathlib import Path

from src.injector import AnomalyInjector, export_ground_truth_files


def main():
    parser = argparse.ArgumentParser(description="YottaFlex Negative Scenario & Anomaly Injection Engine")
    parser.add_argument(
        "--db",
        type=str,
        default="yottaflex.db",
        help="Target SQLite database file. Default: yottaflex.db",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=20261022,
        help="Deterministic pseudorandom seed. Default: 20261022",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=None,
        help="Anomalies per scenario (defaults: 1 for starter mode, 5 for full mode).",
    )
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parent
    db_path = project_root / args.db
    export_dir = project_root / "exports"

    if not db_path.exists():
        print(f"[FATAL ERROR] Database not found at {db_path}. Please generate baseline first.")
        sys.exit(1)

    # Detect dataset scale
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT count(*) FROM employees;")
    emp_count = cursor.fetchone()[0]
    conn.close()

    # Determine count per scenario: 1 for starter (5 total), 5 for full (25 total)
    if args.count is not None:
        target_count = args.count
    else:
        target_count = 5 if emp_count >= 500 else 1

    total_expected = target_count * 5

    print("=" * 70)
    print("YottaFlex Anomaly Injection Engine | Ground Truth Generator")
    print(f"Database: {db_path.name} | Scale: {'FULL' if emp_count >= 500 else 'STARTER'} ({emp_count} emps)")
    print(f"Injecting {target_count} anomaly instances across each of the 5 mandatory scenarios.")
    print(f"Total Target Anomalies: {total_expected}")
    print("=" * 70)

    t0 = time.time()
    injector = AnomalyInjector(db_path, seed=args.seed)
    injected_records = injector.inject_all(target_per_scenario=target_count)

    # Export ground truth files
    csv_file, json_file = export_ground_truth_files(injected_records, export_dir)
    elapsed = time.time() - t0

    print(f"[+] Successfully injected {len(injected_records)} anomalies into database in {elapsed:.2f}s.")
    print(f"[+] Ground truth CSV exported:  {csv_file.resolve()}")
    print(f"[+] Ground truth JSON exported: {json_file.resolve()}")
    print("=" * 70)


if __name__ == "__main__":
    main()