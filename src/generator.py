"""
YottaFlex Synthetic Data Generation Engine (Updated).
Generates deterministic baseline relational data across all 12 entities using fixed seed 20261022.
"""

import json
import random
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class GenerationConfig:
    seed: int = 20261022
    mode: str = "starter"
    num_employees: int = 50
    num_tasks: int = 400
    num_grants: int = 75
    num_assets: int = 60
    num_managers: int = 5
    num_offboarding: int = 8


STARTER_CONFIG = GenerationConfig(
    seed=20261022,
    mode="starter",
    num_employees=50,
    num_tasks=400,
    num_grants=75,
    num_assets=60,
    num_managers=5,
    num_offboarding=8,
)

FULL_CONFIG = GenerationConfig(
    seed=20261022,
    mode="full",
    num_employees=1000,
    num_tasks=8000,
    num_grants=1500,
    num_assets=1200,
    num_managers=50,
    num_offboarding=150,
)


class YottaFlexDataGenerator:
    """
    Deterministic relational data generator adhering to SQLite schema constraints.
    """

    def __init__(self, config: GenerationConfig):
        self.config = config
        self.rng = random.Random(config.seed)
        self.audit_event_counter = 0

        self.first_names = [
            "James", "Mary", "Robert", "Patricia", "John", "Jennifer", "Michael", "Linda",
            "David", "Elizabeth", "William", "Barbara", "Richard", "Susan", "Joseph", "Jessica",
            "Thomas", "Sarah", "Charles", "Karen", "Christopher", "Nancy", "Daniel", "Lisa",
            "Matthew", "Betty", "Anthony", "Margaret", "Mark", "Sandra", "Donald", "Ashley",
            "Steven", "Kimberly", "Paul", "Emily", "Andrew", "Donna", "Joshua", "Michelle",
            "Kenneth", "Dorothy", "Kevin", "Carol", "Brian", "Amanda", "George", "Melissa",
            "Edward", "Deborah", "Ronald", "Stephanie", "Timothy", "Rebecca", "Jason", "Sharon",
            "Jeffrey", "Laura", "Ryan", "Cynthia", "Jacob", "Kathleen", "Gary", "Amy",
            "Nicholas", "Shirley", "Eric", "Angela", "Jonathan", "Helen", "Stephen", "Anna",
            "Larry", "Brenda", "Justin", "Pamela", "Scott", "Nicole", "Brandon", "Emma",
            "Benjamin", "Samantha", "Samuel", "Katherine", "Gregory", "Christine", "Frank", "Debra",
            "Alexander", "Rachel", "Raymond", "Catherine", "Patrick", "Carolyn", "Jack", "Janet",
            "Dennis", "Ruth", "Jerry", "Maria", "Tyler", "Heather", "Aaron", "Diane",
        ]

        self.last_names = [
            "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
            "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson", "Thomas",
            "Taylor", "Moore", "Jackson", "Martin", "Lee", "Perez", "Thompson", "White",
            "Harris", "Sanchez", "Clark", "Ramirez", "Lewis", "Robinson", "Walker", "Young",
            "Allen", "King", "Wright", "Scott", "Torres", "Nguyen", "Hill", "Flores",
            "Green", "Adams", "Nelson", "Baker", "Hall", "Rivera", "Campbell", "Mitchell",
            "Carter", "Roberts", "Gomez", "Phillips", "Evans", "Turner", "Diaz", "Parker",
            "Cruz", "Edwards", "Collins", "Reyes", "Stewart", "Morris", "Morales", "Murphy",
            "Cook", "Rogers", "Gutierrez", "Ortiz", "Morgan", "Cooper", "Peterson", "Bailey",
            "Reed", "Kelly", "Howard", "Ramos", "Kim", "Cox", "Ward", "Richardson",
            "Watson", "Brooks", "Chavez", "Wood", "James", "Bennett", "Gray", "Mendoza",
            "Ruiz", "Hughes", "Price", "Alvarez", "Castillo", "Sanders", "Patel", "Myers",
        ]

        self.dept_templates = [
            ("DEP-001", "Engineering", "CC-1001"),
            ("DEP-002", "Product Management", "CC-1002"),
            ("DEP-003", "Information Technology", "CC-1003"),
            ("DEP-004", "Human Resources", "CC-1004"),
            ("DEP-005", "Sales & Marketing", "CC-1005"),
            ("DEP-006", "Legal & Compliance", "CC-1006"),
            ("DEP-007", "Finance & Accounting", "CC-1007"),
            ("DEP-008", "Global Operations", "CC-1008"),
        ]

        self.role_templates = [
            ("ROL-001", "Software Engineer", "DEP-001", "STANDARD_USER"),
            ("ROL-002", "Senior Software Engineer", "DEP-001", "ELEVATED_USER"),
            ("ROL-003", "Principal Architect", "DEP-001", "DEPT_ADMIN"),
            ("ROL-004", "Associate Product Manager", "DEP-002", "STANDARD_USER"),
            ("ROL-005", "Senior Product Manager", "DEP-002", "ELEVATED_USER"),
            ("ROL-006", "Director of Product", "DEP-002", "DEPT_ADMIN"),
            ("ROL-007", "IT Support Specialist", "DEP-003", "ELEVATED_USER"),
            ("ROL-008", "Systems Administrator", "DEP-003", "SYSTEM_ADMIN"),
            ("ROL-009", "IT Operations Director", "DEP-003", "SYSTEM_ADMIN"),
            ("ROL-010", "HR Coordinator", "DEP-004", "STANDARD_USER"),
            ("ROL-011", "HR Business Partner", "DEP-004", "ELEVATED_USER"),
            ("ROL-012", "Chief People Officer", "DEP-004", "DEPT_ADMIN"),
            ("ROL-013", "Account Executive", "DEP-005", "STANDARD_USER"),
            ("ROL-014", "Sales Operations Manager", "DEP-005", "ELEVATED_USER"),
            ("ROL-015", "VP of Worldwide Sales", "DEP-005", "DEPT_ADMIN"),
            ("ROL-016", "Compliance Analyst", "DEP-006", "STANDARD_USER"),
            ("ROL-017", "Corporate Counsel", "DEP-006", "ELEVATED_USER"),
            ("ROL-018", "General Counsel", "DEP-006", "DEPT_ADMIN"),
            ("ROL-019", "Financial Analyst", "DEP-007", "STANDARD_USER"),
            ("ROL-020", "Senior Controller", "DEP-007", "ELEVATED_USER"),
            ("ROL-021", "Chief Financial Officer", "DEP-007", "DEPT_ADMIN"),
            ("ROL-022", "Operations Associate", "DEP-008", "STANDARD_USER"),
            ("ROL-023", "Operations Manager", "DEP-008", "ELEVATED_USER"),
            ("ROL-024", "Chief Operating Officer", "DEP-008", "DEPT_ADMIN"),
        ]

        self.access_role_templates = [
            ("ACR-001", "Google Workspace Standard", "Google Workspace", "LOW", 0, 0),
            ("ACR-002", "Slack Collaboration Core", "Slack", "LOW", 0, 0),
            ("ACR-003", "Jira & Confluence Contributor", "Atlassian", "LOW", 0, 0),
            ("ACR-004", "GitHub Organization Member", "GitHub Enterprise", "MEDIUM", 1, 0),
            ("ACR-005", "GitHub Repository Administrator", "GitHub Enterprise", "HIGH", 1, 0),
            ("ACR-006", "AWS Cloud Developer Sandbox", "Amazon Web Services", "MEDIUM", 1, 0),
            ("ACR-007", "AWS Production Infrastructure Admin", "Amazon Web Services", "CRITICAL", 1, 1),
            ("ACR-008", "Workday Employee Self-Service", "Workday HCM", "LOW", 0, 0),
            ("ACR-009", "Workday HR Operations Specialist", "Workday HCM", "HIGH", 0, 1),
            ("ACR-010", "Salesforce Sales Representative", "Salesforce CRM", "MEDIUM", 1, 0),
            ("ACR-011", "Salesforce System Administrator", "Salesforce CRM", "CRITICAL", 1, 1),
            ("ACR-012", "Snowflake Analytics Reader", "Snowflake DW", "LOW", 0, 0),
            ("ACR-013", "Snowflake Security Administrator", "Snowflake DW", "CRITICAL", 1, 1),
            ("ACR-014", "NetSuite Financial Accountant", "Oracle NetSuite", "HIGH", 1, 1),
            ("ACR-015", "1Password Corporate Vault Access", "1Password Enterprise", "MEDIUM", 1, 0),
            ("ACR-016", "Datadog Observability Viewer", "Datadog", "LOW", 0, 0),
            ("ACR-017", "PagerDuty Incident Responder", "PagerDuty", "MEDIUM", 1, 0),
            ("ACR-018", "Zoom Pro Video Conferencing", "Zoom Video", "LOW", 0, 0),
            ("ACR-019", "DocuSign Signer & Sender", "DocuSign", "LOW", 0, 0),
            ("ACR-020", "Enterprise VPN Gateway", "Cisco AnyConnect", "HIGH", 1, 0),
        ]

        self.laptop_models = [
            "Apple MacBook Pro 16 M3 Max",
            "Apple MacBook Pro 14 M3 Pro",
            "Lenovo ThinkPad P16s Gen 2",
            "Dell Latitude 7440 Ultrabook",
            "HP EliteBook 840 G10",
        ]

    def _next_audit_id(self) -> str:
        self.audit_event_counter += 1
        return f"AUD-{self.audit_event_counter:010d}"

    def generate_all(self) -> Dict[str, List[Dict[str, Any]]]:
        data: Dict[str, List[Dict[str, Any]]] = {}

        data["departments"] = self._generate_departments()
        data["roles"] = self._generate_roles()
        data["access_roles"] = self._generate_access_roles()
        data["employees"] = self._generate_employees()
        data["managers"] = self._generate_managers_and_assign_hierarchy(data["employees"])
        data["onboarding_cases"] = self._generate_onboarding_cases(data["employees"])
        data["offboarding_cases"] = self._generate_offboarding_cases(data["employees"])
        data["tasks"] = self._generate_tasks(data["onboarding_cases"], data["offboarding_cases"])
        data["task_dependencies"] = self._generate_task_dependencies(data["tasks"])
        data["access_grants"] = self._generate_access_grants(data["employees"], data["access_roles"])
        data["assets"] = self._generate_assets(data["employees"])
        data["audit_events"] = self._generate_audit_events(
            data["employees"],
            data["onboarding_cases"],
            data["offboarding_cases"],
            data["access_grants"],
            data["assets"],
        )
        data["labelled_anomalies"] = []
        return data

    def _generate_departments(self) -> List[Dict[str, Any]]:
        return [
            {
                "dept_id": d[0],
                "dept_name": d[1],
                "cost_center": d[2],
                "created_at": "2025-01-01 00:00:00",
            }
            for d in self.dept_templates
        ]

    def _generate_roles(self) -> List[Dict[str, Any]]:
        return [
            {
                "role_id": r[0],
                "role_title": r[1],
                "dept_id": r[2],
                "standard_access_profile": r[3],
                "created_at": "2025-01-01 00:00:00",
            }
            for r in self.role_templates
        ]

    def _generate_access_roles(self) -> List[Dict[str, Any]]:
        return [
            {
                "access_role_id": a[0],
                "role_name": a[1],
                "system_name": a[2],
                "risk_level": a[3],
                "requires_manager_approval": a[4],
                "requires_hr_approval": a[5],
                "created_at": "2025-01-01 00:00:00",
            }
            for a in self.access_role_templates
        ]

    def _generate_employees(self) -> List[Dict[str, Any]]:
        employees = []
        base_hire_start = date(2025, 10, 1)

        for i in range(1, self.config.num_employees + 1):
            emp_id = f"EMP-{i:06d}"
            first_name = self.rng.choice(self.first_names)
            last_name = self.rng.choice(self.last_names)
            email = f"{first_name.lower()}.{last_name.lower()}.{i:04d}@yottaflex.internal"

            role = self.rng.choice(self.role_templates)
            role_id = role[0]
            dept_id = role[2]

            p_type = self.rng.random()
            if p_type < 0.85:
                emp_type = "FULL_TIME"
            elif p_type < 0.95:
                emp_type = "CONTRACTOR"
            else:
                emp_type = "INTERN"

            hire_offset = int((i / self.config.num_employees) * 240)
            hire_dt = base_hire_start + timedelta(days=hire_offset)

            start_gap = self.rng.randint(14, 28)
            start_dt = hire_dt + timedelta(days=start_gap)

            is_terminated = i <= self.config.num_offboarding
            if is_terminated:
                emp_status = "TERMINATED"
                tenure_days = self.rng.randint(60, 150)
                term_dt = start_dt + timedelta(days=tenure_days)
                termination_date_str = term_dt.strftime("%Y-%m-%d")
            else:
                termination_date_str = None
                p_stat = self.rng.random()
                if p_stat < 0.05:
                    emp_status = "ROLE_CHANGE"
                elif p_stat < 0.08:
                    emp_status = "PRE_HIRE"
                elif p_stat < 0.10:
                    emp_status = "LEAVE"
                else:
                    emp_status = "ACTIVE"

            employees.append(
                {
                    "employee_id": emp_id,
                    "first_name": first_name,
                    "last_name": last_name,
                    "email": email,
                    "role_id": role_id,
                    "dept_id": dept_id,
                    "manager_id": None,
                    "employment_type": emp_type,
                    "employment_status": emp_status,
                    "hire_date": hire_dt.strftime("%Y-%m-%d"),
                    "start_date": start_dt.strftime("%Y-%m-%d"),
                    "termination_date": termination_date_str,
                    "created_at": f"{hire_dt.strftime('%Y-%m-%d')} 08:00:00",
                    "updated_at": f"{start_dt.strftime('%Y-%m-%d')} 09:00:00",
                }
            )

        return employees

    def _generate_managers_and_assign_hierarchy(
        self, employees: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        managers = []
        num_mgrs = min(self.config.num_managers, len(employees))
        mgr_pool_by_dept: Dict[str, List[str]] = {d[0]: [] for d in self.dept_templates}

        for m_idx in range(1, num_mgrs + 1):
            mgr_id = f"MGR-{m_idx:06d}"
            emp = employees[m_idx - 1]
            mgr_pool_by_dept[emp["dept_id"]].append(emp["employee_id"])

            managers.append(
                {
                    "manager_id": mgr_id,
                    "employee_id": emp["employee_id"],
                    "dept_id": emp["dept_id"],
                    "is_active": 1,
                    "appointed_at": f"{emp['start_date']} 09:00:00",
                }
            )

        for emp in employees:
            if emp["employee_id"] == "EMP-000001":
                emp["manager_id"] = None
                continue

            dept_mgrs = mgr_pool_by_dept.get(emp["dept_id"], [])
            if dept_mgrs:
                eligible = [m for m in dept_mgrs if m != emp["employee_id"]]
                if eligible:
                    emp["manager_id"] = self.rng.choice(eligible)
                else:
                    emp["manager_id"] = "EMP-000001"
            else:
                emp["manager_id"] = "EMP-000001"

        return managers

    def _generate_onboarding_cases(
        self, employees: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        cases = []
        for i, emp in enumerate(employees, start=1):
            case_id = f"ONB-2026-{i:06d}"
            target_dt = datetime.strptime(emp["start_date"], "%Y-%m-%d").date()

            is_delayed = (i % 20 == 0) and (emp["employment_status"] != "PRE_HIRE")
            if is_delayed:
                actual_dt = target_dt + timedelta(days=self.rng.randint(7, 14))
                status = "COMPLETED" if emp["employment_status"] in ("ACTIVE", "ROLE_CHANGE", "TERMINATED") else "DELAYED"
            elif emp["employment_status"] == "PRE_HIRE":
                actual_dt = None
                status = "PRE_BOARDING"
            else:
                actual_dt = target_dt
                status = "COMPLETED"

            completed_at_val = (
                f"{actual_dt.strftime('%Y-%m-%d')} 17:00:00" if status == "COMPLETED" and actual_dt else None
            )

            cases.append(
                {
                    "onboarding_case_id": case_id,
                    "employee_id": emp["employee_id"],
                    "target_start_date": target_dt.strftime("%Y-%m-%d"),
                    "actual_start_date": actual_dt.strftime("%Y-%m-%d") if actual_dt else None,
                    "status": status,
                    "created_at": f"{emp['hire_date']} 09:00:00",
                    "completed_at": completed_at_val,
                }
            )

        return cases

    def _generate_offboarding_cases(
        self, employees: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        offboarding_cases = []
        term_emps = [e for e in employees if e["employment_status"] == "TERMINATED"]

        for i, emp in enumerate(term_emps, start=1):
            case_id = f"OFF-2026-{i:06d}"
            term_dt = datetime.strptime(emp["termination_date"], "%Y-%m-%d").date()
            init_dt = term_dt - timedelta(days=14)

            p_term = self.rng.random()
            if p_term < 0.60:
                t_type = "VOLUNTARY"
            elif p_term < 0.85:
                t_type = "INVOLUNTARY"
            elif p_term < 0.95:
                t_type = "CONTRACT_END"
            else:
                t_type = "URGENT_TERMINATION"
                init_dt = term_dt

            status = "COMPLETED"
            completed_at_val = f"{term_dt.strftime('%Y-%m-%d')} 17:00:00"

            offboarding_cases.append(
                {
                    "offboarding_case_id": case_id,
                    "employee_id": emp["employee_id"],
                    "initiated_by": emp["manager_id"] if emp["manager_id"] else "EMP-000001",
                    "initiated_at": f"{init_dt.strftime('%Y-%m-%d')} 09:30:00",
                    "termination_type": t_type,
                    "effective_date": term_dt.strftime("%Y-%m-%d"),
                    "status": status,
                    "completed_at": completed_at_val,
                    "created_at": f"{init_dt.strftime('%Y-%m-%d')} 09:30:00",
                }
            )

        return offboarding_cases

    def _generate_tasks(
        self,
        onboarding_cases: List[Dict[str, Any]],
        offboarding_cases: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        tasks = []

        onb_task_templates = [
            ("1", "Sign Corporate Offer & Compliance Agreement", "DOCUMENTATION", "CANDIDATE", -10),
            ("2", "Provision Corporate Email and Workspace Identity", "IT_PROVISIONING", "IT_OPERATIONS", -7),
            ("3", "Configure & Ship Workstation Hardware", "HARDWARE", "IT_OPERATIONS", -5),
            ("4", "Manager 1-on-1 Planning & Buddy Assignment", "HR_APPROVAL", "MANAGER", -2),
            ("5", "Mandatory Security & Compliance Certification", "SECURITY", "CANDIDATE", 2),
            ("6", "Department Core Systems Entitlement Grant", "IT_PROVISIONING", "SYSTEM_ADMIN", 3),
            ("7", "30-Day Check-in & Manager Performance Alignment", "TRAINING", "MANAGER", 30),
        ]

        for case in onboarding_cases:
            case_id = case["onboarding_case_id"]
            start_dt = datetime.strptime(
                case["actual_start_date"] or case["target_start_date"], "%Y-%m-%d"
            ).date()
            is_case_completed = case["status"] == "COMPLETED"

            for seq_str, name, category, actor, offset in onb_task_templates:
                task_id = f"TASK-{case_id}-{int(seq_str):03d}"
                due_dt = start_dt + timedelta(days=offset)

                if is_case_completed:
                    t_status = "COMPLETED"
                    comp_dt_str = f"{due_dt.strftime('%Y-%m-%d')} 16:00:00"
                else:
                    t_status = "PENDING" if offset <= 0 else "BLOCKED"
                    comp_dt_str = None

                tasks.append(
                    {
                        "task_id": task_id,
                        "case_type": "ONBOARDING",
                        "case_id": case_id,
                        "task_name": name,
                        "task_category": category,
                        "assigned_actor": actor,
                        "status": t_status,
                        "due_date": due_dt.strftime("%Y-%m-%d"),
                        "completed_at": comp_dt_str,
                        "created_at": case["created_at"],
                    }
                )

        tasks_needed = self.config.num_tasks - len(tasks)
        num_off_cases = len(offboarding_cases)

        off_task_templates = [
            ("1", "Conduct Formal HR Exit Interview", "DOCUMENTATION", "HR_PARTNER", -3),
            ("2", "Initiate Knowledge Transfer & Handoff", "TRAINING", "MANAGER", -2),
            ("3", "Recover Laptop, Badges and Security Tokens", "HARDWARE", "IT_OPERATIONS", 0),
            ("4", "Revoke Core Cloud & SSO Access Entitlements", "SECURITY", "SYSTEM_ADMIN", 0),
            ("5", "Archive Email & Redirect Inbound Inquiries", "IT_PROVISIONING", "IT_OPERATIONS", 1),
            ("6", "Final Payroll & Benefits Settlement Signoff", "HR_APPROVAL", "HR_PARTNER", 2),
            ("7", "System Offboarding Audit Verification", "SECURITY", "SYSTEM_ADMIN", 3),
        ]

        base_tasks_per_case = tasks_needed // num_off_cases if num_off_cases > 0 else 0
        extra_tasks = tasks_needed % num_off_cases if num_off_cases > 0 else 0

        for i, case in enumerate(offboarding_cases):
            case_id = case["offboarding_case_id"]
            term_dt = datetime.strptime(case["effective_date"], "%Y-%m-%d").date()
            t_count = base_tasks_per_case + (1 if i < extra_tasks else 0)

            for seq in range(1, t_count + 1):
                tmpl = off_task_templates[min(seq - 1, len(off_task_templates) - 1)]
                task_id = f"TASK-{case_id}-{seq:03d}"
                due_dt = term_dt + timedelta(days=tmpl[4])

                tasks.append(
                    {
                        "task_id": task_id,
                        "case_type": "OFFBOARDING",
                        "case_id": case_id,
                        "task_name": tmpl[1],
                        "task_category": tmpl[2],
                        "assigned_actor": tmpl[3],
                        "status": "COMPLETED",
                        "due_date": due_dt.strftime("%Y-%m-%d"),
                        "completed_at": f"{due_dt.strftime('%Y-%m-%d')} 16:30:00",
                        "created_at": case["created_at"],
                    }
                )

        return tasks

    def _generate_task_dependencies(
        self, tasks: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        dependencies = []
        tasks_by_case: Dict[str, List[Dict[str, Any]]] = {}
        for t in tasks:
            tasks_by_case.setdefault(t["case_id"], []).append(t)

        for case_id, case_tasks in tasks_by_case.items():
            sorted_tasks = sorted(case_tasks, key=lambda x: x["task_id"])
            for idx in range(1, len(sorted_tasks)):
                curr_task = sorted_tasks[idx]
                prereq_task = sorted_tasks[idx - 1]

                dep_id = f"DEP-{curr_task['task_id']}-{idx:03d}"
                dependencies.append(
                    {
                        "dependency_id": dep_id,
                        "task_id": curr_task["task_id"],
                        "prerequisite_task_id": prereq_task["task_id"],
                        "created_at": curr_task["created_at"],
                    }
                )

        return dependencies

    def _generate_access_grants(
        self, employees: List[Dict[str, Any]], access_roles: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        grants = []
        grants_needed = self.config.num_grants
        num_emps = len(employees)

        grant_idx = 0
        for i, emp in enumerate(employees):
            grant_idx += 1
            grant_id = f"GRANT-{emp['employee_id']}-001"
            base_role = access_roles[0] if i % 2 == 0 else access_roles[1]

            is_term = emp["employment_status"] == "TERMINATED"
            status = "REVOKED" if is_term else "ACTIVE"

            grants.append(
                {
                    "grant_id": grant_id,
                    "employee_id": emp["employee_id"],
                    "access_role_id": base_role["access_role_id"],
                    "status": status,
                    "granted_at": f"{emp['start_date']} 09:00:00",
                    "revoked_at": f"{emp['termination_date']} 17:00:00" if is_term else None,
                    "approver_id": emp["manager_id"] if emp["manager_id"] else "EMP-000001",
                    "notes": "Standard automated baseline grant upon start.",
                    "created_at": f"{emp['hire_date']} 10:00:00",
                }
            )

        secondary_pool = access_roles[2:]
        emp_ptr = 0
        while len(grants) < grants_needed:
            emp = employees[emp_ptr % num_emps]
            emp_ptr += 1
            seq = 2
            grant_id = f"GRANT-{emp['employee_id']}-{seq:03d}"

            while any(g["grant_id"] == grant_id for g in grants):
                seq += 1
                grant_id = f"GRANT-{emp['employee_id']}-{seq:03d}"

            spec_role = self.rng.choice(secondary_pool)
            is_term = emp["employment_status"] == "TERMINATED"
            status = "REVOKED" if is_term else "ACTIVE"

            grants.append(
                {
                    "grant_id": grant_id,
                    "employee_id": emp["employee_id"],
                    "access_role_id": spec_role["access_role_id"],
                    "status": status,
                    "granted_at": f"{emp['start_date']} 11:00:00",
                    "revoked_at": f"{emp['termination_date']} 17:00:00" if is_term else None,
                    "approver_id": emp["manager_id"] if emp["manager_id"] else "EMP-000001",
                    "notes": "Department-specific secondary entitlement grant.",
                    "created_at": f"{emp['hire_date']} 11:00:00",
                }
            )

        return grants

    def _generate_assets(self, employees: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        assets = []
        num_assets = self.config.num_assets
        num_emps = len(employees)

        for i in range(1, num_assets + 1):
            asset_id = f"AST-{i:06d}"
            serial_num = f"SN-YOTTA-{i:06d}"
            model = self.rng.choice(self.laptop_models)

            if i <= num_emps:
                emp = employees[i - 1]
                is_term = emp["employment_status"] == "TERMINATED"

                start_dt = datetime.strptime(emp["start_date"], "%Y-%m-%d").date()
                assigned_dt = start_dt - timedelta(days=3)

                if is_term:
                    status = "RECOVERED"
                    assigned_to = None  # Clean baseline: recovered assets have NULL custodian
                    recov_dt = datetime.strptime(emp["termination_date"], "%Y-%m-%d").date()
                    recov_str = f"{recov_dt.strftime('%Y-%m-%d')} 16:00:00"
                else:
                    status = "ASSIGNED"
                    assigned_to = emp["employee_id"]
                    recov_str = None

                assets.append(
                    {
                        "asset_id": asset_id,
                        "asset_type": "LAPTOP",
                        "serial_number": serial_num,
                        "model_name": model,
                        "assigned_to": assigned_to,
                        "status": status,
                        "assigned_at": f"{assigned_dt.strftime('%Y-%m-%d')} 14:00:00",
                        "recovered_at": recov_str,
                        "created_at": "2025-01-01 08:00:00",
                    }
                )
            else:
                p_pool = self.rng.random()
                status = "IN_STOCK" if p_pool < 0.70 else "PROVISIONED"
                assets.append(
                    {
                        "asset_id": asset_id,
                        "asset_type": "LAPTOP",
                        "serial_number": serial_num,
                        "model_name": model,
                        "assigned_to": None,
                        "status": status,
                        "assigned_at": None,
                        "recovered_at": None,
                        "created_at": "2025-01-01 08:00:00",
                    }
                )

        return assets

    def _generate_audit_events(
        self,
        employees: List[Dict[str, Any]],
        onboarding_cases: List[Dict[str, Any]],
        offboarding_cases: List[Dict[str, Any]],
        access_grants: List[Dict[str, Any]],
        assets: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        events = []

        for emp in employees:
            events.append(
                {
                    "event_id": self._next_audit_id(),
                    "entity_name": "employees",
                    "record_id": emp["employee_id"],
                    "action": "INSERT",
                    "actor_id": "EMP-000001",
                    "actor_role": "SYSTEM_ADMIN",
                    "old_values_json": None,
                    "new_values_json": json.dumps({"status": emp["employment_status"], "email": emp["email"]}),
                    "timestamp": emp["created_at"],
                    "details": "Initial employee record created during pre-boarding.",
                }
            )

        for onb in onboarding_cases:
            if onb["status"] == "COMPLETED" and onb["completed_at"]:
                events.append(
                    {
                        "event_id": self._next_audit_id(),
                        "entity_name": "onboarding_cases",
                        "record_id": onb["onboarding_case_id"],
                        "action": "UPDATE",
                        "actor_id": "EMP-000001",
                        "actor_role": "HR_PARTNER",
                        "old_values_json": json.dumps({"status": "IN_PROGRESS"}),
                        "new_values_json": json.dumps({"status": "COMPLETED"}),
                        "timestamp": onb["completed_at"],
                        "details": "All onboarding milestones verified and completed.",
                    }
                )

        for g in access_grants:
            events.append(
                {
                    "event_id": self._next_audit_id(),
                    "entity_name": "access_grants",
                    "record_id": g["grant_id"],
                    "action": "INSERT",
                    "actor_id": g["approver_id"] or "EMP-000001",
                    "actor_role": "IT_OPERATIONS",
                    "old_values_json": None,
                    "new_values_json": json.dumps({"status": g["status"], "role": g["access_role_id"]}),
                    "timestamp": g["granted_at"] or g["created_at"],
                    "details": "Access grant entitlement provisioned.",
                }
            )

        for a in assets:
            if a["assigned_to"]:
                events.append(
                    {
                        "event_id": self._next_audit_id(),
                        "entity_name": "assets",
                        "record_id": a["asset_id"],
                        "action": "UPDATE",
                        "actor_id": "EMP-000001",
                        "actor_role": "IT_OPERATIONS",
                        "old_values_json": json.dumps({"status": "IN_STOCK"}),
                        "new_values_json": json.dumps({"status": a["status"], "assigned_to": a["assigned_to"]}),
                        "timestamp": a["assigned_at"] or a["created_at"],
                        "details": "Hardware asset custodian assignment confirmed.",
                    }
                )

        for off in offboarding_cases:
            events.append(
                {
                    "event_id": self._next_audit_id(),
                    "entity_name": "offboarding_cases",
                    "record_id": off["offboarding_case_id"],
                    "action": "UPDATE",
                    "actor_id": off["initiated_by"],
                    "actor_role": "HR_PARTNER",
                    "old_values_json": json.dumps({"status": "INITIATED"}),
                    "new_values_json": json.dumps({"status": off["status"]}),
                    "timestamp": off["completed_at"] or off["created_at"],
                    "details": f"Offboarding workflow finalized ({off['termination_type']}).",
                }
            )

        return events