"""
YottaFlex 10-Dimension Integrity Validation Engine (Updated).
Performs comprehensive relational, lifecycle, DAG, reconciliation, and audit verification.
Distinguishes between clean baseline requirements and intentional injected anomalies.
Explicitly manages database connections to avoid Windows file lock errors.
"""

import json
import sqlite3
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class ValidationFinding:
    dimension: str
    rule_id: str
    severity: str  # 'CRITICAL', 'HIGH', 'MEDIUM', 'INFO'
    entity_name: str
    record_id: str
    is_injected_anomaly: bool
    description: str


class SystemValidator:
    """Audits database integrity across all 10 mandatory system dimensions."""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.findings: List[ValidationFinding] = []
        self.metrics: Dict[str, Any] = {}

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def run_all_validations(self) -> Dict[str, Any]:
        """
        Executes full 10-dimension audit suite.
        Explicitly closes the database connection to release Windows file locks.
        """
        self.findings.clear()
        self.metrics.clear()

        conn = self._get_connection()
        try:
            # 1. Primary Key Uniqueness
            self._validate_primary_keys(conn)

            # 2. Foreign Key Integrity
            self._validate_foreign_keys(conn)

            # 3. Field Constraints, Enums & Uniqueness
            self._validate_field_constraints(conn)

            # 4. Temporal Consistency & Date Ordering
            self._validate_date_ordering(conn)

            # 5. Task Dependency DAG & Cycle Detection
            self._validate_task_dependencies(conn)

            # 6. Access-to-Employment Reconciliation
            self._validate_access_reconciliation(conn)

            # 7. Asset Custody & Reconciliation
            self._validate_asset_reconciliation(conn)

            # 8. Case Lifecycle Consistency
            self._validate_case_consistency(conn)

            # 9. Arithmetic Reconciliation & Zero-Denominator Safety
            self._validate_arithmetic_reconciliation(conn)

            # 10. Audit Ledger Coverage & Completeness
            self._validate_audit_ledger(conn)
        finally:
            conn.close()

        # Separate baseline defects from injected anomalies
        baseline_defects = [f for f in self.findings if not f.is_injected_anomaly]
        injected_findings = [f for f in self.findings if f.is_injected_anomaly]

        summary = {
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
            "database": self.db_path.name,
            "total_findings": len(self.findings),
            "baseline_defects_count": len(baseline_defects),
            "injected_anomalies_detected": len(injected_findings),
            "metrics": self.metrics,
            "findings": [asdict(f) for f in self.findings],
        }
        return summary

    # ------------------------------------------------------------------------
    # 1. PRIMARY KEY UNIQUENESS
    # ------------------------------------------------------------------------
    def _validate_primary_keys(self, conn: sqlite3.Connection) -> None:
        cursor = conn.cursor()
        tables = [
            ("departments", "dept_id"),
            ("roles", "role_id"),
            ("access_roles", "access_role_id"),
            ("employees", "employee_id"),
            ("managers", "manager_id"),
            ("onboarding_cases", "onboarding_case_id"),
            ("offboarding_cases", "offboarding_case_id"),
            ("tasks", "task_id"),
            ("task_dependencies", "dependency_id"),
            ("access_grants", "grant_id"),
            ("assets", "asset_id"),
            ("audit_events", "event_id"),
        ]
        for tbl, pk in tables:
            cursor.execute(f"SELECT count(*), count(DISTINCT {pk}) FROM {tbl};")
            total, distinct = cursor.fetchone()
            if total != distinct:
                self.findings.append(ValidationFinding(
                    dimension="1_PRIMARY_KEYS",
                    rule_id="PK_UNIQUENESS_VIOLATION",
                    severity="CRITICAL",
                    entity_name=tbl,
                    record_id="MULTIPLE",
                    is_injected_anomaly=False,
                    description=f"Table {tbl} has {total - distinct} duplicate primary keys.",
                ))

    # ------------------------------------------------------------------------
    # 2. FOREIGN KEY INTEGRITY
    # ------------------------------------------------------------------------
    def _validate_foreign_keys(self, conn: sqlite3.Connection) -> None:
        cursor = conn.cursor()
        cursor.execute("PRAGMA foreign_key_check;")
        violations = cursor.fetchall()
        for v in violations:
            tbl, rowid, parent_tbl, fkid = v[0], v[1], v[2], v[3]
            self.findings.append(ValidationFinding(
                dimension="2_FOREIGN_KEYS",
                rule_id="FK_ORPHANED_REFERENCE",
                severity="CRITICAL",
                entity_name=tbl,
                record_id=str(rowid),
                is_injected_anomaly=False,
                description=f"Row {rowid} in {tbl} references non-existent key in {parent_tbl}.",
            ))

    # ------------------------------------------------------------------------
    # 3. FIELD CONSTRAINTS & ENUMS
    # ------------------------------------------------------------------------
    def _validate_field_constraints(self, conn: sqlite3.Connection) -> None:
        cursor = conn.cursor()
        cursor.execute("SELECT employee_id, email FROM employees WHERE email NOT LIKE '%_@__%.__%';")
        for r in cursor.fetchall():
            self.findings.append(ValidationFinding(
                dimension="3_FIELD_CONSTRAINTS",
                rule_id="INVALID_EMAIL_FORMAT",
                severity="HIGH",
                entity_name="employees",
                record_id=r["employee_id"],
                is_injected_anomaly=False,
                description=f"Invalid email pattern: {r['email']}",
            ))

    # ------------------------------------------------------------------------
    # 4. DATE ORDERING & CHRONOLOGY
    # ------------------------------------------------------------------------
    def _validate_date_ordering(self, conn: sqlite3.Connection) -> None:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT employee_id, start_date, termination_date FROM employees
            WHERE termination_date IS NOT NULL AND termination_date < start_date;
            """
        )
        for r in cursor.fetchall():
            self.findings.append(ValidationFinding(
                dimension="4_DATE_ORDERING",
                rule_id="TERMINATION_BEFORE_START",
                severity="CRITICAL",
                entity_name="employees",
                record_id=r["employee_id"],
                is_injected_anomaly=False,
                description=f"Termination date {r['termination_date']} is before start date {r['start_date']}.",
            ))

    # ------------------------------------------------------------------------
    # 5. TASK DEPENDENCY DAG & CYCLE DETECTION
    # ------------------------------------------------------------------------
    def _validate_task_dependencies(self, conn: sqlite3.Connection) -> None:
        cursor = conn.cursor()
        # Detect circular deadlock edges (Scenario 4)
        cursor.execute(
            """
            SELECT td1.dependency_id, td1.task_id, td1.prerequisite_task_id, td2.dependency_id AS partner_dep_id
            FROM task_dependencies td1
            JOIN task_dependencies td2
              ON td1.task_id = td2.prerequisite_task_id AND td1.prerequisite_task_id = td2.task_id
            WHERE td1.dependency_id < td2.dependency_id;
            """
        )
        for r in cursor.fetchall():
            # Check if either edge in this cycle is in labelled_anomalies
            cursor.execute(
                "SELECT count(*) FROM labelled_anomalies WHERE record_id IN (?, ?);",
                (r["dependency_id"], r["partner_dep_id"]),
            )
            is_injected = cursor.fetchone()[0] > 0
            self.findings.append(ValidationFinding(
                dimension="5_TASK_DEPENDENCIES",
                rule_id="TASK_DEPENDENCY_CYCLE",
                severity="CRITICAL",
                entity_name="task_dependencies",
                record_id=r["dependency_id"],
                is_injected_anomaly=is_injected,
                description=f"Circular dependency between {r['task_id']} and {r['prerequisite_task_id']}.",
            ))

    # ------------------------------------------------------------------------
    # 6. ACCESS RECONCILIATION
    # ------------------------------------------------------------------------
    def _validate_access_reconciliation(self, conn: sqlite3.Connection) -> None:
        cursor = conn.cursor()
        # 6.1 Terminated employee retains active grant (Scenario 3)
        cursor.execute(
            """
            SELECT g.grant_id, g.employee_id, e.termination_date
            FROM access_grants g
            JOIN employees e ON g.employee_id = e.employee_id
            WHERE g.status = 'ACTIVE' AND e.employment_status = 'TERMINATED';
            """
        )
        for r in cursor.fetchall():
            cursor.execute("SELECT count(*) FROM labelled_anomalies WHERE record_id = ?;", (r["grant_id"],))
            is_injected = cursor.fetchone()[0] > 0
            self.findings.append(ValidationFinding(
                dimension="6_ACCESS_RECONCILIATION",
                rule_id="TERMINATED_EMPLOYEE_ACTIVE_ACCESS",
                severity="CRITICAL",
                entity_name="access_grants",
                record_id=r["grant_id"],
                is_injected_anomaly=is_injected,
                description=f"Terminated employee {r['employee_id']} retains active access grant.",
            ))

        # 6.2 Pre-start or unapproved access (Scenario 1)
        cursor.execute(
            """
            SELECT g.grant_id, g.employee_id, g.granted_at, e.start_date
            FROM access_grants g
            JOIN employees e ON g.employee_id = e.employee_id
            WHERE g.status = 'ACTIVE' AND (g.granted_at < e.start_date OR g.approver_id IS NULL);
            """
        )
        for r in cursor.fetchall():
            cursor.execute("SELECT count(*) FROM labelled_anomalies WHERE record_id = ?;", (r["grant_id"],))
            is_injected = cursor.fetchone()[0] > 0
            self.findings.append(ValidationFinding(
                dimension="6_ACCESS_RECONCILIATION",
                rule_id="PRESTART_OR_UNAPPROVED_ACCESS",
                severity="CRITICAL",
                entity_name="access_grants",
                record_id=r["grant_id"],
                is_injected_anomaly=is_injected,
                description=f"Grant {r['grant_id']} active before start date {r['start_date']} or unapproved.",
            ))

    # ------------------------------------------------------------------------
    # 7. ASSET RECONCILIATION
    # ------------------------------------------------------------------------
    def _validate_asset_reconciliation(self, conn: sqlite3.Connection) -> None:
        cursor = conn.cursor()
        # 7.1 Duplicate laptop assignments (Scenario 2)
        cursor.execute(
            """
            SELECT assigned_to, count(*) as c, group_concat(asset_id) as ids
            FROM assets
            WHERE status = 'ASSIGNED' AND asset_type = 'LAPTOP' AND assigned_to IS NOT NULL
            GROUP BY assigned_to HAVING count(*) > 1;
            """
        )
        for r in cursor.fetchall():
            asset_ids = r["ids"].split(",")
            placeholders = ",".join(["?"] * len(asset_ids))
            # Check if any asset in this duplicate group was recorded as injected
            cursor.execute(
                f"SELECT count(*) FROM labelled_anomalies WHERE record_id IN ({placeholders});",
                asset_ids,
            )
            is_injected = cursor.fetchone()[0] > 0

            self.findings.append(ValidationFinding(
                dimension="7_ASSET_RECONCILIATION",
                rule_id="DUPLICATE_ASSET_ASSIGNMENT",
                severity="HIGH",
                entity_name="assets",
                record_id=r["ids"],
                is_injected_anomaly=is_injected,
                description=f"Custodian {r['assigned_to']} holds multiple active laptops ({r['ids']}).",
            ))

        # 7.2 Recovered asset retains custodian (Scenario 5)
        cursor.execute("SELECT asset_id, assigned_to FROM assets WHERE status = 'RECOVERED' AND assigned_to IS NOT NULL;")
        for r in cursor.fetchall():
            cursor.execute("SELECT count(*) FROM labelled_anomalies WHERE record_id = ?;", (r["asset_id"],))
            is_injected = cursor.fetchone()[0] > 0
            self.findings.append(ValidationFinding(
                dimension="7_ASSET_RECONCILIATION",
                rule_id="RECOVERED_ASSET_RETAINS_CUSTODIAN",
                severity="HIGH",
                entity_name="assets",
                record_id=r["asset_id"],
                is_injected_anomaly=is_injected,
                description=f"Asset {r['asset_id']} marked RECOVERED but retains custodian {r['assigned_to']}.",
            ))

    # ------------------------------------------------------------------------
    # 8. CASE CONSISTENCY
    # ------------------------------------------------------------------------
    def _validate_case_consistency(self, conn: sqlite3.Connection) -> None:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT e.employee_id FROM employees e
            LEFT JOIN offboarding_cases o ON e.employee_id = o.employee_id
            WHERE e.employment_status = 'TERMINATED' AND o.offboarding_case_id IS NULL;
            """
        )
        for r in cursor.fetchall():
            self.findings.append(ValidationFinding(
                dimension="8_CASE_CONSISTENCY",
                rule_id="MISSING_OFFBOARDING_CASE",
                severity="HIGH",
                entity_name="offboarding_cases",
                record_id=r["employee_id"],
                is_injected_anomaly=False,
                description=f"Terminated employee {r['employee_id']} lacks an offboarding case container.",
            ))

    # ------------------------------------------------------------------------
    # 9. ARITHMETIC RECONCILIATION & SAFE METRICS
    # ------------------------------------------------------------------------
    def _validate_arithmetic_reconciliation(self, conn: sqlite3.Connection) -> None:
        cursor = conn.cursor()

        # Task Completion Rate (Safe division against zero)
        cursor.execute("SELECT count(*) FROM tasks;")
        total_tasks = cursor.fetchone()[0]
        cursor.execute("SELECT count(*) FROM tasks WHERE status = 'COMPLETED';")
        comp_tasks = cursor.fetchone()[0]
        task_comp_rate = (comp_tasks / total_tasks * 100.0) if total_tasks > 0 else 0.0

        # Access Compliance Rate (Safe division against zero)
        cursor.execute("SELECT count(*) FROM access_grants WHERE status = 'ACTIVE';")
        total_active_grants = cursor.fetchone()[0]
        cursor.execute(
            """
            SELECT count(*) FROM access_grants g
            JOIN employees e ON g.employee_id = e.employee_id
            WHERE g.status = 'ACTIVE' AND (e.employment_status = 'TERMINATED' OR g.granted_at < e.start_date);
            """
        )
        violating_grants = cursor.fetchone()[0]
        compliant_grants = max(0, total_active_grants - violating_grants)
        access_comp_rate = (compliant_grants / total_active_grants * 100.0) if total_active_grants > 0 else 100.0

        # Asset Reconciliation Rate (Safe division against zero)
        cursor.execute("SELECT count(*) FROM assets;")
        total_assets = cursor.fetchone()[0]
        cursor.execute("SELECT count(*) FROM assets WHERE status = 'RECOVERED' AND assigned_to IS NOT NULL;")
        reconciled_assets = max(0, total_assets - cursor.fetchone()[0])
        asset_rec_rate = (reconciled_assets / total_assets * 100.0) if total_assets > 0 else 100.0

        self.metrics = {
            "total_tasks": total_tasks,
            "completed_tasks": comp_tasks,
            "task_completion_rate_pct": round(task_comp_rate, 2),
            "total_active_grants": total_active_grants,
            "access_compliance_rate_pct": round(access_comp_rate, 2),
            "total_assets": total_assets,
            "asset_reconciliation_rate_pct": round(asset_rec_rate, 2),
        }

    # ------------------------------------------------------------------------
    # 10. AUDIT LEDGER COVERAGE
    # ------------------------------------------------------------------------
    def _validate_audit_ledger(self, conn: sqlite3.Connection) -> None:
        cursor = conn.cursor()
        cursor.execute("SELECT count(*) FROM audit_events WHERE actor_id IS NULL OR timestamp IS NULL;")
        null_count = cursor.fetchone()[0]
        if null_count > 0:
            self.findings.append(ValidationFinding(
                dimension="10_AUDIT_LEDGER",
                rule_id="NULL_AUDIT_FIELD",
                severity="CRITICAL",
                entity_name="audit_events",
                record_id="MULTIPLE",
                is_injected_anomaly=False,
                description=f"Discovered {null_count} audit events with NULL actor or timestamp.",
            ))


def export_validation_report(summary: Dict[str, Any], export_path: Path) -> None:
    export_path.parent.mkdir(parents=True, exist_ok=True)
    with open(export_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)