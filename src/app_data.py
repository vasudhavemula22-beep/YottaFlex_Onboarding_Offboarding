"""
YottaFlex Analytical Data Access Layer (Updated with Strict Connection Lifecycles).
Provides parameterized read queries and metric aggregators for the Streamlit dashboard.
Explicitly closes every SQLite connection to guarantee zero lingering file locks on Windows.
"""

import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import pandas as pd


class AppDataLayer:
    """Read-only analytical query engine querying yottaflex.db."""

    def __init__(self, db_path: Path):
        self.db_path = db_path

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    # ------------------------------------------------------------------------
    # 1. EXECUTIVE KPI AGGREGATIONS
    # ------------------------------------------------------------------------

    def get_executive_kpis(self) -> Dict[str, Any]:
        """Calculates high-level enterprise metrics across workforce and workflows."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()

            # Employee Counts
            cursor.execute("SELECT count(*) FROM employees;")
            total_emps = cursor.fetchone()[0]

            cursor.execute("SELECT count(*) FROM employees WHERE employment_status = 'ACTIVE';")
            active_emps = cursor.fetchone()[0]

            cursor.execute("SELECT count(*) FROM employees WHERE employment_status = 'TERMINATED';")
            term_emps = cursor.fetchone()[0]

            cursor.execute("SELECT count(*) FROM employees WHERE employment_status = 'PRE_HIRE';")
            prehire_emps = cursor.fetchone()[0]

            # In-flight cases (Count anything not yet completed or cancelled)
            cursor.execute("SELECT count(*) FROM onboarding_cases WHERE status NOT IN ('COMPLETED', 'CANCELLED');")
            active_onb = cursor.fetchone()[0]

            cursor.execute("SELECT count(*) FROM offboarding_cases WHERE status != 'COMPLETED';")
            active_off = cursor.fetchone()[0]

            # Tasks
            cursor.execute("SELECT count(*) FROM tasks WHERE status = 'COMPLETED';")
            comp_tasks = cursor.fetchone()[0]

            cursor.execute("SELECT count(*) FROM tasks;")
            total_tasks = cursor.fetchone()[0]

            cursor.execute("SELECT count(*) FROM tasks WHERE status = 'PENDING';")
            pending_tasks = cursor.fetchone()[0]

            cursor.execute("SELECT count(*) FROM tasks WHERE status = 'BLOCKED';")
            blocked_tasks = cursor.fetchone()[0]

            # Access Grants
            cursor.execute("SELECT count(*) FROM access_grants WHERE status = 'ACTIVE';")
            active_grants = cursor.fetchone()[0]

            cursor.execute(
                """
                SELECT count(*) FROM access_grants g
                JOIN employees e ON g.employee_id = e.employee_id
                WHERE g.status = 'ACTIVE' AND (e.employment_status = 'TERMINATED' OR g.granted_at < e.start_date);
                """
            )
            non_compliant_grants = cursor.fetchone()[0]
            compliance_rate = (
                ((active_grants - non_compliant_grants) / active_grants * 100.0)
                if active_grants > 0 else 100.0
            )

            # Assets
            cursor.execute("SELECT count(*) FROM assets;")
            total_assets = cursor.fetchone()[0]

            cursor.execute("SELECT count(*) FROM assets WHERE status = 'ASSIGNED';")
            assigned_assets = cursor.fetchone()[0]

            # Anomalies Count
            cursor.execute("SELECT count(*) FROM labelled_anomalies;")
            anom_count = cursor.fetchone()[0]

            return {
                "total_employees": total_emps,
                "active_employees": active_emps,
                "terminated_employees": term_emps,
                "prehire_employees": prehire_emps,
                "active_onboarding_cases": active_onb,
                "active_offboarding_cases": active_off,
                "task_completion_rate": (comp_tasks / total_tasks * 100.0) if total_tasks > 0 else 0.0,
                "pending_tasks": pending_tasks,
                "blocked_tasks": blocked_tasks,
                "active_grants": active_grants,
                "access_compliance_rate": compliance_rate,
                "total_assets": total_assets,
                "assigned_assets": assigned_assets,
                "total_exceptions": anom_count,
            }
        finally:
            conn.close()

    def get_employees_df(
        self,
        dept_id: Optional[str] = None,
        status: Optional[str] = None,
        search_query: Optional[str] = None,
    ) -> pd.DataFrame:
        query = """
            SELECT e.employee_id, e.first_name, e.last_name, e.email,
                   d.dept_name, r.role_title, e.employment_type, e.employment_status,
                   e.manager_id, e.start_date, e.termination_date
            FROM employees e
            JOIN departments d ON e.dept_id = d.dept_id
            JOIN roles r ON e.role_id = r.role_id
            WHERE 1=1
        """
        params = []
        if dept_id and dept_id != "ALL":
            query += " AND e.dept_id = ?"
            params.append(dept_id)
        if status and status != "ALL":
            query += " AND e.employment_status = ?"
            params.append(status)
        if search_query:
            query += " AND (e.first_name LIKE ? OR e.last_name LIKE ? OR e.employee_id LIKE ? OR e.email LIKE ?)"
            term = f"%{search_query.strip()}%"
            params.extend([term, term, term, term])

        query += " ORDER BY e.employee_id ASC LIMIT 250;"

        conn = self._get_connection()
        try:
            return pd.read_sql_query(query, conn, params=params)
        finally:
            conn.close()

    def get_departments_list(self) -> List[Tuple[str, str]]:
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT dept_id, dept_name FROM departments ORDER BY dept_id;")
            return cursor.fetchall()
        finally:
            conn.close()

    def get_onboarding_cases_df(self, status: Optional[str] = None) -> pd.DataFrame:
        query = """
            SELECT o.onboarding_case_id, o.employee_id, e.first_name || ' ' || e.last_name AS employee_name,
                   d.dept_name, o.target_start_date, o.actual_start_date, o.status, o.created_at
            FROM onboarding_cases o
            JOIN employees e ON o.employee_id = e.employee_id
            JOIN departments d ON e.dept_id = d.dept_id
            WHERE 1=1
        """
        params = []
        if status and status != "ALL":
            query += " AND o.status = ?"
            params.append(status)
        query += " ORDER BY o.onboarding_case_id ASC LIMIT 250;"

        conn = self._get_connection()
        try:
            return pd.read_sql_query(query, conn, params=params)
        finally:
            conn.close()

    def get_case_tasks_df(self, case_id: str) -> pd.DataFrame:
        query = """
            SELECT task_id, task_name, task_category, assigned_actor, status, due_date, completed_at
            FROM tasks
            WHERE case_id = ?
            ORDER BY task_id ASC;
        """
        conn = self._get_connection()
        try:
            return pd.read_sql_query(query, conn, params=(case_id,))
        finally:
            conn.close()

    def get_task_prerequisites(self, task_id: str) -> List[Dict[str, Any]]:
        query = """
            SELECT t.task_id, t.task_name, t.status
            FROM task_dependencies td
            JOIN tasks t ON td.prerequisite_task_id = t.task_id
            WHERE td.task_id = ?;
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(query, (task_id,))
            return [dict(r) for r in cursor.fetchall()]
        finally:
            conn.close()

    def get_access_grants_df(self, status: Optional[str] = None) -> pd.DataFrame:
        query = """
            SELECT g.grant_id, g.employee_id, e.first_name || ' ' || e.last_name AS employee_name,
                   r.role_name, r.system_name, r.risk_level, g.status, g.granted_at, g.revoked_at,
                   g.approver_id, g.notes
            FROM access_grants g
            JOIN employees e ON g.employee_id = e.employee_id
            JOIN access_roles r ON g.access_role_id = r.access_role_id
            WHERE 1=1
        """
        params = []
        if status and status != "ALL":
            query += " AND g.status = ?"
            params.append(status)
        query += " ORDER BY g.grant_id ASC LIMIT 250;"

        conn = self._get_connection()
        try:
            return pd.read_sql_query(query, conn, params=params)
        finally:
            conn.close()

    def get_access_roles_catalog(self) -> List[Dict[str, Any]]:
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT access_role_id, role_name, system_name, risk_level FROM access_roles ORDER BY access_role_id;")
            return [dict(r) for r in cursor.fetchall()]
        finally:
            conn.close()

    def get_assets_df(self, status: Optional[str] = None, asset_type: Optional[str] = None) -> pd.DataFrame:
        query = """
            SELECT a.asset_id, a.asset_type, a.serial_number, a.model_name,
                   a.status, a.assigned_to, e.first_name || ' ' || e.last_name AS custodian_name,
                   a.assigned_at, a.recovered_at
            FROM assets a
            LEFT JOIN employees e ON a.assigned_to = e.employee_id
            WHERE 1=1
        """
        params = []
        if status and status != "ALL":
            query += " AND a.status = ?"
            params.append(status)
        if asset_type and asset_type != "ALL":
            query += " AND a.asset_type = ?"
            params.append(asset_type)
        query += " ORDER BY a.asset_id ASC LIMIT 250;"

        conn = self._get_connection()
        try:
            return pd.read_sql_query(query, conn, params=params)
        finally:
            conn.close()

    def get_offboarding_cases_df(self, status: Optional[str] = None) -> pd.DataFrame:
        query = """
            SELECT o.offboarding_case_id, o.employee_id, e.first_name || ' ' || e.last_name AS employee_name,
                   o.termination_type, o.effective_date, o.status, o.initiated_by, o.completed_at
            FROM offboarding_cases o
            JOIN employees e ON o.employee_id = e.employee_id
            WHERE 1=1
        """
        params = []
        if status and status != "ALL":
            query += " AND o.status = ?"
            params.append(status)
        query += " ORDER BY o.offboarding_case_id ASC LIMIT 250;"

        conn = self._get_connection()
        try:
            return pd.read_sql_query(query, conn, params=params)
        finally:
            conn.close()

    def get_detected_anomalies(self) -> List[Dict[str, Any]]:
        """Executes the 5 canonical business-rule detection queries."""
        anomalies = []
        conn = self._get_connection()
        try:
            cursor = conn.cursor()

            # Rule 1: Premature or unapproved access
            cursor.execute(
                """
                SELECT g.grant_id, g.employee_id, g.granted_at, e.start_date
                FROM access_grants g
                JOIN employees e ON g.employee_id = e.employee_id
                WHERE g.status = 'ACTIVE' AND (g.granted_at < e.start_date OR g.approver_id IS NULL);
                """
            )
            for r in cursor.fetchall():
                anomalies.append({
                    "scenario": "SCENARIO_1_PRESTART_ACCESS",
                    "entity": "access_grants",
                    "record_id": r["grant_id"],
                    "severity": "CRITICAL",
                    "issue_type": "PRESTART_OR_UNAPPROVED_ACCESS",
                    "description": f"Grant {r['grant_id']} active before start date {r['start_date']} or unapproved.",
                })

            # Rule 2: Duplicate laptops
            cursor.execute(
                """
                SELECT assigned_to, count(*) as c, group_concat(asset_id) as ids
                FROM assets
                WHERE status = 'ASSIGNED' AND asset_type = 'LAPTOP' AND assigned_to IS NOT NULL
                GROUP BY assigned_to HAVING count(*) > 1;
                """
            )
            for r in cursor.fetchall():
                for a_id in r["ids"].split(","):
                    anomalies.append({
                        "scenario": "SCENARIO_2_DUPLICATE_ASSET",
                        "entity": "assets",
                        "record_id": a_id,
                        "severity": "HIGH",
                        "issue_type": "DUPLICATE_ASSET_ASSIGNMENT",
                        "description": f"Custodian {r['assigned_to']} holds multiple active laptops ({r['ids']}).",
                    })

            # Rule 3: Terminated employee active access
            cursor.execute(
                """
                SELECT g.grant_id, g.employee_id, e.termination_date
                FROM access_grants g
                JOIN employees e ON g.employee_id = e.employee_id
                WHERE g.status = 'ACTIVE' AND e.employment_status = 'TERMINATED';
                """
            )
            for r in cursor.fetchall():
                anomalies.append({
                    "scenario": "SCENARIO_3_TERMINATED_RETAINS_ACCESS",
                    "entity": "access_grants",
                    "record_id": r["grant_id"],
                    "severity": "CRITICAL",
                    "issue_type": "TERMINATED_EMPLOYEE_ACTIVE_ACCESS",
                    "description": f"Terminated employee {r['employee_id']} retains active grant {r['grant_id']}.",
                })

            # Rule 4: Circular task dependencies
            cursor.execute(
                """
                SELECT td1.dependency_id, td1.task_id, td1.prerequisite_task_id
                FROM task_dependencies td1
                JOIN task_dependencies td2
                  ON td1.task_id = td2.prerequisite_task_id AND td1.prerequisite_task_id = td2.task_id;
                """
            )
            for r in cursor.fetchall():
                anomalies.append({
                    "scenario": "SCENARIO_4_TASK_CYCLE",
                    "entity": "task_dependencies",
                    "record_id": r["dependency_id"],
                    "severity": "CRITICAL",
                    "issue_type": "TASK_DEPENDENCY_CYCLE",
                    "description": f"Circular deadlock edge between {r['task_id']} and {r['prerequisite_task_id']}.",
                })

            # Rule 5: Recovered asset retains custodian
            cursor.execute(
                """
                SELECT asset_id, assigned_to FROM assets
                WHERE status = 'RECOVERED' AND assigned_to IS NOT NULL;
                """
            )
            for r in cursor.fetchall():
                anomalies.append({
                    "scenario": "SCENARIO_5_RECOVERED_REMAINS_ASSIGNED",
                    "entity": "assets",
                    "record_id": r["asset_id"],
                    "severity": "HIGH",
                    "issue_type": "RECOVERED_ASSET_RETAINS_CUSTODIAN",
                    "description": f"Asset {r['asset_id']} marked RECOVERED but retains custodian {r['assigned_to']}.",
                })

            return anomalies
        finally:
            conn.close()

    def get_audit_trail_df(
        self, entity_name: Optional[str] = None, action: Optional[str] = None
    ) -> pd.DataFrame:
        query = """
            SELECT event_id, entity_name, record_id, action, actor_id, actor_role, timestamp, details
            FROM audit_events
            WHERE 1=1
        """
        params = []
        if entity_name and entity_name != "ALL":
            query += " AND entity_name = ?"
            params.append(entity_name)
        if action and action != "ALL":
            query += " AND action = ?"
            params.append(action)

        query += " ORDER BY event_id DESC LIMIT 250;"

        conn = self._get_connection()
        try:
            return pd.read_sql_query(query, conn, params=params)
        finally:
            conn.close()