"""
YottaFlex Master End-to-End System Orchestrator (Updated Pipeline Sequence).
Ensures baseline tests verify the pristine baseline BEFORE anomalies are injected.
"""

import argparse
import sqlite3
import subprocess
import sys
import time
from pathlib import Path


def run_command(command: list[str], description: str) -> None:
    print(f"\n[*] Executing: {description}...")
    t0 = time.time()
    result = subprocess.run(command, capture_output=True, text=True)
    elapsed = time.time() - t0

    if result.returncode != 0:
        print(f"[FAIL] {description} failed with return code {result.returncode}!")
        print(result.stdout)
        print(result.stderr)
        sys.exit(result.returncode)
    else:
        print(f"[PASS] {description} succeeded in {elapsed:.2f}s.")
        lines = [line for line in result.stdout.splitlines() if line.startswith(("[SUCCESS]", "[STEP", "[+]"))]
        for l in lines:
            print(f"       {l}")


def print_database_health(db_path: Path) -> None:
    print("\n" + "=" * 70)
    print(f"DATABASE HEALTH & VOLUME AUDIT: {db_path.name}")
    print("=" * 70)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON;")

    cursor.execute("SELECT count(*) FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
    tbl_count = cursor.fetchone()[0]

    cursor.execute("PRAGMA foreign_key_check;")
    fk_violations = len(cursor.fetchall())

    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name;"
    )
    tables = [row[0] for row in cursor.fetchall()]

    print(f"[+] Total Relational Tables : {tbl_count}")
    print(f"[+] Foreign Key Violations  : {fk_violations}")
    print("\nTable Breakdown:")
    total_records = 0
    for t in tables:
        cursor.execute(f"SELECT count(*) FROM {t};")
        cnt = cursor.fetchone()[0]
        total_records += cnt
        print(f"    - {t:<24}: {cnt:>7,d} rows")

    print("-" * 70)
    print(f"Total Relational Records Ingested: {total_records:,d}")
    print("=" * 70)
    conn.close()


def main():
    parser = argparse.ArgumentParser(description="YottaFlex Unified System Orchestrator")
    parser.add_argument(
        "--mode",
        choices=["starter", "full"],
        default="starter",
        help="Dataset generation scale (starter: 50 emps, full: 1000 emps). Default: starter",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=20261022,
        help="Deterministic pseudorandom seed. Default: 20261022",
    )
    parser.add_argument(
        "--skip-tests",
        action="store_true",
        help="Skip executing verification test suites.",
    )
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parent
    db_path = project_root / "yottaflex.db"
    python_exe = sys.executable

    print("\n" + "#" * 70)
    print(f"  YottaFlex Master Orchestrator | Target Scale: {args.mode.upper()}")
    print(f"  Python Runtime : {sys.version.split()[0]}")
    print(f"  Working Path   : {project_root}")
    print("#" * 70)

    # 1. Database DDL Initialization
    run_command([python_exe, "init_db.py"], "Step 1: Database DDL Provisioning")

    # 2. Baseline Generation
    run_command(
        [python_exe, "generate_data.py", "--mode", args.mode, "--seed", str(args.seed)],
        f"Step 2: Baseline Generation ({args.mode.upper()} mode)",
    )

    # 3. Verify Pristine Baseline (Schema & Volume & Business Rules)
    if not args.skip_tests:
        print("\n" + "=" * 70)
        print("PHASE A: VERIFYING PRISTINE BASELINE INTEGRITY (Steps 1 to 3)")
        print("=" * 70)
        run_command([python_exe, "verify_step1.py"], "Verification 1: Schema & Catalog Integrity")
        run_command([python_exe, "verify_step2.py"], "Verification 2: Baseline Volume & DAG Non-Circularity")
        run_command([python_exe, "verify_step3.py"], "Verification 3: Workflow Business Rules & Segregation of Duties")

    # 4. Anomaly Injection
    run_command([python_exe, "inject_anomalies.py"], "Step 4: Anomaly Injection & Ground Truth Generation")

    # 5. Verify Injected Anomalies & UI Services
    if not args.skip_tests:
        print("\n" + "=" * 70)
        print("PHASE B: VERIFYING ANOMALY DETECTION & BACKEND (Steps 4 & 5)")
        print("=" * 70)
        run_command([python_exe, "verify_step4.py"], "Verification 4: Anomaly Detection & Ground Truth Reconciler")
        run_command([python_exe, "verify_step5.py"], "Verification 5: Streamlit Backend & Analytical Query Layer")

    # 6. Database Health Summary
    print_database_health(db_path)

    print("\n[COMPLETE] YottaFlex environment fully provisioned and validated.")
    print("To launch the interactive dashboard, run:")
    print("    streamlit run app.py\n")


if __name__ == "__main__":
    main()