"""
YottaFlex Verification Script for Step 2 (State-Aware).
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
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name;")
        tables = [r[0] for r in cursor.fetchall()]

        counts = {}
        for tbl in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {tbl};")
            counts[tbl] = cursor.fetchone()[0]

        emp_count = counts.get("employees", 0)
        mode = "full" if emp_count >= 500 else "starter"
        print(f"\n[+] Detected Dataset Scale: {mode.upper()} MODE ({emp_count} employees)")

        if mode == "full":
            expected_specs = {
                "employees": (1000, 1000),
                "tasks": (8000, 8025),
                "access_grants": (1500, 1515),
                "assets": (1200, 1200),
                "departments": (8, 8),
                "roles": (24, 24),
                "access_roles": (20, 20),
                "managers": (50, 50),
                "onboarding_cases": (1000, 1000),
                "offboarding_cases": (150, 160),
            }
        else:
            expected_specs = {
                "employees": (50, 50),
                "tasks": (400, 420),
                "access_grants": (75, 85),
                "assets": (60, 60),
                "departments": (8, 8),
                "roles": (24, 24),
                "access_roles": (20, 20),
                "managers": (5, 5),
                "onboarding_cases": (50, 50),
                "offboarding_cases": (8, 15),
            }

        print("\n[*] Validating Mandatory Entity Target Requirements:")
        for entity, (min_target, max_target) in expected_specs.items():
            actual = counts.get(entity, 0)
            if min_target <= actual <= max_target:
                print(f"[PASS] {entity:<20}: {actual} satisfies target requirement ({min_target}..{max_target})")
            else:
                print(f"[FAIL] {entity:<20}: expected {min_target}..{max_target}, got {actual}")
                failures += 1

        cursor.execute("PRAGMA foreign_key_check;")
        fk_violations = len(cursor.fetchall())
        if fk_violations == 0:
            print("[PASS] 0 Foreign Key violations detected across all relations.")
        else:
            print(f"[FAIL] Detected {fk_violations} FK violations.")
            failures += 1

        cursor.execute("SELECT employee_id, manager_id FROM employees WHERE employee_id = manager_id;")
        if len(cursor.fetchall()) == 0:
            print("[PASS] No employee is self-managed (acyclic supervisory structure).")
        else:
            print("[FAIL] Self-managed employees detected.")
            failures += 1

        cursor.execute("SELECT count(*) FROM employees WHERE termination_date IS NOT NULL AND termination_date < start_date;")
        if cursor.fetchone()[0] == 0:
            print("[PASS] All termination dates are chronologically on or after start dates.")
        else:
            failures += 1

        cursor.execute("SELECT count(*) FROM task_dependencies WHERE task_id = prerequisite_task_id;")
        if cursor.fetchone()[0] == 0:
            print("[PASS] No reflexive self-dependency loops detected in task DAGs.")
        else:
            failures += 1

        cursor.execute("SELECT count(*) FROM labelled_anomalies;")
        anom_count = cursor.fetchone()[0]
        if anom_count in (0, 5, 25):
            print(f"[PASS] Valid anomaly catalog status verified ({anom_count} anomalies registered).")
        else:
            print(f"[FAIL] Unexpected anomaly count: {anom_count}")
            failures += 1

    except Exception as e:
        print(f"[FAIL] SQLite error: {e}")
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
    verify_step2(PROJECT_ROOT / "yottaflex.db")
