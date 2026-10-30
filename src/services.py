"""
YottaFlex Core Business Logic and Workflow Engine (Updated).
Provides transactional service functions for onboarding, task execution,
access provisioning, equipment lifecycle management, offboarding, and auditing.
"""

import json
import sqlite3
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from src.templates import (
    DEPARTMENT_ASSET_BUNDLES,
    OFFBOARDING_TASK_TEMPLATES,
    ONBOARDING_TASK_TEMPLATES,
)


class WorkflowEngineError(Exception):
    pass


class PrerequisiteNotSatisfiedError(WorkflowEngineError):
    pass


class InvalidLifecycleTransitionError(WorkflowEngineError):
    pass


class AccessGovernanceError(WorkflowEngineError):
    pass


class AssetUnavailableError(WorkflowEngineError):
    pass


class EntityNotFoundError(WorkflowEngineError):
    pass


class WorkflowService:
    def __init__(self, db_path: Path):
        self.db_path = db_path

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.row_factory = sqlite3.Row
        return conn

    def _now(self, simulated_dt: Optional[str] = None) -> str:
        if simulated_dt:
            return simulated_dt
        return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

    def _generate_audit_id(self, cursor: sqlite3.Cursor) -> str:
        cursor.execute("SELECT max(CAST(substr(event_id, 5) AS INTEGER)) FROM audit_events;")
        res = cursor.fetchone()[0]
        next_seq = (res or 0) + 1
        return f"AUD-{next_seq:010d}"

    def _log_audit_event(
        self,
        cursor: sqlite3.Cursor,
        entity_name: str,
        record_id: str,
        action: str,
        actor_id: str,
        actor_role: str,
        old_val: Optional[Dict[str, Any]],
        new_val: Optional[Dict[str, Any]],
        details: str,
        timestamp: Optional[str] = None,
    ) -> str:
        audit_id = self._generate_audit_id(cursor)
        ts = timestamp or self._now()
        cursor.execute(
            """
            INSERT INTO audit_events (
                event_id, entity_name, record_id, action, actor_id, actor_role,
                old_values_json, new_values_json, timestamp, details
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                audit_id,
                entity_name,
                record_id,
                action,
                actor_id,
                actor_role,
                json.dumps(old_val) if old_val else None,
                json.dumps(new_val) if new_val else None,
                ts,
                details,
            ),
        )
        return audit_id

    def complete_task(
        self,
        task_id: str,
        actor_id: str,
        actor_role: str,
        force_override: bool = False,
        override_reason: Optional[str] = None,
        simulated_dt: Optional[str] = None,
    ) -> Dict[str, Any]:
        ts = self._now(simulated_dt)
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM tasks WHERE task_id = ?;", (task_id,))
            task = cursor.fetchone()
            if not task:
                raise EntityNotFoundError(f"Task '{task_id}' not found.")

            if task["status"] == "COMPLETED":
                return dict(task)

            cursor.execute(
                """
                SELECT t.task_id, t.task_name, t.status
                FROM task_dependencies td
                JOIN tasks t ON td.prerequisite_task_id = t.task_id
                WHERE td.task_id = ?;
                """,
                (task_id,),
            )
            prereqs = cursor.fetchall()
            unmet_prereqs = [p for p in prereqs if p["status"] not in ("COMPLETED", "WAIVED")]

            if unmet_prereqs and not force_override:
                names = [f"{p['task_id']} ({p['task_name']}: {p['status']})" for p in unmet_prereqs]
                raise PrerequisiteNotSatisfiedError(
                    f"Cannot complete '{task_id}'. Unmet prerequisites: {', '.join(names)}"
                )

            action = "OVERRIDE" if force_override else "UPDATE"
            old_val = {"status": task["status"], "completed_at": task["completed_at"]}
            new_val = {"status": "COMPLETED", "completed_at": ts}

            cursor.execute(
                "UPDATE tasks SET status = 'COMPLETED', completed_at = ? WHERE task_id = ?;",
                (ts, task_id),
            )

            details = f"Task completed by {actor_role}."
            if force_override:
                details = f"Authorized override applied: {override_reason or 'No justification provided'}"

            self._log_audit_event(
                cursor, "tasks", task_id, action, actor_id, actor_role, old_val, new_val, details, ts
            )

            cursor.execute(
                """
                SELECT td.task_id
                FROM task_dependencies td
                JOIN tasks t ON td.task_id = t.task_id
                WHERE td.prerequisite_task_id = ? AND t.status = 'BLOCKED';
                """,
                (task_id,),
            )
            downstream = cursor.fetchall()
            for ds in downstream:
                ds_id = ds["task_id"]
                cursor.execute(
                    """
                    SELECT count(*) FROM task_dependencies td
                    JOIN tasks t ON td.prerequisite_task_id = t.task_id
                    WHERE td.task_id = ? AND t.status NOT IN ('COMPLETED', 'WAIVED');
                    """,
                    (ds_id,),
                )
                remaining = cursor.fetchone()[0]
                if remaining == 0:
                    cursor.execute("UPDATE tasks SET status = 'PENDING' WHERE task_id = ?;", (ds_id,))
                    self._log_audit_event(
                        cursor,
                        "tasks",
                        ds_id,
                        "UPDATE",
                        "SYSTEM",
                        "SYSTEM_ADMIN",
                        {"status": "BLOCKED"},
                        {"status": "PENDING"},
                        f"All prerequisites satisfied. Task unblocked following completion of {task_id}.",
                        ts,
                    )

            conn.commit()
            cursor.execute("SELECT * FROM tasks WHERE task_id = ?;", (task_id,))
            return dict(cursor.fetchone())

    def request_access(
        self,
        employee_id: str,
        access_role_id: str,
        actor_id: str,
        actor_role: str,
        notes: str = "Standard access request",
        simulated_dt: Optional[str] = None,
    ) -> Dict[str, Any]:
        ts = self._now(simulated_dt)
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM employees WHERE employee_id = ?;", (employee_id,))
            emp = cursor.fetchone()
            if not emp:
                raise EntityNotFoundError(f"Employee '{employee_id}' not found.")
            if emp["employment_status"] == "TERMINATED":
                raise AccessGovernanceError(f"Cannot request access for terminated employee '{employee_id}'.")

            cursor.execute("SELECT * FROM access_roles WHERE access_role_id = ?;", (access_role_id,))
            role = cursor.fetchone()
            if not role:
                raise EntityNotFoundError(f"Access Role '{access_role_id}' not found.")

            cursor.execute("SELECT count(*) FROM access_grants WHERE employee_id = ?;", (employee_id,))
            count = cursor.fetchone()[0]
            grant_id = f"GRANT-{employee_id}-{count + 1:03d}"

            requires_approval = bool(role["requires_manager_approval"] or role["requires_hr_approval"])
            initial_status = "REQUESTED" if requires_approval else "APPROVED"

            cursor.execute(
                """
                INSERT INTO access_grants (
                    grant_id, employee_id, access_role_id, status, granted_at,
                    revoked_at, approver_id, notes, created_at
                ) VALUES (?, ?, ?, ?, NULL, NULL, NULL, ?, ?);
                """,
                (grant_id, employee_id, access_role_id, initial_status, notes, ts),
            )

            self._log_audit_event(
                cursor,
                "access_grants",
                grant_id,
                "INSERT",
                actor_id,
                actor_role,
                None,
                {"status": initial_status, "role": access_role_id},
                f"Access entitlement requested for {role['role_name']}.",
                ts,
            )

            conn.commit()
            cursor.execute("SELECT * FROM access_grants WHERE grant_id = ?;", (grant_id,))
            return dict(cursor.fetchone())

    def approve_access(
        self,
        grant_id: str,
        approver_id: str,
        approver_role: str,
        notes: str = "Access request approved.",
        simulated_dt: Optional[str] = None,
    ) -> Dict[str, Any]:
        ts = self._now(simulated_dt)
        if approver_role not in ("MANAGER", "HR_PARTNER", "SYSTEM_ADMIN"):
            raise AccessGovernanceError(f"Role '{approver_role}' is not authorized to approve access grants.")

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM access_grants WHERE grant_id = ?;", (grant_id,))
            grant = cursor.fetchone()
            if not grant:
                raise EntityNotFoundError(f"Grant '{grant_id}' not found.")

            if grant["status"] != "REQUESTED":
                raise InvalidLifecycleTransitionError(
                    f"Cannot approve grant '{grant_id}' with status '{grant['status']}'. Must be REQUESTED."
                )

            cursor.execute(
                """
                UPDATE access_grants
                SET status = 'APPROVED', approver_id = ?, notes = ?
                WHERE grant_id = ?;
                """,
                (approver_id, notes, grant_id),
            )

            self._log_audit_event(
                cursor,
                "access_grants",
                grant_id,
                "UPDATE",
                approver_id,
                approver_role,
                {"status": "REQUESTED"},
                {"status": "APPROVED", "approver": approver_id},
                notes,
                ts,
            )

            conn.commit()
            cursor.execute("SELECT * FROM access_grants WHERE grant_id = ?;", (grant_id,))
            return dict(cursor.fetchone())

    def provision_access(
        self,
        grant_id: str,
        actor_id: str,
        actor_role: str,
        simulated_dt: Optional[str] = None,
    ) -> Dict[str, Any]:
        ts = self._now(simulated_dt)
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT g.*, e.employment_status, e.start_date
                FROM access_grants g
                JOIN employees e ON g.employee_id = e.employee_id
                WHERE g.grant_id = ?;
                """,
                (grant_id,),
            )
            record = cursor.fetchone()
            if not record:
                raise EntityNotFoundError(f"Grant '{grant_id}' not found.")

            if record["status"] != "APPROVED":
                raise AccessGovernanceError(
                    f"Cannot provision grant '{grant_id}'. Current status is '{record['status']}' (expected APPROVED)."
                )

            if record["employment_status"] == "TERMINATED":
                raise AccessGovernanceError(
                    f"Cannot provision access to terminated employee '{record['employee_id']}'."
                )

            cursor.execute(
                "UPDATE access_grants SET status = 'ACTIVE', granted_at = ? WHERE grant_id = ?;",
                (ts, grant_id),
            )

            self._log_audit_event(
                cursor,
                "access_grants",
                grant_id,
                "UPDATE",
                actor_id,
                actor_role,
                {"status": "APPROVED"},
                {"status": "ACTIVE", "granted_at": ts},
                "Simulated provisioning executed successfully in identity system.",
                ts,
            )

            conn.commit()
            cursor.execute("SELECT * FROM access_grants WHERE grant_id = ?;", (grant_id,))
            return dict(cursor.fetchone())

    def revoke_access(
        self,
        grant_id: str,
        actor_id: str,
        actor_role: str,
        reason: str = "Standard departure revocation",
        simulated_dt: Optional[str] = None,
    ) -> Dict[str, Any]:
        ts = self._now(simulated_dt)
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM access_grants WHERE grant_id = ?;", (grant_id,))
            grant = cursor.fetchone()
            if not grant:
                raise EntityNotFoundError(f"Grant '{grant_id}' not found.")

            old_status = grant["status"]
            cursor.execute(
                "UPDATE access_grants SET status = 'REVOKED', revoked_at = ?, notes = ? WHERE grant_id = ?;",
                (ts, reason, grant_id),
            )

            self._log_audit_event(
                cursor,
                "access_grants",
                grant_id,
                "UPDATE",
                actor_id,
                actor_role,
                {"status": old_status},
                {"status": "REVOKED", "revoked_at": ts},
                reason,
                ts,
            )

            conn.commit()
            cursor.execute("SELECT * FROM access_grants WHERE grant_id = ?;", (grant_id,))
            return dict(cursor.fetchone())

    def assign_asset(
        self,
        asset_id: str,
        employee_id: str,
        actor_id: str,
        actor_role: str,
        simulated_dt: Optional[str] = None,
    ) -> Dict[str, Any]:
        ts = self._now(simulated_dt)
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM employees WHERE employee_id = ?;", (employee_id,))
            emp = cursor.fetchone()
            if not emp:
                raise EntityNotFoundError(f"Employee '{employee_id}' not found.")
            if emp["employment_status"] == "TERMINATED":
                raise WorkflowEngineError(f"Cannot assign hardware to terminated employee '{employee_id}'.")

            cursor.execute("SELECT * FROM assets WHERE asset_id = ?;", (asset_id,))
            asset = cursor.fetchone()
            if not asset:
                raise EntityNotFoundError(f"Asset '{asset_id}' not found.")

            if asset["status"] == "ASSIGNED":
                raise AssetUnavailableError(
                    f"Asset '{asset_id}' is already ASSIGNED to custodian '{asset['assigned_to']}'."
                )
            if asset["status"] not in ("IN_STOCK", "PROVISIONED", "RECOVERED"):
                raise AssetUnavailableError(
                    f"Asset '{asset_id}' has status '{asset['status']}' and cannot be assigned."
                )

            old_val = {"status": asset["status"], "assigned_to": asset["assigned_to"]}
            new_val = {"status": "ASSIGNED", "assigned_to": employee_id, "assigned_at": ts}

            cursor.execute(
                """
                UPDATE assets
                SET status = 'ASSIGNED', assigned_to = ?, assigned_at = ?, recovered_at = NULL
                WHERE asset_id = ?;
                """,
                (employee_id, ts, asset_id),
            )

            self._log_audit_event(
                cursor,
                "assets",
                asset_id,
                "UPDATE",
                actor_id,
                actor_role,
                old_val,
                new_val,
                f"Hardware asset assigned to {employee_id}.",
                ts,
            )

            conn.commit()
            cursor.execute("SELECT * FROM assets WHERE asset_id = ?;", (asset_id,))
            return dict(cursor.fetchone())

    def acknowledge_asset(
        self,
        asset_id: str,
        employee_id: str,
        simulated_dt: Optional[str] = None,
    ) -> Dict[str, Any]:
        ts = self._now(simulated_dt)
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM assets WHERE asset_id = ?;", (asset_id,))
            asset = cursor.fetchone()
            if not asset:
                raise EntityNotFoundError(f"Asset '{asset_id}' not found.")
            if asset["assigned_to"] != employee_id:
                raise WorkflowEngineError(
                    f"Employee '{employee_id}' is not the recorded custodian for asset '{asset_id}'."
                )

            self._log_audit_event(
                cursor,
                "assets",
                asset_id,
                "UPDATE",
                employee_id,
                "CANDIDATE",
                {"status": asset["status"]},
                {"status": asset["status"], "acknowledged": True},
                "Formal equipment custody acknowledgement signed by employee.",
                ts,
            )

            conn.commit()
            return dict(asset)

    def recover_asset(
        self,
        asset_id: str,
        actor_id: str,
        actor_role: str,
        simulated_dt: Optional[str] = None,
    ) -> Dict[str, Any]:
        ts = self._now(simulated_dt)
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM assets WHERE asset_id = ?;", (asset_id,))
            asset = cursor.fetchone()
            if not asset:
                raise EntityNotFoundError(f"Asset '{asset_id}' not found.")

            old_val = {"status": asset["status"], "assigned_to": asset["assigned_to"]}
            new_val = {"status": "RECOVERED", "assigned_to": None, "recovered_at": ts}

            cursor.execute(
                """
                UPDATE assets
                SET status = 'RECOVERED', assigned_to = NULL, recovered_at = ?
                WHERE asset_id = ?;
                """,
                (ts, asset_id),
            )

            self._log_audit_event(
                cursor,
                "assets",
                asset_id,
                "UPDATE",
                actor_id,
                actor_role,
                old_val,
                new_val,
                "Hardware inspected, wiped, and recovered to inventory.",
                ts,
            )

            conn.commit()
            cursor.execute("SELECT * FROM assets WHERE asset_id = ?;", (asset_id,))
            return dict(cursor.fetchone())

    def initiate_offboarding(
        self,
        employee_id: str,
        termination_type: str,
        effective_date: str,
        initiator_id: str,
        initiator_role: str,
        reason: str = "Standard departure",
        simulated_dt: Optional[str] = None,
    ) -> Dict[str, Any]:
        ts = self._now(simulated_dt)
        valid_term_types = ("VOLUNTARY", "INVOLUNTARY", "CONTRACT_END", "URGENT_TERMINATION")
        if termination_type not in valid_term_types:
            raise WorkflowEngineError(f"Invalid termination type '{termination_type}'.")

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM employees WHERE employee_id = ?;", (employee_id,))
            emp = cursor.fetchone()
            if not emp:
                raise EntityNotFoundError(f"Employee '{employee_id}' not found.")

            cursor.execute("SELECT * FROM offboarding_cases WHERE employee_id = ?;", (employee_id,))
            existing_case = cursor.fetchone()
            if existing_case:
                raise WorkflowEngineError(
                    f"Offboarding case '{existing_case['offboarding_case_id']}' already exists for employee."
                )

            cursor.execute("SELECT count(*) FROM offboarding_cases;")
            off_count = cursor.fetchone()[0] + 1
            case_id = f"OFF-2026-{off_count:06d}"

            # 1. Update Employee Status
            cursor.execute(
                """
                UPDATE employees
                SET employment_status = 'TERMINATED', termination_date = ?, updated_at = ?
                WHERE employee_id = ?;
                """,
                (effective_date, ts, employee_id),
            )
            self._log_audit_event(
                cursor,
                "employees",
                employee_id,
                "UPDATE",
                initiator_id,
                initiator_role,
                {"status": emp["employment_status"]},
                {"status": "TERMINATED", "termination_date": effective_date},
                f"Offboarding initiated ({termination_type}). Reason: {reason}",
                ts,
            )

            # 2. Insert Offboarding Case
            cursor.execute(
                """
                INSERT INTO offboarding_cases (
                    offboarding_case_id, employee_id, initiated_by, initiated_at,
                    termination_type, effective_date, status, completed_at, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, 'INITIATED', NULL, ?);
                """,
                (case_id, employee_id, initiator_id, ts, termination_type, effective_date, ts),
            )
            self._log_audit_event(
                cursor,
                "offboarding_cases",
                case_id,
                "INSERT",
                initiator_id,
                initiator_role,
                None,
                {"status": "INITIATED", "effective_date": effective_date},
                "Offboarding lifecycle container instantiated.",
                ts,
            )

            # 3. Automatically Revoke Active Grants on Departure
            cursor.execute(
                """
                UPDATE access_grants
                SET status = 'REVOKED', revoked_at = ?, notes = 'Automated departure revocation.'
                WHERE employee_id = ? AND status = 'ACTIVE';
                """,
                (ts, employee_id),
            )

            # 4. Instantiate Departure Tasks and Dependencies from Templates
            term_dt = datetime.strptime(effective_date, "%Y-%m-%d").date()
            task_id_by_seq = {}

            for tmpl in OFFBOARDING_TASK_TEMPLATES:
                t_id = f"TASK-{case_id}-{tmpl.sequence:03d}"
                task_id_by_seq[tmpl.sequence] = t_id
                due_dt = term_dt + timedelta(days=tmpl.offset_days)
                initial_task_status = "PENDING" if len(tmpl.prerequisite_sequences) == 0 else "BLOCKED"

                cursor.execute(
                    """
                    INSERT INTO tasks (
                        task_id, case_type, case_id, task_name, task_category,
                        assigned_actor, status, due_date, completed_at, created_at
                    ) VALUES (?, 'OFFBOARDING', ?, ?, ?, ?, ?, ?, NULL, ?);
                    """,
                    (
                        t_id,
                        case_id,
                        tmpl.name,
                        tmpl.category,
                        tmpl.assigned_actor,
                        initial_task_status,
                        due_dt.strftime("%Y-%m-%d"),
                        ts,
                    ),
                )

            for tmpl in OFFBOARDING_TASK_TEMPLATES:
                current_task_id = task_id_by_seq[tmpl.sequence]
                for prereq_seq in tmpl.prerequisite_sequences:
                    prereq_task_id = task_id_by_seq[prereq_seq]
                    dep_id = f"DEP-{current_task_id}-{prereq_seq:03d}"
                    cursor.execute(
                        """
                        INSERT INTO task_dependencies (
                            dependency_id, task_id, prerequisite_task_id, created_at
                        ) VALUES (?, ?, ?, ?);
                        """,
                        (dep_id, current_task_id, prereq_task_id, ts),
                    )

            # 5. Flag Assigned Assets for Return
            cursor.execute(
                """
                UPDATE assets
                SET status = 'RETURN_REQUESTED'
                WHERE assigned_to = ? AND status = 'ASSIGNED';
                """,
                (employee_id,),
            )

            conn.commit()
            cursor.execute("SELECT * FROM offboarding_cases WHERE offboarding_case_id = ?;", (case_id,))
            return dict(cursor.fetchone())

    def verify_access_compliance(self, employee_id: Optional[str] = None) -> List[Dict[str, Any]]:
        query = """
            SELECT g.grant_id, g.employee_id, e.employment_status, e.start_date, e.termination_date,
                   g.status AS grant_status, g.granted_at, r.role_name
            FROM access_grants g
            JOIN employees e ON g.employee_id = e.employee_id
            JOIN access_roles r ON g.access_role_id = r.access_role_id
            WHERE g.status = 'ACTIVE'
        """
        params = []
        if employee_id:
            query += " AND g.employee_id = ?"
            params.append(employee_id)

        violations = []
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            for row in cursor.fetchall():
                if row["employment_status"] == "TERMINATED":
                    violations.append({
                        "grant_id": row["grant_id"],
                        "employee_id": row["employee_id"],
                        "issue_type": "TERMINATED_EMPLOYEE_ACTIVE_ACCESS",
                        "severity": "CRITICAL",
                        "description": f"Employee {row['employee_id']} is TERMINATED but retains active grant.",
                    })
        return violations