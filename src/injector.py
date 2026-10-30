"""
YottaFlex Deterministic Anomaly Injection Engine (Updated).
Injects the 5 mandatory negative test scenarios into the SQLite baseline database
and records ground-truth metadata in both the database catalog and exported ledgers.
Operates seamlessly across both starter (60 assets) and full (1,200 assets) modes.
"""

import csv
import json
import random
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple


class AnomalyInjector:
    """
    Coordinates atomic injection of 5 negative compliance scenarios
    while preserving unrelated baseline data and referential integrity.
    """

    def __init__(self, db_path: Path, seed: int = 20261022):
        self.db_path = db_path
        self.seed = seed
        self.rng = random.Random(seed)
        self.anomaly_counter = 0

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.row_factory = sqlite3.Row
        return conn

    def _next_anomaly_id(self) -> str:
        self.anomaly_counter += 1
        return f"ANO-{self.anomaly_counter:06d}"

    def _log_audit_override(
        self,
        cursor: sqlite3.Cursor,
        entity_name: str,
        record_id: str,
        old_val: Dict[str, Any],
        new_val: Dict[str, Any],
        description: str,
    ) -> None:
        """Appends an EXCEPTION / OVERRIDE audit event for traceability."""
        cursor.execute("SELECT max(CAST(substr(event_id, 5) AS INTEGER)) FROM audit_events;")
        res = cursor.fetchone()[0]
        next_seq = (res or 0) + 1
        audit_id = f"AUD-{next_seq:010d}"
        now_ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

        cursor.execute(
            """
            INSERT INTO audit_events (
                event_id, entity_name, record_id, action, actor_id, actor_role,
                old_values_json, new_values_json, timestamp, details
            ) VALUES (?, ?, ?, 'EXCEPTION', 'SYSTEM_INJECTOR', 'SYSTEM_ADMIN', ?, ?, ?, ?);
            """,
            (
                audit_id,
                entity_name,
                record_id,
                json.dumps(old_val),
                json.dumps(new_val),
                now_ts,
                f"Synthetic negative test case injected: {description}",
            ),
        )

    def inject_all(self, target_per_scenario: int = 1) -> List[Dict[str, Any]]:
        ground_truth_records: List[Dict[str, Any]] = []

        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Clean prior anomalies to prevent duplicate accumulation
            cursor.execute("DELETE FROM labelled_anomalies;")
            self.anomaly_counter = 0

            # 1. SCENARIO 1: Access granted before start date or approval
            s1_records = self._inject_scenario_1(cursor, target_per_scenario)
            ground_truth_records.extend(s1_records)

            # 2. SCENARIO 2: Duplicate asset assignment
            s2_records = self._inject_scenario_2(cursor, target_per_scenario)
            ground_truth_records.extend(s2_records)

            # 3. SCENARIO 3: Terminated employee retains active access grant
            s3_records = self._inject_scenario_3(cursor, target_per_scenario)
            ground_truth_records.extend(s3_records)

            # 4. SCENARIO 4: Task dependency cycle
            s4_records = self._inject_scenario_4(cursor, target_per_scenario)
            ground_truth_records.extend(s4_records)

            # 5. SCENARIO 5: Asset marked recovered remains assigned to custodian
            s5_records = self._inject_scenario_5(cursor, target_per_scenario, excluded_assets=[r["record_id"] for r in s2_records])
            ground_truth_records.extend(s5_records)

            # Record all in labelled_anomalies table
            for gt in ground_truth_records:
                cursor.execute(
                    """
                    INSERT INTO labelled_anomalies (
                        anomaly_id, scenario_id, entity_name, record_id,
                        issue_type, description, is_ground_truth, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, 1, strftime('%Y-%m-%d %H:%M:%S', 'now'));
                    """,
                    (
                        gt["anomaly_id"],
                        gt["scenario_id"],
                        gt["entity_name"],
                        gt["record_id"],
                        gt["issue_type"],
                        gt["expected_finding"],
                    ),
                )

            conn.commit()

        return ground_truth_records

    def _inject_scenario_1(self, cursor: sqlite3.Cursor, count: int) -> List[Dict[str, Any]]:
        results = []
        cursor.execute(
            """
            SELECT g.grant_id, g.employee_id, e.start_date, g.status, g.granted_at, g.approver_id
            FROM access_grants g
            JOIN employees e ON g.employee_id = e.employee_id
            WHERE e.employment_status = 'ACTIVE'
            ORDER BY g.grant_id DESC
            LIMIT ?;
            """,
            (count,),
        )
        candidates = cursor.fetchall()

        for c in candidates:
            ano_id = self._next_anomaly_id()
            grant_id = c["grant_id"]
            start_dt = datetime.strptime(c["start_date"], "%Y-%m-%d").date()
            premature_dt = (start_dt - timedelta(days=21)).strftime("%Y-%m-%d 08:00:00")

            old_val = {"status": c["status"], "granted_at": c["granted_at"], "approver_id": c["approver_id"]}
            new_val = {"status": "ACTIVE", "granted_at": premature_dt, "approver_id": None}

            cursor.execute(
                """
                UPDATE access_grants
                SET status = 'ACTIVE', granted_at = ?, approver_id = NULL,
                    notes = 'INJECTED ANOMALY: Premature activation without manager approval'
                WHERE grant_id = ?;
                """,
                (premature_dt, grant_id),
            )

            self._log_audit_override(
                cursor, "access_grants", grant_id, old_val, new_val,
                f"Premature access activation for {c['employee_id']} prior to start date {c['start_date']}."
            )

            results.append({
                "anomaly_id": ano_id,
                "scenario_id": "SCENARIO_1_PRESTART_ACCESS",
                "entity_name": "access_grants",
                "record_id": grant_id,
                "issue_type": "PRESTART_OR_UNAPPROVED_ACCESS",
                "expected_finding": f"Access granted on {premature_dt[:10]} prior to start date {c['start_date']} with no approver.",
                "expected_decision": "REVOKE_AND_REAPPROVE",
                "rule_violated": "Access Rule 4.1: Entitlements must not be active before employee start date and without recorded approval.",
                "is_ground_truth": 1,
            })

        return results

    def _inject_scenario_2(self, cursor: sqlite3.Cursor, count: int) -> List[Dict[str, Any]]:
        results = []
        cursor.execute(
            """
            SELECT a.asset_id, a.assigned_to
            FROM assets a
            JOIN employees e ON a.assigned_to = e.employee_id
            WHERE a.status = 'ASSIGNED' AND a.asset_type = 'LAPTOP' AND e.employment_status = 'ACTIVE'
            ORDER BY a.asset_id ASC
            LIMIT ?;
            """,
            (count,),
        )
        emp_candidates = cursor.fetchall()

        cursor.execute(
            "SELECT asset_id, status FROM assets WHERE status = 'IN_STOCK' AND asset_type = 'LAPTOP' ORDER BY asset_id ASC LIMIT ?;",
            (count,),
        )
        spare_assets = cursor.fetchall()

        for idx in range(min(len(emp_candidates), len(spare_assets))):
            ano_id = self._next_anomaly_id()
            target_emp = emp_candidates[idx]["assigned_to"]
            spare_asset_id = spare_assets[idx]["asset_id"]

            old_val = {"status": spare_assets[idx]["status"], "assigned_to": None}
            new_val = {"status": "ASSIGNED", "assigned_to": target_emp}

            cursor.execute(
                """
                UPDATE assets
                SET status = 'ASSIGNED', assigned_to = ?, assigned_at = strftime('%Y-%m-%d %H:%M:%S', 'now')
                WHERE asset_id = ?;
                """,
                (target_emp, spare_asset_id),
            )

            self._log_audit_override(
                cursor, "assets", spare_asset_id, old_val, new_val,
                f"Duplicate laptop asset {spare_asset_id} assigned to custodian {target_emp}."
            )

            results.append({
                "anomaly_id": ano_id,
                "scenario_id": "SCENARIO_2_DUPLICATE_ASSET",
                "entity_name": "assets",
                "record_id": spare_asset_id,
                "issue_type": "DUPLICATE_ASSET_ASSIGNMENT",
                "expected_finding": f"Employee {target_emp} holds multiple active primary laptop assignments.",
                "expected_decision": "RECOVER_SURPLUS_ASSET",
                "rule_violated": "Hardware Rule 2.3: Employees may hold at most one active primary workstation laptop.",
                "is_ground_truth": 1,
            })

        return results

    def _inject_scenario_3(self, cursor: sqlite3.Cursor, count: int) -> List[Dict[str, Any]]:
        results = []
        cursor.execute(
            """
            SELECT g.grant_id, g.employee_id, e.termination_date, g.status
            FROM access_grants g
            JOIN employees e ON g.employee_id = e.employee_id
            WHERE e.employment_status = 'TERMINATED'
            ORDER BY g.grant_id ASC
            LIMIT ?;
            """,
            (count,),
        )
        candidates = cursor.fetchall()

        for c in candidates:
            ano_id = self._next_anomaly_id()
            grant_id = c["grant_id"]

            old_val = {"status": c["status"]}
            new_val = {"status": "ACTIVE", "revoked_at": None}

            cursor.execute(
                """
                UPDATE access_grants
                SET status = 'ACTIVE', revoked_at = NULL,
                    notes = 'INJECTED ANOMALY: Terminated employee retains active entitlement'
                WHERE grant_id = ?;
                """,
                (grant_id,),
            )

            self._log_audit_override(
                cursor, "access_grants", grant_id, old_val, new_val,
                f"Active grant retained for terminated employee {c['employee_id']} (Terminated on {c['termination_date']})."
            )

            results.append({
                "anomaly_id": ano_id,
                "scenario_id": "SCENARIO_3_TERMINATED_RETAINS_ACCESS",
                "entity_name": "access_grants",
                "record_id": grant_id,
                "issue_type": "TERMINATED_EMPLOYEE_ACTIVE_ACCESS",
                "expected_finding": f"Active entitlement retained post-termination date {c['termination_date']} for {c['employee_id']}.",
                "expected_decision": "EMERGENCY_REVOCATION",
                "rule_violated": "Deprovisioning Rule 7.2: All access entitlements must be revoked immediately upon employee termination.",
                "is_ground_truth": 1,
            })

        return results

    def _inject_scenario_4(self, cursor: sqlite3.Cursor, count: int) -> List[Dict[str, Any]]:
        results = []
        cursor.execute(
            """
            SELECT td.dependency_id, td.task_id, td.prerequisite_task_id
            FROM task_dependencies td
            ORDER BY td.dependency_id ASC
            LIMIT ?;
            """,
            (count,),
        )
        candidates = cursor.fetchall()

        for c in candidates:
            ano_id = self._next_anomaly_id()
            task_a = c["task_id"]
            task_b = c["prerequisite_task_id"]

            cycle_dep_id = f"DEP-{task_b}-REV"

            cursor.execute(
                """
                INSERT OR REPLACE INTO task_dependencies (dependency_id, task_id, prerequisite_task_id, created_at)
                VALUES (?, ?, ?, strftime('%Y-%m-%d %H:%M:%S', 'now'));
                """,
                (cycle_dep_id, task_b, task_a),
            )

            self._log_audit_override(
                cursor, "task_dependencies", cycle_dep_id, {}, {"cycle": f"{task_a} <-> {task_b}"},
                f"Injected circular dependency between {task_a} and {task_b}."
            )

            results.append({
                "anomaly_id": ano_id,
                "scenario_id": "SCENARIO_4_TASK_CYCLE",
                "entity_name": "task_dependencies",
                "record_id": cycle_dep_id,
                "issue_type": "TASK_DEPENDENCY_CYCLE",
                "expected_finding": f"Circular deadlock edge detected: {task_b} depends on {task_a}, while {task_a} depends on {task_b}.",
                "expected_decision": "BREAK_DEPENDENCY_CYCLE",
                "rule_violated": "Workflow Rule 1.4: Task workflows must form a strict Directed Acyclic Graph (DAG) with zero circular edges.",
                "is_ground_truth": 1,
            })

        return results

    def _inject_scenario_5(
        self, cursor: sqlite3.Cursor, count: int, excluded_assets: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Picks assets that are currently ASSIGNED, not in the excluded list,
        and marks them RECOVERED without clearing assigned_to.
        Works seamlessly in both starter (60 assets) and full (1,200 assets) modes.
        """
        results = []
        placeholders = ",".join(["?"] * len(excluded_assets)) if excluded_assets else "''"
        query = f"""
            SELECT asset_id, assigned_to, status
            FROM assets
            WHERE status = 'ASSIGNED' AND assigned_to IS NOT NULL
              AND asset_id NOT IN ({placeholders})
            ORDER BY asset_id DESC
            LIMIT ?;
        """
        params = list(excluded_assets) + [count]
        cursor.execute(query, params)
        candidates = cursor.fetchall()

        for c in candidates:
            ano_id = self._next_anomaly_id()
            asset_id = c["asset_id"]
            custodian = c["assigned_to"]
            now_ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

            old_val = {"status": c["status"], "assigned_to": custodian}
            new_val = {"status": "RECOVERED", "assigned_to": custodian, "recovered_at": now_ts}

            cursor.execute(
                """
                UPDATE assets
                SET status = 'RECOVERED', recovered_at = ?
                WHERE asset_id = ?;
                """,
                (now_ts, asset_id),
            )

            self._log_audit_override(
                cursor, "assets", asset_id, old_val, new_val,
                f"Asset {asset_id} marked RECOVERED while retaining custodian reference {custodian}."
            )

            results.append({
                "anomaly_id": ano_id,
                "scenario_id": "SCENARIO_5_RECOVERED_REMAINS_ASSIGNED",
                "entity_name": "assets",
                "record_id": asset_id,
                "issue_type": "RECOVERED_ASSET_RETAINS_CUSTODIAN",
                "expected_finding": f"Asset {asset_id} is marked RECOVERED but still assigned to custodian {custodian}.",
                "expected_decision": "CLEAR_CUSTODIAN_REFERENCE",
                "rule_violated": "Asset Rule 3.5: Assets in RECOVERED or IN_STOCK status must have assigned_to set to NULL.",
                "is_ground_truth": 1,
            })

        return results


def export_ground_truth_files(records: List[Dict[str, Any]], export_dir: Path) -> Tuple[Path, Path]:
    export_dir.mkdir(parents=True, exist_ok=True)
    csv_path = export_dir / "ground_truth.csv"
    json_path = export_dir / "ground_truth.json"

    with open(json_path, "w", encoding="utf-8") as jf:
        json.dump(records, jf, indent=2)

    if records:
        fieldnames = list(records[0].keys())
        with open(csv_path, "w", newline="", encoding="utf-8") as cf:
            writer = csv.DictWriter(cf, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(records)

    return csv_path, json_path