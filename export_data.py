
"""
YottaFlex CLI Data Export Runner.
Generates CSV, JSON, SQL seed script, provenance manifest, and SHA-256 checksums.
"""

import argparse
import sys
import time
from pathlib import Path

from src.exporter import DataExporter


def main():
    parser = argparse.ArgumentParser(description="YottaFlex Multi-Format Data Exporter")
    parser.add_argument(
        "--db",
        type=str,
        default="yottaflex.db",
        help="Source SQLite database file. Default: yottaflex.db",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=20261022,
        help="Deterministic pseudorandom seed. Default: 20261022",
    )
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parent
    db_path = project_root / args.db
    export_dir = project_root / "exports"

    if not db_path.exists():
        print(f"[FATAL ERROR] Source database not found at {db_path}")
        sys.exit(1)

    print("=" * 70)
    print("YottaFlex Multi-Format Export & Data Provenance Engine")
    print(f"Source Database : {db_path.name}")
    print(f"Export Directory: {export_dir.resolve()}")
    print("=" * 70)

    t0 = time.time()
    exporter = DataExporter(db_path, export_dir)
    res = exporter.export_all(seed=args.seed)
    elapsed = time.time() - t0

    print(f"\n[+] Successfully exported {res['tables_exported']} tables in {elapsed:.2f}s:")
    for tbl, count in res["table_counts"].items():
        print(f"    - {tbl:<22}: {count:>6,d} records (CSV & JSON)")

    print("\n[+] Export Deliverables Generated:")
    print("    - exports/csv/*.csv                  (12 tabular CSV files)")
    print("    - exports/json/*.json                (12 JSON array files)")
    print("    - exports/sql/seed_data.sql          (Complete SQL recreation script)")
    print("    - exports/source_manifest.json       (Data provenance manifest)")
    print("    - exports/checksums.json             (Cryptographic SHA-256 ledger)")
    print("    - exports/checksums.sha256           (Standard GNU checksum ledger)")
    print("=" * 70)


if __name__ == "__main__":
    main()