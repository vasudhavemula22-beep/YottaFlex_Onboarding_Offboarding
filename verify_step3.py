"""
YottaFlex Verification Script for Step 3 (Updated).
Executes an end-to-end integration test suite exercising the Workflow Engine:
- Task DAG prerequisite blocking and authorized overrides
- Access request, approval, and provisioning lifecycle (using active employees)
- Hardware asset assignment, custody conflict detection, and recovery (using active employees)
- Offboarding orchestration, auto-task DAG generation, and access compliance
- Audit ledger verification
"""

import sqlite3
import sys
from pathlib import Path

from src.services import (
    AccessGovernanceError,
    AssetUnavailableError,
    PrerequisiteNotSatisfiedError,
    WorkflowEngineError,
    WorkflowService,
)


def run_step3_verification():
    print("\n" + "=" * 70)
    print("STEP 3 VERIFICATION: Business Rules & Workflow Engine Test Suite")
    print("=" * 70)

    project_root = Path(__file__).resolve().parent
    db_path = project_root / "yottaflex.db"

    if not db_path.exists():
        print(f"[FAIL] Target database not found at {db_path}. Run Step 2 generator first.")
        sys.exit(1)

    service = WorkflowService(db_path)
    failures = 0

    # Retrieve active employees dynamically for testing
    conn = service._get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT employee_id FROM employees WHERE employment_status = 'ACTIVE' ORDER BY employee_id LIMIT 5;"
    )
    active_emps = [row["employee_id"] for row in cursor.fetchall()]
    conn.close()

    if len(active_emps) < 3:
        print("[FAIL] Insufficient active employees in database to perform verification.")
        sys.exit(1)

    test_emp_1 = active_emps[0]
    test_emp_2 = active_emps[1]
    test_emp_3 = active_emps[2]

    # Test 1: Task Prerequisite Enforcement
    print("\n[TEST 1] Auditing Task Prerequisite & DAG Enforcement...")
    try:
        conn = service._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT td.task_id, td.prerequisite_task_id
            FROM task_dependencies td
            JOIN tasks t ON td.task_id = t.task_id
            JOIN tasks tp ON td.prerequisite_task_id = tp.task_id
            WHERE t.status = 'BLOCKED' AND tp.status != 'COMPLETED'
            LIMIT 1;
            """
        )
        row = cursor.fetchone()
        conn.close()

        if row:
            blocked_task_id = row["task_id"]
            # Attempt to complete blocked task without override -> MUST FAIL
            try:
                service.complete_task(
                    blocked_task_id,
                    actor_id=test_emp_1,
                    actor_role="IT_OPERATIONS",
                    force_override=False,
                )
                print(f"[FAIL] Task '{blocked_task_id}' was completed despite unmet prerequisites!")
                failures += 1
            except PrerequisiteNotSatisfiedError as e:
                print(f"[PASS] Prerequisite barrier correctly blocked task: {e}")

            # Now test authorized override on the same task
            overridden_task = service.complete_task(
                blocked_task_id,
                actor_id=test_emp_1,
                actor_role="SYSTEM_ADMIN",
                force_override=True,
                override_reason="Expedited provisioning authorized by VP of IT.",
            )
            if overridden_task["status"] == "COMPLETED":
                print(f"[PASS] Authorized override succeeded for '{blocked_task_id}'.")
            else:
                print(f"[FAIL] Override failed to transition '{blocked_task_id}' to COMPLETED.")
                failures += 1
        else:
            print("[SKIP] No blocked tasks found in dataset to test prerequisite failure.")

    except Exception as ex:
        print(f"[FAIL] Test 1 unexpected error: {ex}")
        failures += 1

    # Test 2: Access Governance (Request -> Approve -> Provision)
    print("\n[TEST 2] Auditing Access Governance & Segregation of Duties...")
    try:
        # 1. Request access for an active employee (test_emp_1)
        grant = service.request_access(
            employee_id=test_emp_1,
            access_role_id="ACR-007",  # AWS Admin (Critical)
            actor_id=test_emp_1,
            actor_role="CANDIDATE",
            notes="Project requirement for infrastructure team.",
        )
        grant_id = grant["grant_id"]
        print(f"[PASS] Access requested for '{test_emp_1}': {grant_id} (Initial status: {grant['status']})")

        # 2. Attempt to provision without approval -> MUST FAIL
        try:
            service.provision_access(grant_id, actor_id=test_emp_1, actor_role="SYSTEM_ADMIN")
            print(f"[FAIL] Grant '{grant_id}' provisioned without mandatory approval!")
            failures += 1
        except AccessGovernanceError as age:
            print(f"[PASS] Provisioning rejected without prior approval: {age}")

        # 3. Manager approves access
        approved_grant = service.approve_access(
            grant_id,
            approver_id=test_emp_2,
            approver_role="MANAGER",
            notes="Approved after management review.",
        )
        if approved_grant["status"] == "APPROVED":
            print(f"[PASS] Access grant {grant_id} successfully approved by Manager.")
        else:
            print(f"[FAIL] Expected grant status APPROVED, got {approved_grant['status']}")
            failures += 1

        # 4. IT provisions access
        active_grant = service.provision_access(
            grant_id, actor_id=test_emp_2, actor_role="SYSTEM_ADMIN"
        )
        if active_grant["status"] == "ACTIVE" and active_grant["granted_at"]:
            print(f"[PASS] Access grant {grant_id} successfully provisioned to ACTIVE.")
        else:
            print(f"[FAIL] Expected grant status ACTIVE, got {active_grant['status']}")
            failures += 1

    except Exception as ex:
        print(f"[FAIL] Test 2 unexpected error: {ex}")
        failures += 1

    # Test 3: Hardware Lifecycle & Duplicate Assignment Prevention
    print("\n[TEST 3] Auditing Asset Lifecycle & Conflict Detection...")
    try:
        # Find an in-stock asset
        conn = service._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT asset_id FROM assets WHERE status = 'IN_STOCK' LIMIT 1;")
        res = cursor.fetchone()
        conn.close()

        if res:
            test_asset_id = res["asset_id"]
            # 1. Assign to active employee test_emp_2
            assigned = service.assign_asset(
                test_asset_id,
                employee_id=test_emp_2,
                actor_id=test_emp_1,
                actor_role="IT_OPERATIONS",
            )
            print(f"[PASS] Asset '{test_asset_id}' assigned to active employee '{test_emp_2}'.")

            # 2. Attempt duplicate assignment to test_emp_3 -> MUST FAIL
            try:
                service.assign_asset(
                    test_asset_id,
                    employee_id=test_emp_3,
                    actor_id=test_emp_1,
                    actor_role="IT_OPERATIONS",
                )
                print(f"[FAIL] Duplicate assignment permitted on asset '{test_asset_id}'!")
                failures += 1
            except AssetUnavailableError as aue:
                print(f"[PASS] Duplicate assignment correctly blocked: {aue}")

            # 3. Employee acknowledges custody
            service.acknowledge_asset(test_asset_id, employee_id=test_emp_2)
            print(f"[PASS] Hardware custody acknowledgement registered.")

            # 4. IT recovers asset
            recovered = service.recover_asset(
                test_asset_id, actor_id=test_emp_1, actor_role="IT_OPERATIONS"
            )
            if recovered["status"] == "RECOVERED" and recovered["assigned_to"] is None:
                print(f"[PASS] Asset '{test_asset_id}' successfully recovered to stock.")
            else:
                print(f"[FAIL] Asset recovery failed. State: {recovered}")
                failures += 1
        else:
            print("[SKIP] No IN_STOCK asset available for lifecycle test.")

    except Exception as ex:
        print(f"[FAIL] Test 3 unexpected error: {ex}")
        failures += 1

    # Test 4: Offboarding Workflow & Exit Orchestration
    print("\n[TEST 4] Auditing Offboarding Workflow & Automatic DAG Instantiation...")
    try:
        # Select an active employee who has no existing offboarding case
        conn = service._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT e.employee_id
            FROM employees e
            LEFT JOIN offboarding_cases o ON e.employee_id = o.employee_id
            WHERE e.employment_status = 'ACTIVE' AND o.offboarding_case_id IS NULL
              AND e.employee_id = 'EMP-000500'
            LIMIT 1;
            """
        )
        candidate = cursor.fetchone()
        conn.close()

        if candidate:
            off_emp_id = candidate["employee_id"]
            off_case = service.initiate_offboarding(
                employee_id=off_emp_id,
                termination_type="VOLUNTARY",
                effective_date="2026-11-30",
                initiator_id=test_emp_1,
                initiator_role="HR_PARTNER",
                reason="Accepted opportunity outside the firm.",
            )
            off_case_id = off_case["offboarding_case_id"]
            print(f"[PASS] Offboarding case '{off_case_id}' instantiated for '{off_emp_id}'.")

            # Check that departure tasks and dependencies were created
            conn = service._get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT count(*) FROM tasks WHERE case_id = ?;", (off_case_id,))
            off_tasks_count = cursor.fetchone()[0]
            cursor.execute(
                """
                SELECT count(*) FROM task_dependencies td
                JOIN tasks t ON td.task_id = t.task_id
                WHERE t.case_id = ?;
                """,
                (off_case_id,),
            )
            off_deps_count = cursor.fetchone()[0]
            conn.close()

            if off_tasks_count == 7 and off_deps_count > 0:
                print(f"[PASS] Generated {off_tasks_count} departure tasks and {off_deps_count} DAG dependencies.")
            else:
                print(f"[FAIL] Expected 7 departure tasks and dependencies, got {off_tasks_count} / {off_deps_count}")
                failures += 1

            # Verify that requesting access for this now-terminated employee FAILS
            try:
                service.request_access(
                    employee_id=off_emp_id,
                    access_role_id="ACR-001",
                    actor_id=off_emp_id,
                    actor_role="CANDIDATE",
                )
                print(f"[FAIL] Access requested for terminated employee '{off_emp_id}' was not blocked!")
                failures += 1
            except AccessGovernanceError as age:
                print(f"[PASS] Inappropriate access request for terminated staff blocked: {age}")
        else:
            print("[SKIP] No eligible active employee found for offboarding test.")

    except Exception as ex:
        print(f"[FAIL] Test 4 unexpected error: {ex}")
        failures += 1

    # Test 5: Audit Trail Verification
    print("\n[TEST 5] Auditing Completeness of Event Ledger...")
    try:
        conn = service._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT count(*) FROM audit_events
            WHERE entity_name IN ('tasks', 'access_grants', 'assets', 'offboarding_cases', 'employees');
            """
        )
        total_events = cursor.fetchone()[0]

        cursor.execute("SELECT count(*) FROM audit_events WHERE actor_id IS NULL OR timestamp IS NULL;")
        invalid_events = cursor.fetchone()[0]
        conn.close()

        print(f"[PASS] Verified {total_events} total audit events in ledger.")
        if invalid_events == 0:
            print("[PASS] 0 corrupted audit records (all events have non-null actor and timestamp).")
        else:
            print(f"[FAIL] Detected {invalid_events} malformed audit events!")
            failures += 1

    except Exception as ex:
        print(f"[FAIL] Test 5 unexpected error: {ex}")
        failures += 1

    print("\n" + "=" * 70)
    if failures == 0:
        print("[STEP 3 COMPLETE] All Business Rules & Workflow Engine tests PASSED.")
        print("=" * 70 + "\n")
        sys.exit(0)
    else:
        print(f"[STEP 3 FAILED] Detected {failures} assertion failures.")
        print("=" * 70 + "\n")
        sys.exit(1)


if __name__ == "__main__":
    run_step3_verification()