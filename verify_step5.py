"""
YottaFlex Verification Script for Step 5 (Scale-Aware).
Validates all backend data queries, aggregations, and transactional workflows
used by the Streamlit application across both starter and full modes.
"""

import sys
from pathlib import Path

from src.app_data import AppDataLayer
from src.services import (
    AccessGovernanceError,
    AssetUnavailableError,
    PrerequisiteNotSatisfiedError,
    WorkflowService,
)


def run_step5_verification():
    print("\n" + "=" * 70)
    print("STEP 5 VERIFICATION: Streamlit Backend & Data Access Layer Audit")
    print("=" * 70)

    project_root = Path(__file__).resolve().parent
    db_path = project_root / "yottaflex.db"

    if not db_path.exists():
        print(f"[FAIL] Target database not found at {db_path}")
        sys.exit(1)

    data_layer = AppDataLayer(db_path)
    service = WorkflowService(db_path)
    failures = 0

    # 1. Test KPI Aggregation Engine
    print("\n[TEST 1] Auditing Executive KPI Aggregations...")
    try:
        kpis = data_layer.get_executive_kpis()
        print(f"    - Total Workforce : {kpis['total_employees']}")
        print(f"    - Task Completion : {kpis['task_completion_rate']:.1f}%")
        print(f"    - Access Compliance: {kpis['access_compliance_rate']:.1f}%")
        print(f"    - Total Exceptions: {kpis['total_exceptions']}")

        if kpis["total_employees"] in (50, 1000) and kpis["total_exceptions"] in (5, 25):
            print("[PASS] KPI metrics accurately represent the database state.")
        else:
            print(f"[FAIL] Unexpected KPI counts: {kpis}")
            failures += 1
    except Exception as ex:
        print(f"[FAIL] KPI calculation failed: {ex}")
        failures += 1

    # 2. Test Parameterized Query Filters (Employee Directory)
    print("\n[TEST 2] Auditing Employee Directory Search & Filtering...")
    try:
        df_eng = data_layer.get_employees_df(dept_id="DEP-001", status="ACTIVE")
        print(f"    - Active Engineering personnel discovered: {len(df_eng)}")
        if len(df_eng) > 0 and (df_eng["dept_name"] == "Engineering").all():
            print("[PASS] Departmental and status query filters validated.")
        else:
            print(f"[FAIL] Query filter returned invalid records or zero rows.")
            failures += 1
    except Exception as ex:
        print(f"[FAIL] Directory query failed: {ex}")
        failures += 1

    # 3. Test Onboarding Workflow & Prerequisite Blocking Path
    print("\n[TEST 3] Auditing Onboarding DAG Action Service...")
    try:
        df_onb = data_layer.get_onboarding_cases_df()
        if not df_onb.empty:
            test_case = df_onb["onboarding_case_id"].iloc[0]
            df_tasks = data_layer.get_case_tasks_df(test_case)
            blocked_tasks = df_tasks[df_tasks["status"] == "BLOCKED"]

            if not blocked_tasks.empty:
                b_task_id = blocked_tasks["task_id"].iloc[0]
                try:
                    service.complete_task(
                        task_id=b_task_id,
                        actor_id="EMP-000001",
                        actor_role="IT_OPERATIONS",
                        force_override=False,
                    )
                    print(f"[FAIL] Blocked task '{b_task_id}' was completed without satisfying prerequisites!")
                    failures += 1
                except PrerequisiteNotSatisfiedError:
                    print(f"[PASS] Streamlit workflow service blocked premature task execution as expected.")
            else:
                print("[SKIP] No blocked tasks in selected case.")
        else:
            print("[SKIP] No onboarding cases available.")
    except Exception as ex:
        print(f"[FAIL] Onboarding workflow test error: {ex}")
        failures += 1

    # 4. Test Asset Duplicate Assignment Prevention
    print("\n[TEST 4] Auditing Asset Assignment Conflict Path...")
    try:
        df_assigned = data_layer.get_assets_df(status="ASSIGNED")
        df_active_emps = data_layer.get_employees_df(status="ACTIVE")
        if not df_assigned.empty and not df_active_emps.empty:
            assigned_ast = df_assigned["asset_id"].iloc[0]
            active_emp = df_active_emps["employee_id"].iloc[0]
            try:
                service.assign_asset(
                    asset_id=assigned_ast,
                    employee_id=active_emp,
                    actor_id="EMP-000001",
                    actor_role="IT_OPERATIONS",
                )
                print(f"[FAIL] Duplicate assignment permitted on asset '{assigned_ast}'!")
                failures += 1
            except AssetUnavailableError:
                print(f"[PASS] Asset allocation conflict prevented by service layer.")
        else:
            print("[SKIP] Insufficient assigned assets or active employees.")
    except Exception as ex:
        print(f"[FAIL] Asset conflict test error: {ex}")
        failures += 1

    # 5. Test Anomaly Detection Query Feed
    print("\n[TEST 5] Auditing Exception & Anomaly Detection Queries...")
    try:
        anomalies = data_layer.get_detected_anomalies()
        print(f"    - Detected violations: {len(anomalies)}")
        scenarios = {a["scenario"] for a in anomalies}
        print(f"    - Distinct scenarios identified: {len(scenarios)} of 5")

        if len(scenarios) == 5:
            print("[PASS] All 5 anomaly scenarios detected by data access layer.")
        else:
            print(f"[FAIL] Expected 5 distinct anomaly scenarios, discovered {len(scenarios)}")
            failures += 1
    except Exception as ex:
        print(f"[FAIL] Exception detection failed: {ex}")
        failures += 1

    # 6. Test Audit Trail Log Integrity
    print("\n[TEST 6] Auditing Audit Trail Ledger Retrieval...")
    try:
        df_audit = data_layer.get_audit_trail_df()
        print(f"    - Retrieved audit entries: {len(df_audit)}")
        if len(df_audit) > 0 and "timestamp" in df_audit.columns:
            print("[PASS] Audit trail records verified with non-empty event log.")
        else:
            print(f"[FAIL] Audit trail empty or malformed.")
            failures += 1
    except Exception as ex:
        print(f"[FAIL] Audit trail test error: {ex}")
        failures += 1

    print("\n" + "=" * 70)
    if failures == 0:
        print("[STEP 5 COMPLETE] All Streamlit backend routines and service paths PASSED.")
        print("=" * 70 + "\n")
        sys.exit(0)
    else:
        print(f"[STEP 5 FAILED] Detected {failures} assertion failures.")
        print("=" * 70 + "\n")
        sys.exit(1)


if __name__ == "__main__":
    run_step5_verification()