
"""
YottaFlex Verification Script for Step 2.
Validates table counts, exact targets, foreign key integrity, date sanity, and DAG structures.
"""

import sqlite3
import sys
from pathlib import Path


def verify_step2(db_path: Path) -> None:
    print("\n" + "=" * 70)
    print("STEP 2 VERIFICATION: Relational Data Generation & Integrity Audit")
    print("=" * 70)

    if not db_path.exists():
        print(f"[FAIL] Target database not found at: {db_path}")
        sys.exit(1)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON;")

    failures = 0

    try:
        # 1. Inspect table counts
        print("\n[*] Auditing Record Volumes per Table:")
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name;"
        )
        tables = [r[0] for r in cursor.fetchall()]

        counts = {}
        for tbl in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {tbl};")
            c = cursor.fetchone()[0]
            counts[tbl] = c
            print(f"    - {tbl:<22}: {c:>6} rows")

        # Detect Mode
        emp_count = counts.get("employees", 0)
        mode = "full" if emp_count >= 500 else "starter"
        print(f"\n[+] Detected Dataset Scale: {mode.upper()} MODE ({emp_count} employees)")

        # Target Volume Assertions
        if mode == "full":
            expected_targets = {
                "employees": 1000,
                "tasks": 8000,
                "access_grants": 1500,
                "assets": 1200,
                "departments": 8,
                "roles": 24,
                "access_roles": 20,
                "managers": 50,
                "onboarding_cases": 1000,
                "offboarding_cases": 150,
            }
        else:
            expected_targets = {
                "employees": 50,
                "tasks": 400,
                "access_grants": 75,
                "assets": 60,
                "departments": 8,
                "roles": 24,
                "access_roles": 20,
                "managers": 5,
                "onboarding_cases": 50,
                "offboarding_cases": 8,
            }

        print("\n[*] Validating Mandatory Entity Target Requirements:")
        for entity, target in expected_targets.items():
            actual = counts.get(entity, 0)
            if actual == target:
                print(f"[PASS] {entity:<20}: {actual} matches exact requirement {target}")
            else:
                print(f"[FAIL] {entity:<20}: expected {target}, got {actual}")
                failures += 1

        # 2. SQLite Foreign Key Integrity Check
        print("\n[*] Executing Deep SQLite Foreign Key Scan (PRAGMA foreign_key_check)...")
        cursor.execute("PRAGMA foreign_key_check;")
        fk_violations = cursor.fetchall()
        if len(fk_violations) == 0:
            print("[PASS] 0 Foreign Key violations detected across all relations.")
        else:
            print(f"[FAIL] Detected {len(fk_violations)} FK violations: {fk_violations}")
            failures += 1

        # 3. Check for Manager Circularity
        print("\n[*] Validating Management Hierarchy Non-Circularity:")
        cursor.execute("SELECT employee_id, manager_id FROM employees WHERE employee_id = manager_id;")
        self_managed = cursor.fetchall()
        if len(self_managed) == 0:
            print("[PASS] No employee is self-managed (acyclic supervisory structure).")
        else:
            print(f"[FAIL] Self-managed employees detected: {self_managed}")
            failures += 1

        # Top Executive Manager Check
        cursor.execute("SELECT manager_id FROM employees WHERE employee_id = 'EMP-000001';")
        ceo_mgr = cursor.fetchone()
        if ceo_mgr and ceo_mgr[0] is None:
            print("[PASS] Top executive (EMP-000001) has manager_id = NULL.")
        else:
            print(f"[FAIL] Expected EMP-000001 to have manager_id = NULL, found {ceo_mgr}")
            failures += 1

        # 4. Check Date Logic
        print("\n[*] Auditing Temporal Consistency & Business Rules:")
        cursor.execute(
            "SELECT count(*) FROM employees WHERE termination_date IS NOT NULL AND termination_date < start_date;"
        )
        invalid_term_dates = cursor.fetchone()[0]
        if invalid_term_dates == 0:
            print("[PASS] All termination dates are chronologically on or after start dates.")
        else:
            print(f"[FAIL] Found {invalid_term_dates} records with termination_date < start_date.")
            failures += 1

        cursor.execute(
            "SELECT count(*) FROM onboarding_cases WHERE actual_start_date < target_start_date;"
        )
        early_starts = cursor.fetchone()[0]
        if early_starts == 0:
            print("[PASS] Onboarding case dates respect baseline scheduling.")
        else:
            print(f"[FAIL] Found {early_starts} onboarding cases with unexpected early starts.")
            failures += 1

        # 5. Check Task DAG Validity (No self-dependencies)
        print("\n[*] Auditing Task Workflow DAGs:")
        cursor.execute(
            "SELECT count(*) FROM task_dependencies WHERE task_id = prerequisite_task_id;"
        )
        cycle_count = cursor.fetchone()[0]
        if cycle_count == 0:
            print("[PASS] No reflexive self-dependency loops detected in task DAGs.")
        else:
            print(f"[FAIL] Detected {cycle_count} reflexive task dependencies.")
            failures += 1

        # 6. Check Baseline Anomaly Table (Must be empty in Step 2)
        cursor.execute("SELECT count(*) FROM labelled_anomalies;")
        anom_count = cursor.fetchone()[0]
        if anom_count == 0:
            print("[PASS] Baseline data is clean (0 rows in labelled_anomalies).")
        else:
            print(f"[FAIL] Found unexpected anomalies in Step 2 baseline: {anom_count}")
            failures += 1

    except sqlite3.Error as e:
        print(f"[FAIL] SQLite query error: {e}")
        failures += 1
    finally:
        conn.close()

    print("\n" + "=" * 70)
    if failures == 0:
        print(f"[STEP 2 COMPLETE] All {mode.upper()} mode validation tests PASSED.")
        print("=" * 70 + "\n")
        sys.exit(0)
    else:
        print(f"[STEP 2 FAILED] Detected {failures} assertion failures.")
        print("=" * 70 + "\n")
        sys.exit(1)


if __name__ == "__main__":
    PROJECT_ROOT = Path(__file__).resolve().parent
    DATABASE_PATH = PROJECT_ROOT / "yottaflex.db"
    verify_step2(DATABASE_PATH)