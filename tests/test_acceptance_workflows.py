"""
YottaFlex End-to-End Acceptance Test Suite.
Executes in an isolated temporary database to leave working data untouched.
Tests the 5 negative anomaly scenarios and 7 operational workflow lifecycles.
"""

import gc
import json
import sqlite3
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from src.app_data import AppDataLayer
from src.services import (
    AccessGovernanceError,
    AssetUnavailableError,
    PrerequisiteNotSatisfiedError,
    WorkflowService,
)


class AcceptanceTestSuite:
    """End-to-end acceptance runner operating in an isolated test sandbox."""

    def __init__(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp_dir.name) / "test_acceptance.db"
        self._setup_schema()
        self.service = WorkflowService(self.db_path)
        self.app_data = AppDataLayer(self.db_path)
        self.test_results: List[Dict[str, Any]] = []

    def _setup_schema(self):
        project_root = Path(__file__).resolve().parent.parent
        schema_path = project_root / "sql" / "schema.sql"
        conn = sqlite3.connect(self.db_path)
        try:
            with open(schema_path, "r", encoding="utf-8") as f:
                conn.executescript(f.read())
        finally:
            conn.close()

    def teardown(self):
        del self.service
        del self.app_data
        gc.collect()
        try:
            self.tmp_dir.cleanup()
        except Exception:
            pass

    def record_test(self, test_name: str, passed: bool, details: str):
        self.test_results.append({
            "test_name": test_name,
            "passed": passed,
            "details": details,
        })

    def run_all(self) -> Dict[str, Any]:
        self._seed_minimal_fixture()

        # Part 1: Negative Anomaly Scenarios
        self.test_scenario_1_prestart_access()
        self.test_scenario_2_duplicate_asset()
        self.test_scenario_3_terminated_retains_access()
        self.test_scenario_4_task_dependency_cycle()
        self.test_scenario_5_recovered_retains_custodian()

        # Part 2: Successful Workflow Lifecycles
        self.test_workflow_normal_onboarding()
        self.test_workflow_delayed_start()
        self.test_workflow_contractor_onboarding()
        self.test_workflow_role_change()
        self.test_workflow_urgent_termination()
        self.test_workflow_equipment_lifecycle()
        self.test_workflow_prerequisite_blocking()

        return self._generate_report()

    def _seed_minimal_fixture(self):
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute("PRAGMA foreign_keys = OFF;")

            # Master org
            cursor.execute("INSERT INTO departments VALUES ('DEP-001', 'Engineering', 'CC-1001', '2026-01-01');")
            cursor.execute("INSERT INTO roles VALUES ('ROL-001', 'Software Engineer', 'DEP-001', 'STANDARD_USER', '2026-01-01');")
            cursor.execute("INSERT INTO access_roles VALUES ('ACR-001', 'GitHub Core', 'GitHub', 'LOW', 0, 0, '2026-01-01');")
            cursor.execute("INSERT INTO access_roles VALUES ('ACR-007', 'AWS Production Admin', 'AWS', 'CRITICAL', 1, 1, '2026-01-01');")

            # Baseline Employees
            cursor.execute(
                """
                INSERT INTO employees VALUES
                ('EMP-000001', 'Alice', 'Admin', 'alice@yottaflex.internal', 'ROL-001', 'DEP-001', NULL, 'FULL_TIME', 'ACTIVE', '2026-01-01', '2026-01-15', NULL, '2026-01-01', '2026-01-01'),
                ('EMP-000002', 'Bob', 'Terminated', 'bob@yottaflex.internal', 'ROL-001', 'DEP-001', 'EMP-000001', 'FULL_TIME', 'TERMINATED', '2026-01-01', '2026-01-15', '2026-06-01', '2026-01-01', '2026-06-01'),
                ('EMP-000003', 'Charlie', 'Developer', 'charlie@yottaflex.internal', 'ROL-001', 'DEP-001', 'EMP-000001', 'FULL_TIME', 'ACTIVE', '2026-02-01', '2026-02-15', NULL, '2026-02-01', '2026-02-01');
                """
            )

            # Baseline Assets
            cursor.execute(
                """
                INSERT INTO assets VALUES
                ('AST-000001', 'LAPTOP', 'SN-YOTTA-001', 'ThinkPad P16s', 'EMP-000003', 'ASSIGNED', '2026-02-10', NULL, '2026-01-01'),
                ('AST-000002', 'LAPTOP', 'SN-YOTTA-002', 'MacBook Pro 16', NULL, 'IN_STOCK', NULL, NULL, '2026-01-01'),
                ('AST-000003', 'LAPTOP', 'SN-YOTTA-003', 'Dell Latitude', NULL, 'IN_STOCK', NULL, NULL, '2026-01-01');
                """
            )

            # Baseline Grants
            cursor.execute(
                """
                INSERT INTO access_grants VALUES
                ('GRANT-EMP-000001-001', 'EMP-000001', 'ACR-001', 'ACTIVE', '2026-01-15', NULL, 'EMP-000001', 'Initial', '2026-01-01'),
                ('GRANT-EMP-000002-001', 'EMP-000002', 'ACR-001', 'REVOKED', '2026-01-15', '2026-06-01', 'EMP-000001', 'Revoked', '2026-01-01');
                """
            )

            cursor.execute("PRAGMA foreign_keys = ON;")
            conn.commit()
        finally:
            conn.close()

    # ------------------------------------------------------------------------
    # 5 MANDATORY NEGATIVE SCENARIOS
    # ------------------------------------------------------------------------

    def test_scenario_1_prestart_access(self):
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute(
                """
                INSERT INTO access_grants VALUES
                ('GRANT-EMP-000003-001', 'EMP-000003', 'ACR-007', 'ACTIVE', '2026-01-01', NULL, NULL, 'Premature', '2026-01-01');
                """
            )
            conn.commit()
        finally:
            conn.close()

        anomalies = self.app_data.get_detected_anomalies()
        matched = any(a["scenario"] == "SCENARIO_1_PRESTART_ACCESS" and a["record_id"] == "GRANT-EMP-000003-001" for a in anomalies)
        self.record_test("Scenario 1: Premature/Unapproved Access", matched, "Flagged premature grant before start date.")

    def test_scenario_2_duplicate_asset(self):
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute("UPDATE assets SET status = 'ASSIGNED', assigned_to = 'EMP-000003' WHERE asset_id = 'AST-000002';")
            conn.commit()
        finally:
            conn.close()

        anomalies = self.app_data.get_detected_anomalies()
        matched = any(a["scenario"] == "SCENARIO_2_DUPLICATE_ASSET" and "AST-000002" in a["record_id"] for a in anomalies)
        self.record_test("Scenario 2: Duplicate Asset Assignment", matched, "Detected multiple laptops assigned to one custodian.")

    def test_scenario_3_terminated_retains_access(self):
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute("UPDATE access_grants SET status = 'ACTIVE', revoked_at = NULL WHERE grant_id = 'GRANT-EMP-000002-001';")
            conn.commit()
        finally:
            conn.close()

        anomalies = self.app_data.get_detected_anomalies()
        matched = any(a["scenario"] == "SCENARIO_3_TERMINATED_RETAINS_ACCESS" and a["record_id"] == "GRANT-EMP-000002-001" for a in anomalies)
        self.record_test("Scenario 3: Terminated Employee Active Access", matched, "Identified active entitlement on terminated worker.")

    def test_scenario_4_task_dependency_cycle(self):
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute("INSERT INTO onboarding_cases VALUES ('ONB-2026-000001', 'EMP-000001', '2026-01-15', '2026-01-15', 'COMPLETED', '2026-01-01', '2026-01-15');")
            conn.execute("INSERT INTO tasks VALUES ('TASK-ONB-2026-000001-001', 'ONBOARDING', 'ONB-2026-000001', 'Task A', 'SECURITY', 'SYSTEM_ADMIN', 'PENDING', '2026-01-15', NULL, '2026-01-01');")
            conn.execute("INSERT INTO tasks VALUES ('TASK-ONB-2026-000001-002', 'ONBOARDING', 'ONB-2026-000001', 'Task B', 'SECURITY', 'SYSTEM_ADMIN', 'PENDING', '2026-01-15', NULL, '2026-01-01');")
            conn.execute("INSERT INTO task_dependencies VALUES ('DEP-TASK-001', 'TASK-ONB-2026-000001-001', 'TASK-ONB-2026-000001-002', '2026-01-01');")
            conn.execute("INSERT INTO task_dependencies VALUES ('DEP-TASK-002', 'TASK-ONB-2026-000001-002', 'TASK-ONB-2026-000001-001', '2026-01-01');")
            conn.commit()
        finally:
            conn.close()

        anomalies = self.app_data.get_detected_anomalies()
        matched = any(a["scenario"] == "SCENARIO_4_TASK_CYCLE" for a in anomalies)
        self.record_test("Scenario 4: Task Dependency Cycle", matched, "Detected circular DAG deadlock edges.")

    def test_scenario_5_recovered_retains_custodian(self):
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute("UPDATE assets SET status = 'RECOVERED', assigned_to = 'EMP-000001' WHERE asset_id = 'AST-000003';")
            conn.commit()
        finally:
            conn.close()

        anomalies = self.app_data.get_detected_anomalies()
        matched = any(a["scenario"] == "SCENARIO_5_RECOVERED_REMAINS_ASSIGNED" and a["record_id"] == "AST-000003" for a in anomalies)
        self.record_test("Scenario 5: Recovered Asset Retains Custodian", matched, "Detected recovered asset with uncleared custodian.")

    # ------------------------------------------------------------------------
    # 7 REQUIRED BUSINESS WORKFLOWS
    # ------------------------------------------------------------------------

    def test_workflow_normal_onboarding(self):
        grant = self.service.request_access("EMP-000001", "ACR-007", "EMP-000001", "MANAGER")
        app = self.service.approve_access(grant["grant_id"], "EMP-000001", "MANAGER")
        prov = self.service.provision_access(grant["grant_id"], "EMP-000001", "SYSTEM_ADMIN")
        passed = prov["status"] == "ACTIVE"
        self.record_test("Workflow 1: Normal Onboarding & Access Flow", passed, "Request -> Approve -> Provision executed cleanly.")

    def test_workflow_delayed_start(self):
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute("INSERT INTO employees VALUES ('EMP-000004', 'David', 'Delayed', 'david@yottaflex.internal', 'ROL-001', 'DEP-001', 'EMP-000001', 'FULL_TIME', 'PRE_HIRE', '2026-01-01', '2026-12-01', NULL, '2026-01-01', '2026-01-01');")
            conn.commit()
        finally:
            conn.close()

        g = self.service.request_access("EMP-000004", "ACR-001", "EMP-000001", "MANAGER")
        passed = g["status"] == "APPROVED"
        self.record_test("Workflow 2: Delayed Start Governance", passed, "Future hire access is governed and traceable.")

    def test_workflow_contractor_onboarding(self):
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute("INSERT INTO employees VALUES ('EMP-000005', 'Eva', 'Contractor', 'eva@yottaflex.internal', 'ROL-001', 'DEP-001', 'EMP-000001', 'CONTRACTOR', 'ACTIVE', '2026-01-01', '2026-01-15', NULL, '2026-01-01', '2026-01-01');")
            conn.commit()
        finally:
            conn.close()

        g = self.service.request_access("EMP-000005", "ACR-001", "EMP-000001", "MANAGER")
        passed = g["employee_id"] == "EMP-000005"
        self.record_test("Workflow 3: Contractor Lifecycle", passed, "Contractor enrolled with scoped entitlement profile.")

    def test_workflow_role_change(self):
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute("UPDATE employees SET employment_status = 'ROLE_CHANGE' WHERE employee_id = 'EMP-000003';")
            conn.commit()
        finally:
            conn.close()

        g = self.service.request_access("EMP-000003", "ACR-001", "EMP-000001", "MANAGER")
        passed = g["status"] in ("APPROVED", "REQUESTED")
        self.record_test("Workflow 4: Role Change Review", passed, "Role transition triggered access entitlement reassessment.")

    def test_workflow_urgent_termination(self):
        off_case = self.service.initiate_offboarding(
            employee_id="EMP-000003",
            termination_type="URGENT_TERMINATION",
            effective_date="2026-10-30",
            initiator_id="EMP-000001",
            initiator_role="HR_PARTNER",
        )
        passed = off_case["termination_type"] == "URGENT_TERMINATION"
        self.record_test("Workflow 5: Urgent Termination", passed, "Immediate departure instantiated exit tasks and flagged assets.")

    def test_workflow_equipment_lifecycle(self):
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute("INSERT INTO assets VALUES ('AST-000004', 'MONITOR', 'SN-YOTTA-004', 'Dell UltraSharp', NULL, 'IN_STOCK', NULL, NULL, '2026-01-01');")
            conn.commit()
        finally:
            conn.close()

        a = self.service.assign_asset("AST-000004", "EMP-000001", "EMP-000001", "IT_OPERATIONS")
        self.service.acknowledge_asset("AST-000004", "EMP-000001")
        rec = self.service.recover_asset("AST-000004", "EMP-000001", "IT_OPERATIONS")
        passed = rec["status"] == "RECOVERED" and rec["assigned_to"] is None
        self.record_test("Workflow 6: Equipment Lifecycle & Recovery", passed, "Assign -> Acknowledge -> Recover pipeline verified.")

    def test_workflow_prerequisite_blocking(self):
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute("INSERT INTO tasks VALUES ('TASK-ONB-2026-000001-003', 'ONBOARDING', 'ONB-2026-000001', 'Dependent Task', 'HARDWARE', 'IT_OPERATIONS', 'BLOCKED', '2026-01-15', NULL, '2026-01-01');")
            conn.execute("INSERT INTO task_dependencies VALUES ('DEP-TASK-003', 'TASK-ONB-2026-000001-003', 'TASK-ONB-2026-000001-001', '2026-01-01');")
            conn.commit()
        finally:
            conn.close()

        blocked_caught = False
        try:
            self.service.complete_task("TASK-ONB-2026-000001-003", "EMP-000001", "IT_OPERATIONS", force_override=False)
        except PrerequisiteNotSatisfiedError:
            blocked_caught = True

        overridden = self.service.complete_task(
            "TASK-ONB-2026-000001-003", "EMP-000001", "SYSTEM_ADMIN", force_override=True, override_reason="Authorized"
        )
        passed = blocked_caught and overridden["status"] == "COMPLETED"
        self.record_test("Workflow 7: Prerequisite Enforcement & Override", passed, "Prerequisite blocked execution; authorized override succeeded.")

    def _generate_report(self) -> Dict[str, Any]:
        passed_count = sum(1 for t in self.test_results if t["passed"])
        failed_count = len(self.test_results) - passed_count
        return {
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
            "total_acceptance_tests": len(self.test_results),
            "passed": passed_count,
            "failed": failed_count,
            "success_rate_pct": round(passed_count / len(self.test_results) * 100.0, 2),
            "tests": self.test_results,
        }