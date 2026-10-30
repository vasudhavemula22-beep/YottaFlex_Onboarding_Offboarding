# 🏢 YottaFlex — AI Employee Onboarding & Offboarding Workflow Automation

![Python Version](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)
![Database](https://img.shields.io/badge/Database-SQLite%203-003B57?logo=sqlite&logoColor=white)
![UI Framework](https://img.shields.io/badge/Frontend-Streamlit-FF4B4B?logo=streamlit&logoColor=white)
![Deterministic Seed](https://img.shields.io/badge/Seed-20261022-success)
![Integrity](https://img.shields.io/badge/Foreign%20Keys-Enforced%20(ON)-blue)
![License](https://img.shields.io/badge/License-MIT-green)

An enterprise lifecycle automation engine governing worker pre-boarding, onboarding, equipment provisioning, access governance, offboarding, and compliance audit tracking. Built using a normalized SQLite relational schema, an atomic business rules service layer, an anomaly injection framework, and an interactive Streamlit operations dashboard.

---

## 📌 Executive Summary

Modern enterprise HR and IT operations often suffer from deprovisioning gaps (e.g., terminated employees retaining system access) and workflow bottlenecks. **YottaFlex** solves this with:
- **Directed Acyclic Graph (DAG) Task Engine**: Prevents dependent tasks from completing until prerequisites are satisfied (with traceable administrative overrides).
- **Segregation of Duties**: Enforces multi-stage access approval (`REQUESTED` ➔ `APPROVED` ➔ `ACTIVE` ➔ `REVOKED`).
- **Asset Custody & Recovery**: Eliminates duplicate equipment assignments and ensures recovered assets have cleared custodians.
- **Continuous Compliance & Anomaly Benchmarking**: Evaluates compliance detectors against deliberately injected negative scenarios using isolated ground truth.
- **100% Deterministic & Synthetic**: Reproducible from seed `20261022` with zero third-party confidential data.

---

## 🏛️ System Architecture & 12 Relational Entities

The system defines 12 core relational entities plus an isolated anomaly evaluation store:
┌───────────────────┐
                          │    departments    │
                          └─────────┬─────────┘
                                    │ 1:N
                           ┌────────┴──────────┐
                 ┌─────────┤       roles       ├─────────┐
                 │         └────────┬──────────┘         │
                 │ 1:N              │ 1:N                │
                 │         ┌────────┴──────────┐         │
                 │         │     employees     │◄──┐     │
                 │         └───┬─────────────┬─┘   │     │
                 │             │ 1:N       1 │     │     │
                 │    ┌────────┴──────────┐  └─────┼─────┤ (Acyclic self-ref
                 │    │     managers      │────────┘ N:1 │  manager_id)
                 │    └───────────────────┘              │
    ┌────────────┴─────────────┬─────────────────────────┴─────────────┐
    │ 1:N                      │ 1:N                                   │ 1:N
    ┌───────┴──────────────┐ ┌───────┴──────────────┐ ┌─────────┴────────────┐
│ onboarding_cases │ │ offboarding_cases │ │ access_grants │
└───────┬──────────────┘ └───────┬──────────────┘ └─────────┬────────────┘
│ 1:N │ 1:N │ N:1
└──────────────┬───────────┴──────────────┐ ┌─────────┴────────────┐
▼ │ │ access_roles │
┌───────────┐ │ └──────────────────────┘
│ tasks │ │
└─────┬─────┘ │
1:N │ 1:N │
┌──────────────┴──────────────┐ ┌───────┴─────────────┐
│ task_dependencies │ │ assets │
└─────────────────────────────┘ └─────────────────────┘
| # | Entity | ID Pattern | Description |
|:---:|:---|:---|:---|
| 1 | **`departments`** | `DEP-###` | Organizational divisions and cost centers (`DEP-001` to `DEP-008`). |
| 2 | **`roles`** | `ROL-###` | Job positions mapped to departments with standard access profiles. |
| 3 | **`employees`** | `EMP-######` | Master personnel records with acyclic self-referential management hierarchy. |
| 4 | **`managers`** | `MGR-######` | Formal supervisory appointments and department oversight roster. |
| 5 | **`onboarding_cases`** | `ONB-YYYY-######` | Pre-hire and start-date lifecycle tracking containers. |
| 6 | **`tasks`** | `TASK-case_id-###` | Work items assigned to actors (Candidate, Manager, IT, HR, Admin). |
| 7 | **`task_dependencies`** | `DEP-TASK-...` | Directed prerequisite constraints forming workflow DAGs. |
| 8 | **`access_roles`** | `ACR-###` | System entitlements catalog with risk levels (Low, Medium, High, Critical). |
| 9 | **`access_grants`** | `GRANT-EMP-...` | Point-in-time security entitlements issued to employees. |
| 10 | **`assets`** | `AST-######` | Physical hardware inventory with custodian tracking. |
| 11 | **`offboarding_cases`** | `OFF-YYYY-######` | Departure containers managing access revocation and asset return. |
| 12 | **`audit_events`** | `AUD-##########` | Immutable append-only ledger capturing all state changes and overrides. |
| 13 | **`labelled_anomalies`** | `ANO-######` | Isolated benchmark table tracking injected negative scenarios. |

---

## 🎯 Target Volumes & Operational Modes

| Entity | Starter Scale (Demo) | Full Production Scale | Technical Rationale |
|:---|:---:|:---:|:---|
| **Employees** | 50 | **1,000** | Master workforce population |
| **Tasks** | 400 | **8,000** | 7 tasks per onboarding case + offboarding departure checklists |
| **Access Grants** | 76 | **1,501** | Baseline SaaS tools + specialized system entitlements |
| **Assets** | 60 | **1,200** | Deployed workstations + warehouse buffer inventory |
| **Managers** | 5 | **50** | 5% supervisory ratio across the organization |
| **Injected Anomalies** | 5 | **25** | Exactly 5 instances per mandatory negative scenario |

---

## 🚨 The 5 Mandatory Anomaly Scenarios & Benchmarks

To benchmark compliance detection, 5 negative scenarios are injected into baseline data without corrupting unrelated records. Ground-truth labels are isolated in `exports/ground_truth.json`:

1. **Premature / Unapproved Access (`PRESTART_OR_UNAPPROVED_ACCESS`)**: Entitlement active before worker start date or lacking required manager/HR approval.
2. **Duplicate Asset Assignment (`DUPLICATE_ASSET_ASSIGNMENT`)**: Multiple primary workstation laptops assigned to a single custodian.
3. **Terminated Worker Retaining Access (`TERMINATED_EMPLOYEE_ACTIVE_ACCESS`)**: Departing employee retains active cloud permissions post-termination date.
4. **Task Dependency Cycle (`TASK_DEPENDENCY_CYCLE`)**: Injected circular dependency edge creating a workflow deadlock ($T_A \to T_B$ and $T_B \to T_A$).
5. **Recovered Asset Retaining Custodian (`RECOVERED_ASSET_RETAINS_CUSTODIAN`)**: Hardware marked warehouse-recovered while retaining an active custodian ID.

### Benchmark Evaluation Results:
```text
Evaluation Metric          Controlled Sandbox     Production DB Set
──────────────────────────────────────────────────────────────────
True Positives (TP)               25                     25
False Negatives (FN)               0                      0
Recall                         100.00%                100.00%
Precision                      100.00%                 71.43%*
F1-Score                       100.00%                 83.33%
    
