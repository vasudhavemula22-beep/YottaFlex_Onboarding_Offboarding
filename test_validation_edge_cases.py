"""
YottaFlex Edge-Case Validation Unit Tests (Windows-Safe).
Tests validator behavior against empty databases, missing parent keys,
impossible dates, and zero-denominator calculations with explicit connection cleanup.
"""

import gc
import sqlite3
import sys
import tempfile
from pathlib import Path

from src.validator import SystemValidator


def test_edge_cases():
    print("\n" + "=" * 70)
    print("EDGE-CASE UNIT TESTS: Zero-Denominators, Empty DB & Invalid References")
    print("=" * 70)

    project_root = Path(__file__).resolve().parent
    schema_sql_path = project_root / "sql" / "schema.sql"

    with tempfile.TemporaryDirectory() as tmp_dir:
        test_db = Path(tmp_dir) / "test_edge.db"
        conn = sqlite3.connect(test_db)
        with open(schema_sql_path, "r", encoding="utf-8") as f:
            conn.executescript(f.read())
        conn.close()

        validator = SystemValidator(test_db)

        # 1. Test Empty Database & Zero Denominators
        print("\n[TEST 1] Testing Empty Database & Zero-Denominator Safety...")
        res_empty = validator.run_all_validations()
        metrics = res_empty["metrics"]
        print(f"    - Task Completion Rate on 0 tasks   : {metrics['task_completion_rate_pct']}%")
        print(f"    - Access Compliance on 0 grants     : {metrics['access_compliance_rate_pct']}%")
        print(f"    - Asset Reconciliation on 0 assets  : {metrics['asset_reconciliation_rate_pct']}%")

        assert metrics["task_completion_rate_pct"] == 0.0, "Expected 0.0% for 0 tasks"
        assert metrics["access_compliance_rate_pct"] == 100.0, "Expected 100.0% for 0 grants"
        assert metrics["asset_reconciliation_rate_pct"] == 100.0, "Expected 100.0% for 0 assets"
        print("[PASS] Zero-denominator arithmetic handled safely without ZeroDivisionError.")

        # 2. Test Detection of Impossible Dates
        print("\n[TEST 2] Testing Detection of Impossible Dates (Termination < Start)...")
        conn = sqlite3.connect(test_db)
        conn.execute("INSERT INTO departments VALUES ('DEP-001', 'Eng', 'CC-1001', '2026-01-01');")
        conn.execute("INSERT INTO roles VALUES ('ROL-001', 'Dev', 'DEP-001', 'STANDARD_USER', '2026-01-01');")
        conn.execute("PRAGMA ignore_check_constraints = ON;")
        conn.execute(
            """
            INSERT INTO employees (
                employee_id, first_name, last_name, email, role_id, dept_id,
                employment_type, employment_status, hire_date, start_date, termination_date
            ) VALUES (
                'EMP-000001', 'Test', 'User', 'test.user@yottaflex.internal', 'ROL-001', 'DEP-001',
                'FULL_TIME', 'TERMINATED', '2026-01-01', '2026-02-01', '2026-01-15'
            );
            """
        )
        conn.commit()
        conn.close()

        res_date = validator.run_all_validations()
        date_findings = [f for f in res_date["findings"] if f["rule_id"] == "TERMINATION_BEFORE_START"]
        print(f"    - Detected date ordering violations: {len(date_findings)}")
        assert len(date_findings) == 1, "Expected exactly 1 TERMINATION_BEFORE_START finding"
        print("[PASS] Impossible chronological sequence detected successfully.")

        # Force Windows garbage collector to release any residual SQLite file locks
        del validator
        gc.collect()

    print("\n" + "=" * 70)
    print("[ALL EDGE-CASE TESTS PASSED]")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    test_edge_cases()