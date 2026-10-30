
"""
YottaFlex Workflow and Role Templates.
Defines canonical operational task workflows, baseline access packages,
and hardware provisioning bundles across departments and termination scenarios.
"""

from dataclasses import dataclass
from typing import List, Tuple


@dataclass(frozen=True)
class TaskTemplate:
    sequence: int
    name: str
    category: str
    assigned_actor: str
    offset_days: int
    prerequisite_sequences: Tuple[int, ...]


# Canonical Onboarding Workflow Template (7 sequential & branched tasks)
ONBOARDING_TASK_TEMPLATES: List[TaskTemplate] = [
    TaskTemplate(
        sequence=1,
        name="Sign Corporate Offer & Compliance Agreement",
        category="DOCUMENTATION",
        assigned_actor="CANDIDATE",
        offset_days=-10,
        prerequisite_sequences=(),
    ),
    TaskTemplate(
        sequence=2,
        name="Provision Corporate Email and Workspace Identity",
        category="IT_PROVISIONING",
        assigned_actor="IT_OPERATIONS",
        offset_days=-7,
        prerequisite_sequences=(1,),
    ),
    TaskTemplate(
        sequence=3,
        name="Configure & Ship Workstation Hardware",
        category="HARDWARE",
        assigned_actor="IT_OPERATIONS",
        offset_days=-5,
        prerequisite_sequences=(2,),
    ),
    TaskTemplate(
        sequence=4,
        name="Manager 1-on-1 Planning & Buddy Assignment",
        category="HR_APPROVAL",
        assigned_actor="MANAGER",
        offset_days=-2,
        prerequisite_sequences=(1,),
    ),
    TaskTemplate(
        sequence=5,
        name="Mandatory Security & Compliance Certification",
        category="SECURITY",
        assigned_actor="CANDIDATE",
        offset_days=2,
        prerequisite_sequences=(2,),
    ),
    TaskTemplate(
        sequence=6,
        name="Department Core Systems Entitlement Grant",
        category="IT_PROVISIONING",
        assigned_actor="SYSTEM_ADMIN",
        offset_days=3,
        prerequisite_sequences=(3, 5),
    ),
    TaskTemplate(
        sequence=7,
        name="30-Day Check-in & Manager Performance Alignment",
        category="TRAINING",
        assigned_actor="MANAGER",
        offset_days=30,
        prerequisite_sequences=(4, 6),
    ),
]


# Canonical Offboarding Workflow Template (7 departure tasks)
OFFBOARDING_TASK_TEMPLATES: List[TaskTemplate] = [
    TaskTemplate(
        sequence=1,
        name="Conduct Formal HR Exit Interview",
        category="DOCUMENTATION",
        assigned_actor="HR_PARTNER",
        offset_days=-3,
        prerequisite_sequences=(),
    ),
    TaskTemplate(
        sequence=2,
        name="Initiate Knowledge Transfer & Operational Handoff",
        category="TRAINING",
        assigned_actor="MANAGER",
        offset_days=-2,
        prerequisite_sequences=(),
    ),
    TaskTemplate(
        sequence=3,
        name="Recover Laptop, Badges and Security Tokens",
        category="HARDWARE",
        assigned_actor="IT_OPERATIONS",
        offset_days=0,
        prerequisite_sequences=(),
    ),
    TaskTemplate(
        sequence=4,
        name="Revoke Core Cloud & SSO Access Entitlements",
        category="SECURITY",
        assigned_actor="SYSTEM_ADMIN",
        offset_days=0,
        prerequisite_sequences=(),
    ),
    TaskTemplate(
        sequence=5,
        name="Archive Mailbox & Configure Inbound Auto-Reply",
        category="IT_PROVISIONING",
        assigned_actor="IT_OPERATIONS",
        offset_days=1,
        prerequisite_sequences=(4,),
    ),
    TaskTemplate(
        sequence=6,
        name="Final Payroll & Benefits Settlement Signoff",
        category="HR_APPROVAL",
        assigned_actor="HR_PARTNER",
        offset_days=2,
        prerequisite_sequences=(1, 3),
    ),
    TaskTemplate(
        sequence=7,
        name="System Offboarding Audit Verification",
        category="SECURITY",
        assigned_actor="SYSTEM_ADMIN",
        offset_days=3,
        prerequisite_sequences=(4, 5, 6),
    ),
]


# Standard Hardware Bundles by Department Profile
DEPARTMENT_ASSET_BUNDLES = {
    "DEP-001": "Apple MacBook Pro 16 M3 Max",       # Engineering
    "DEP-002": "Apple MacBook Pro 14 M3 Pro",       # Product
    "DEP-003": "Lenovo ThinkPad P16s Gen 2",        # IT Operations
    "DEP-004": "Dell Latitude 7440 Ultrabook",      # HR
    "DEP-005": "HP EliteBook 840 G10",              # Sales
    "DEP-006": "Dell Latitude 7440 Ultrabook",      # Legal
    "DEP-007": "Lenovo ThinkPad P16s Gen 2",        # Finance
    "DEP-008": "HP EliteBook 840 G10",              # Operations
}