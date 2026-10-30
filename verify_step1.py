"""
YottaFlex Verification Script for Step 1 (Updated).
Validates table creation, foreign-key enforcement capability, index counts, and column schemas.
"""

import sqlite3
import sys
from pathlib import Path

EXPECTED_TABLES = [
    "departments",
    "roles",
    "employees",
    "managers",
    "onboarding_cases",
    "tasks",
    "task_dependencies",
    "access_roles",
    "access_grants",
    "assets",
    "offboarding_cases",
    "audit_events",
    "labelled_anomalies",
]


def verify_step1(db_path: Path) -> None:
    print("\n" + "=" * 70)
    print("STEP 1 VERIFICATION: Database Catalog & Integrity Check")
    print("=" * 70)

    if not db_path.exists():
        print(f"[FAIL] Database file does not exist: {db_path}")
        sys.exit(1)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    failures = 0

    try:
        # Check 1: Enable and verify foreign key support on SQLite connection
        cursor.execute("PRAGMA foreign_keys = ON;")
        cursor.execute("PRAGMA foreign_keys;")
        fk_status = cursor.fetchone()[0]

        if fk_status == 1:
            print("[PASS] SQLite PRAGMA foreign_keys can be enabled and verified as ACTIVE.")
        else:
            print("[FAIL] SQLite engine failed to activate PRAGMA foreign_keys.")
            failures += 1

        # Check 2: Active Foreign Key enforcement test
        # Attempt to insert an employee referencing a non-existent role/department
        fk_violation_caught = False
        try:
            cursor.execute(
                """
                INSERT INTO employees (
                    employee_id, first_name, last_name, email, role_id, dept_id,
                    employment_type, employment_status, hire_date, start_date
                ) VALUES (
                    'EMP-999999', 'Ghost', 'Tester', 'ghost@invalid.local',
                    'ROL-999', 'DEP-999', 'FULL_TIME', 'PRE_HIRE',
                    '2026-01-01', '2026-01-15'
                );
                """
            )
        except sqlite3.IntegrityError:
            fk_violation_caught = True
        finally:
            conn.rollback()

        if fk_violation_caught:
            print("[PASS] Foreign Key Constraint Enforcement confirmed (invalid insertion was blocked).")
        else:
            print("[FAIL] Foreign Key Constraint did not block invalid foreign key insertion.")
            failures += 1

        # Check 3: Table catalog verification
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name;"
        )
        existing_tables = [row[0] for row in cursor.fetchall()]

        print(f"\n[*] Discovered {len(existing_tables)} tables in database:")
        for tbl in existing_tables:
            print(f"    - {tbl}")

        for expected in EXPECTED_TABLES:
            if expected in existing_tables:
                print(f"[PASS] Expected table confirmed: {expected}")
            else:
                print(f"[FAIL] Missing table: {expected}")
                failures += 1

        # Check 4: Column count audit per table
        print("\n[*] Auditing table structure and column counts:")
        for tbl in EXPECTED_TABLES:
            if tbl in existing_tables:
                cursor.execute(f"PRAGMA table_info({tbl});")
                columns = cursor.fetchall()
                print(f"    Table '{tbl}' has {len(columns)} columns.")
                if len(columns) == 0:
                    print(f"[FAIL] Table '{tbl}' has 0 columns.")
                    failures += 1

        # Check 5: Index count audit
        cursor.execute(
            "SELECT count(*) FROM sqlite_master WHERE type='index' AND name NOT LIKE 'sqlite_%';"
        )
        index_count = cursor.fetchone()[0]
        print(f"\n[*] Discovered {index_count} custom indexes across all entities.")
        if index_count < 10:
            print(f"[FAIL] Unexpectedly low index count: {index_count} (expected >= 10)")
            failures += 1
        else:
            print(f"[PASS] Index density requirement satisfied ({index_count} indexes).")

    except sqlite3.Error as err:
        print(f"[FAIL] SQLite verification query error: {err}")
        failures += 1
    finally:
        conn.close()

    print("\n" + "=" * 70)
    if failures == 0:
        print("[STEP 1 COMPLETE] All schema, table, and catalog checks PASSED.")
        print("=" * 70 + "\n")
        sys.exit(0)
    else:
        print(f"[STEP 1 FAILED] Detected {failures} assertion failures.")
        print("=" * 70 + "\n")
        sys.exit(1)


if __name__ == "__main__":
    PROJECT_ROOT = Path(__file__).resolve().parent
    DATABASE_PATH = PROJECT_ROOT / "yottaflex.db"
    verify_step1(DATABASE_PATH)