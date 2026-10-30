
"""
YottaFlex Step 10 Reproducibility and Determinism Verification Suite.
Generates two independent datasets (Run A and Run B) using seed 20261022,
normalizes timestamps, and asserts byte-level equivalence and record-count stability.
Windows-safe connection handling.
"""

import gc
import hashlib
import json
import sqlite3
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List

from src.generator import FULL_CONFIG, STARTER_CONFIG, YottaFlexDataGenerator
from src.injector import AnomalyInjector


def hash_record(record: Dict[str, Any], ignore_keys: tuple = ("created_at", "updated_at", "appointed_at", "timestamp")) -> str:
    """Normalizes records by stripping wall-clock timestamps before hashing."""
    normalized = {k: v for k, v in sorted(record.items()) if k not in ignore_keys}
    raw = json.dumps(normalized, sort_keys=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def test_reproducibility():
    print("\n" + "=" * 70)
    print("STEP 10 VERIFICATION: Reproducibility & Dual-Generation Audit")
    print("=" * 70)

    # 1. Generate Run A and Run B in memory using seed 20261022
    print("\n[*] Audit 1: Generating Dual Independent Datasets (Run A & Run B)...")
    gen_a = YottaFlexDataGenerator(FULL_CONFIG)
    data_a = gen_a.generate_all()

    gen_b = YottaFlexDataGenerator(FULL_CONFIG)
    data_b = gen_b.generate_all()

    failures = 0

    # 2. Assert Row Count Identicality across all 12 tables
    print("\n[*] Audit 2: Asserting Row Count Equality Across Runs:")
    for table_name in data_a.keys():
        count_a = len(data_a[table_name])
        count_b = len(data_b[table_name])
        if count_a == count_b:
            print(f"[PASS] {table_name:<22}: Run A = {count_a:>5} | Run B = {count_b:>5}")
        else:
            print(f"[FAIL] {table_name:<22}: Mismatch! Run A={count_a}, Run B={count_b}")
            failures += 1

    # 3. Assert Primary Key & Value Hash Equality
    print("\n[*] Audit 3: Asserting Deterministic Content Equivalence (Sample Audit):")
    for tbl in ["employees", "tasks", "access_grants", "assets"]:
        rows_a = data_a[tbl]
        rows_b = data_b[tbl]

        hashes_a = [hash_record(r) for r in rows_a]
        hashes_b = [hash_record(r) for r in rows_b]

        if hashes_a == hashes_b:
            print(f"[PASS] {tbl:<22}: 100% Deterministic record match across all {len(rows_a)} rows.")
        else:
            print(f"[FAIL] {tbl:<22}: Non-deterministic variation detected!")
            failures += 1

    # 4. Test Idempotency / No Duplicate Accumulation
    print("\n[*] Audit 4: Testing Repeatable Generation Idempotency...")
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_db = Path(tmp_dir) / "test_repeat.db"
        project_root = Path(__file__).resolve().parent
        schema_path = project_root / "sql" / "schema.sql"

        # Pass 1: Provision schema and seed starter
        conn = sqlite3.connect(tmp_db)
        with open(schema_path, "r", encoding="utf-8") as sf:
            conn.executescript(sf.read())
        conn.close()

        # Seed Run 1
        from generate_data import insert_records
        conn = sqlite3.connect(tmp_db)
        conn.execute("PRAGMA foreign_keys = ON;")
        starter_data_1 = YottaFlexDataGenerator(STARTER_CONFIG).generate_all()
        with conn:
            insert_records(conn, starter_data_1)

        c1 = conn.cursor().execute("SELECT count(*) FROM employees;").fetchone()[0]
        conn.close()

        # Re-seed Run 2 with reset
        from generate_data import reset_database
        conn = sqlite3.connect(tmp_db)
        reset_database(conn, schema_path)
        starter_data_2 = YottaFlexDataGenerator(STARTER_CONFIG).generate_all()
        with conn:
            insert_records(conn, starter_data_2)

        c2 = conn.cursor().execute("SELECT count(*) FROM employees;").fetchone()[0]
        conn.close()

        if c1 == 50 and c2 == 50:
            print("[PASS] Idempotent generation verified: 50 rows on Pass 1 and exactly 50 rows on Pass 2.")
        else:
            print(f"[FAIL] Record accumulation detected: Pass 1={c1}, Pass 2={c2}")
            failures += 1

        del conn
        gc.collect()

    print("\n" + "=" * 70)
    if failures == 0:
        print("[STEP 10 COMPLETE] System reproducibility, determinism, and idempotency PASSED.")
        print("=" * 70 + "\n")
        sys.exit(0)
    else:
        print(f"[STEP 10 FAILED] Detected {failures} assertion failures.")
        print("=" * 70 + "\n")
        sys.exit(1)


if __name__ == "__main__":
    test_reproducibility()